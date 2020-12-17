==========
Work units
==========

Work units are the building blocks of BPTL. They are the smallest units that can be
executed by themselves, while having sufficient meaning.

Work units typically require input variables, process these and do some work, and
finally (optionally) return output variables.

Work unit interface
===================

Work units have two possible interface: function or class based. Function based work
units are easiest to reason about, while class-based units are suited to more complex
units.

Function based
--------------

A function based unit follows the following pattern:

.. code-block:: python

    def some_work_unit(task):
        # ... extract relevant variables

        # ... perform work

        return {"foo": "bar"}  # return relevant result variables

See for example ``bptl.dummy.tasks.dummy``.

Class based
-----------

Class based work units allow you to split up work into methods.

Example:

.. code-block:: python

    from bptl.tasks.base import WorkUnit


    class MyWorkUnit(WorkUnit):

        def perform(self):
            # ... extract relevant variables

            # ... perform work

            return {"foo": "bar"}  # return relevant result variables

The unit constructor receives the task instance as sole argument.

Registering work units
======================

Work units can be contributed to BPTL, or can be defined in third-party packages.

Autodiscover
------------

Work units are auto-discovered for Django apps in the ``tasks`` module, so make sure to:

1. Add your app to ``INSTALLED_APPS``
2. Define your units in ``myapp.tasks``

or, alternatively, you can use the ``ready`` hook in your ``AppConfig`` to import the
relevant tasks module.

Registration
------------

Registering work units is done by decorating them with ``bptl.tasks.registry.register``,
which is the default registry:

.. code-block:: python

    from bptl.tasks.registry import register

    @register
    class SomeWorkUnit(WorkUnit):
        ...


    @register
    def another_work_unit(task):
        ...


Defining required services
--------------------------

Work units often interact with various external services, which require authentication.
You can declare which type of services with which aliases are required for a work-unit,
and then safely use those aliases in the code to build a client and retrieve credentials.

The forms to configure task mappings will validate that the declared required services
are configured correctly.

Example:

.. code-block:: python

    from bptl.tasks.registry import register

    @register
    @register.require_service("zrc", "The Zaken API to use", alias="zrc")
    def some_work_unit(task):
        service = DefaultService.objects.get(
            task_mapping__topic_name=task.topic_name,
            alias="zrc"
        ).service
        ...

The decorator is currently only used for form validation.

.. autofunction:: bptl.tasks.registry.register.require_service


Authenticating in a work unit
-----------------------------

BPTL executes work units on behalf of another application, often through a process
engine. For auditing purposes, you should not interface to external services with
"blanket" BPTL credentials, but instead use application specific credentials.

BPTL has a credential store containing the credentials for a particular application
(identified by an "App ID") for each service it needs to interact with. To use this,
you must:

1. Extract the ``bptlAppId`` process variable from the task:

    .. code-block:: python

        @register
        def some_work_unit(task):
            app_id = check_variable(task.get_variables(), "bptlAppId")

2. Determine the required service(s):

    .. code-block:: python

        @register
        @register.require_service("zrc", "The Zaken API to use", alias="zrc")
        @register.require_service("drc", "The Documenten API to use", alias="drc")
        def some_work_unit(task):
            app_id = check_variable(task.get_variables(), "bptlAppId")
            default_services = DefaultService.objects.get(
                task_mapping__topic_name=task.topic_name,
                alias__in=["zrc", "drc"]
            )
            services = {
                default_service.alias: default_service.service
                for default_service in default_services
            }

3. Obtain the application-specific credentials:

    .. code-block:: python

        @register
        @register.require_service("zrc", "The Zaken API to use", alias="zrc")
        @register.require_service("drc", "The Documenten API to use", alias="drc")
        def some_work_unit(task):
            app_id = check_variable(task.get_variables(), "bptlAppId")
            default_services = DefaultService.objects.get(
                task_mapping__topic_name=task.topic_name,
                alias__in=["zrc", "drc"]
            )
            services = {
                default_service.alias: default_service.service
                for default_service in default_services
            }
            auth_headers = get_credentials(app_id, services["zrc"], services["drc"])

            zrc_client = services["zrc"].build_client()
            zrc_client.set_auth_value(auth_headers[services["zrc"]])

            drc_client = services["drc"].build_client()
            drc_client.set_auth_value(auth_headers[services["drc"]])


The public api to get the credentials is:

.. autofunction:: bptl.credentials.api.get_credentials


Task interface
==============

Work units receive the ``task`` instance that they should execute. This is always a
subclass of :class:`bptl.tasks.models.BaseTask`:

.. autoclass:: bptl.tasks.models.BaseTask
    :members:

Subclasses are aimed at particular process engines, and are expected to implement the
:meth:`bptl.tasks.models.BaseTask.get_variables` interface correctly.

Best practices
==============

Documentation
-------------

Document your work unit extensively! You can use RST - the docstring is extracted
into the task documentation and displayed in the web-interface, admin, and even command
line output. The recommended format is:

.. code-block:: python

    def work_unit(task):
        """
        Describe a short summary of what the task does.

        **Required process variables**

        * ``var``: a string representing an example

        **Optional process variables**

        * ``foo``: if provided, will summon Chtulhu

        **Optional process variables (engine specific)**

        * ``bar``: complex JSON variable with the following structure:

            .. code-block:: json

                {"ok": "I lied"}

        **Sets the process variables**

        * ``quux``: PI with all decimals, ever

        """

Variable extraction
-------------------

Use the :meth:`bptl.tasks.models.BaseTask.get_variables` to obtain the variables. This
takes care of deserialization into the appropriate Python data-type, and is responsible
for abstracting away the differences between process engines.

Use ``bptl.tasks.base.check_variable`` to retrieve (soft-)required process variables:

.. autofunction:: bptl.tasks.base.check_variable

It will raise a clear error when a process variable is missing, and shortcuts the
unit execution.
