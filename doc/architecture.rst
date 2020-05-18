.. _architecture:

============
Architecture
============

BPTL is a middle-man in your application landscape. It "talks" to APIs or performs task
when asked to do so.

A typical layout of your application landscape would be the following set-up:

* a number of user-facing applications start process instances - they communicate with
  the API of your process engine (e.g. Camunda)
* process definitions can change as often as needed because of business needs
* processes require input or processing from certain data-sources that you wish to
  automate
* data needs to be stored in the appropriate locations

BPTL solves the last two items - it helps automating *very specific* tasks that are
too complex for BPMN, but not complex enough to warrant an entire, dedicated
application.


BPTL Components
===============

BPTL consists of a number of components that make it work for various use cases.

**Work units**

Work units are logical units of work that can be performed. This can be a collection of
API calls, for example to create a **Zaak**, or to check if someone's age is above a
certain number, using the BRP API's. These are the steps that you want to "embed" in
your process.

Work units are grouped around themes, such as the ZGW APIs, the BRP, Camunda API or the
Kadaster APIs.

Work units are implemented in Python code.

**Web interface**

The web interface allows you to configure work-units to a certain topic. This way, you
can use meaningful names in your process, or decide to only let BPTL handle a subset
of topics relevant for you, and another solution for other specialized topics.

Additionally, the web interface provides you monitoring and debug-information for if/when
something goes wrong.

**Workers**

Workers are responsible for performance of the work-units. Whenever a task is picked
up from the task queue, a worker is assigned to execute it. Workers can be scaled
independently from the web-interface, and they prevent the web-interface from locking
up during long-running tasks.

**Beat**

Beat is used to periodically fire tasks that workers need to perform. Beat is essential
to poll Camunda for new work to assign to the workers.

**Task monitoring**

The communication between web, workers and beat is monitored to see if tasks get dropped
or investigating where scaling is needed.

.. _architecture_timeline:

Timeline
--------

A typical timeline is the following:

1. Process execution is started
2. Process execution arrives at an external task
3. External task is put on the queue
4. BPTL polling picks up the queued task
5. BPTL assigns the task to a worker
6. BPTL worker performs the related work unit
7. BPTL worker marks the task as completed
8. Process execution continues to the next waiting point

Process engines
===============

Currently, two process engines are supported to varying degrees:

* Camunda: arguably the most fleshed out, and the target architecture
* Activiti: a proof of concept showed promising results

Camunda architecture
====================

The above :ref:`architecture_timeline` describes Camunda architecture.

Camunda uses a service-task implementation called **External Task**. Whenever a process
execution arrives at an external task, the task is put on a queue with its *topic name*.

BPTL periodically polls the Camunda queue for work, and it does so by only asking about
topics that BPTL is configured to handle.

Whenever work is picked up, the task is locked and handled by BPTL. BPTL either completes
it and sets the relevant process variables, or marks the task as failed if errors occur.
The failure information is visible in BPTL monitoring and in the Camunda cockpit.

REST-full API architecture
==========================

Activiti does not use a queue to schedule work. Instead, you can include REST-call
activities in the process definition. BPTL offers a REST-full API to call/execute
work units, using a similar format to Camunda's external tasks.

The API endpoints can also be used by other applications who wish to re-use the building
blocks offered by BPTL.

In this configuration, the workers, beat and task monitoring are not relevant.
