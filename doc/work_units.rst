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
