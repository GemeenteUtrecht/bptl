==========
Deployment
==========

For BPTL deployment, we recommend using the Docker images, available on `Docker Hub`_.

The ``docker-compose.yml`` can provide a little insight in the required services.

Dependencies
============

BPTL is tested against Camunda. 

If you're running against Camunda, you need:

* A Camunda instance with REST api, e.g. ``https://camunda.example.com/engine-rest/``
* An API user with username/password credentials. The user needs at least the following
  permissions:

      - ``READ``, ``UPDATE``, ``UPDATE_VARIABLE`` on *Process Instance*, with wildcard
        Resource ID.

Services
========

BPTL requires the following services:

- PostgreSQL 14 or higher database
- Redis as message queue broker, result store and in-memory cache for the web interface
- Some form of reverse proxy (e.g. Nginx, Traefik...)

The BPTL docker image contains the following executables:

- web worker (``/start.sh``)
- celery beat to kick off periodic tasks (``/celery_beat.sh``)
- celery worker (``/celery_worker.sh``)
- celery monitoring (``/celery_flower.sh``)

Celery is the tooling used for asynchronous background tasks, which is *required* if
you use Camunda.

Queues
------

BPTL makes use of two distinct Celery queues, which means you will need to have at
least one worker running on each.

You can set the queue name via the ``CELERY_WORKER_QUEUE`` environment variable.

You can scale the parallel work-load by scaling the amount of workers.

**Long-polling queue**

This queue is intended for the long-polling tasks, which can run up to 30 minutes.
Regular work may not be scheduled on this queue, as it might be blocked behind such
a long-polling job.

We recommend running two workers for high-availability set-up, but one should work too.

.. code-block:: bash

    export CELERY_WORKER_QUEUE=long-polling
    /celery_worker.sh

**Worker queue**

The worker queue is intended for jobs that should run asynchronously, but still complete
in a matter of seconds.

.. code-block:: bash

    export CELERY_WORKER_QUEUE=celery
    /celery_worker.sh

Celery beat
-----------

Beat is used to periodically kick off tasks, you can compare it a little to cronjobs.
It ensures that the long-polling is initially started, and re-started in case a crash
happens.

.. code-block:: bash

    /celery_beat.sh

Celery monitoring
-----------------

Flower is used for task monitoring. You should carefully protect the endpoint where
Flower is hosted, as it gives insight into the app settings. It's meant for
troubleshooting and should be developer/ops-only access.

.. code-block:: bash

    /celery_flower.sh

Recap
=====

If you're running 100% on Docker, for a single BPTL instance you would have:

- 1 PostgreSQL database container
- 1 Redis container
- 1 web worker
- 1 celery beat
- 2 celery workers, ``long-polling`` queue
- 3 celery workers, ``celery`` queue
- 1 celery flower
- nginx on the host system or a suitable Kubernetes Ingress solution

.. _Docker Hub: https://hub.docker.com/r/scrumteamzgw/bptl
