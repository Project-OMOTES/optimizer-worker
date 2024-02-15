#!/bin/bash

. .venv/bin/activate
. ci/linux/_load_dot_env.sh .env.local

PYTHONPATH="src/" python3 -m grow_worker.worker
