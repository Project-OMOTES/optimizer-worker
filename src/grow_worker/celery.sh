#!/usr/bin/env bash

WORKER_TYPE='grow'
CELERY_SCALE=1

mkdir -p /var/run/celery /var/log/celery

exec celery --app=grow_worker.worker worker \
            --autoscale ${CELERY_SCALE} \
            --loglevel=INFO \
            --hostname=worker-${WORKER_TYPE}@%h \
            --queues=${WORKER_TYPE} \
            --logfile=/var/log/celery/worker.log \
            --statedb=/var/run/celery/worker@%h.state
