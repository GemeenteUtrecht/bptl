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

Using ValidSign with BPTL
=========================

BPTL can be used to create tasks to electronically sign a set of documents using `ValidSign`_.
When the task ``CreateValidSignPackageTask`` is executed, the following steps are performed:

    1. A package is created. The signers specified in the task process variables are included in the package when it is created.
    2. The documents are added to the package. All documents specified in the process variables are retrieved from their respective API. For each document, an 'approval' is created. This is a field where a signer will be able to sign.
    3. The package status is changed to SENT. This automatically sends an email to the signers with links to where they can sign the documents.

.. TODO Add details on how to configure the approval


.. _ValidSign: https://www.validsign.nl/
