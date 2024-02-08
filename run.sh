#!/bin/bash

. .venv/bin/activate
. ci/linux/_load_dot_env.sh .env.local

mkdir -p ./temp/input_files
mkdir -p ./temp/output_files

export INPUT_FILES_DIR=./temp/input_files
export OUTPUT_FILES_DIR=./temp/output_files

PYTHONPATH="src/" python3 -m grow_worker.worker
