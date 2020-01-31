#!/bin/sh

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

echo "Starting celery worker"
celery worker \
    --app camunda_worker \
    -l $LOGLEVEL \
    --workdir src
