#!/bin/bash

set -e

while [ $# -gt 0 ]; do

   if [[ $1 == *"--"* ]]; then
        param="${1/--/}"
        declare $param="$2"
   fi

  shift
done

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-1}
QUEUE=${CELERY_WORKER_QUEUE:-default}
NAME=${CELERY_WORKER_NAME:-worker.$QUEUE}

echo "Starting celery worker: $NAME." 
celery worker \
    --app bptl \
    -n $NAME \
    -Q $QUEUE \
    -l $LOGLEVEL \
    --workdir src \
    -O fair \
    -c $CONCURRENCY \
    -- detach
