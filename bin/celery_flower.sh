#!/bin/bash

set -e

echo "Starting flower"
celery flower \
    --app bptl \
    --workdir src \
