#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-1}

echo "Starting celery worker"
celery worker \
    --app bptl \
    -l $LOGLEVEL \
    --workdir src \
    -O fair \
    -c $CONCURRENCY
