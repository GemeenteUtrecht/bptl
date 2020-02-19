=====
Usage
=====

Management commands
===================

``fetch_and_lock_tasks``
------------------------

This command fetches and locks a number of external tasks for futher processing, from
the Camunda instance. The Camunda instance decides which tasks you get returned.

In its current form, only the topic ``zaak-initialize`` is recognized. Topic names are
required input parameters for the Camunda API call, which will be made dynamic in
future iterations.

The task is locked for 10 minutes in its current implementation, and fetched tasks are
visible in the admin interface.

Example:

.. code-block:: bash

    python src/manage.py fetch_and_lock_tasks 1

``show_task_registry``
----------------------

A command to quickly see which tasks are registered in the project.

Example:

.. code-block:: bash

    python src/manage.py show_task_registry

    bptl.dummy.tasks.dummy

      A dummy task to demonstrate the registry machinery.

      The task receives the :class:`FetchedTask` instance and logs some information,
      after which it completes the task.


Python API
==========

.. TODO Use sphinx-autodoc for this

Complete tasks
--------------

Whenever an external task for a certain topic is done/performed, the task itself
needs to be completed and updated with resulting process variables.

For this purpose, ``bptl.camunda.utils.complete_task`` exists. Pass
the ``FetchedTask`` instance and a dict of ``variable_name: value`` to update
process variables. If no process variables need to be updated, you can leave the
``variables`` off.

Note that this needs to happen within the expiry time for the tasks - when a task is
fetched and locked, the lock expires after a while. You can verify this in the admin.
