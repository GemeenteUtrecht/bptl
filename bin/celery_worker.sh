#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-1}

QUEUE=${1:-${CELERY_WORKER_QUEUE:=celery}}
WORKER_NAME=${2:-${CELERY_WORKER_NAME:=$QUEUE}}
POD_NAME=${3:-${hostname:=default}}

NAME="${WORKER_NAME}.${POD_NAME}"

echo "Starting celery worker $NAME with queue $QUEUE"
celery worker \
    --app bptl \
    -Q $QUEUE \
    -n $NAME \
    -l $LOGLEVEL \
    --workdir src \
    -O fair \
    -c $CONCURRENCY

