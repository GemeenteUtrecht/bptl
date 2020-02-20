==========
Public API
==========

Tasks and task registry
=======================

.. automodule:: bptl.tasks.api
    :members:

Work units
==========
Work units are python callbacks which process tasks from external engines.
They are engine independent and can be python functions or classes.
Work units are registered in the registry.

.. automodule:: bptl.work_units.zgw.tasks
    :members:


Camunda tasks
==============

.. automodule:: bptl.camunda.utils
    :members:
