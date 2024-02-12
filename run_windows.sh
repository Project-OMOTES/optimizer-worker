#!/bin/bash

source ./venv/Scripts/activate
set -a
source .env
set +a

mkdir -p ./temp/input_files
mkdir -p ./temp/output_files

export INPUT_FILES_DIR=./temp/input_files
export OUTPUT_FILES_DIR=./temp/output_files

export PYTHONPATH=./src/
python -m grow_worker.worker
