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

Python API
==========

.. TODO Use sphinx-autodoc for this

Whenever an external task for a certain topic is done/performed, the task itself
needs to be completed and updated with resulting process variables.

For this purpose, ``camunda_worker.external_tasks.camunda.complete_task`` exists. Pass
the ``FetchedTask`` instance and a dict of ``variable_name: value`` to update
process variables. If no process variables need to be updated, you can leave the
``variables`` off.

Note that this needs to happen within the expiry time for the tasks - when a task is
fetched and locked, the lock expires after a while. You can verify this in the admin.
