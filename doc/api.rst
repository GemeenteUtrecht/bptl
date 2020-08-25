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

API's voor Zaakgericht Werken
-----------------------------

.. automodule:: bptl.work_units.zgw.tasks.zaak
    :members:

.. automodule:: bptl.work_units.zgw.tasks.status
    :members:

.. automodule:: bptl.work_units.zgw.tasks.resultaat
    :members:

.. automodule:: bptl.work_units.zgw.tasks.zaak_relations
    :members:

BRP
---

.. automodule:: bptl.work_units.brp.tasks
    :members:

Kadaster
--------

.. automodule:: bptl.work_units.kadaster.tasks
    :members:

Camunda
-------

.. automodule:: bptl.work_units.camunda_api.tasks
    :members:

ValidSign
---------

.. automodule:: bptl.work_units.valid_sign.tasks
    :members:

Camunda tasks
==============

.. automodule:: bptl.camunda.utils
    :members:
