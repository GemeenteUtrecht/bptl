#!/bin/sh

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

echo "Starting celery beat"
celery beat \
    --app camunda_worker \
    --workdir src \
    -l $LOGLEVEL \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
