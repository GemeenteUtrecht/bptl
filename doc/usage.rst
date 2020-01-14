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
