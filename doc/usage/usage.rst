.. _usage:

=====
Usage
=====

Management commands
===================

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

Execute tasks
--------------

When an external task for a certain topic is received, you can use ``bptl.tasks.api.execute``
to process it. Pass the ``FetchedTask`` instance and make sure that the required ``WorkUnit``
is added to the registry.
