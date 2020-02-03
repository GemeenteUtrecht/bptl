#!/bin/sh

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

mkdir -p ../celerybeat

echo "Starting celery worker"
celery worker \
    --app camunda_worker \
    -l $LOGLEVEL \
    --workdir src \
    -B \
    -s ../celerybeat/beat

