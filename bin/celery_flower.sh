#!/bin/bash

set -e

echo "Starting flower"
flower \
    --app bptl \
    --workdir src \
