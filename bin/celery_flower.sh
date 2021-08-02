#!/bin/bash
exec celery --workdir src --app bptl flower 
