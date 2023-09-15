#!/bin/bash

. .venv/bin/activate

mkdir -p ./temp/input_files
mkdir -p ./temp/output_files

export INPUT_FILES_DIR=./temp/input_files
export OUTPUT_FILES_DIR=./temp/output_files

PYTHONPATH="src/" python3 -m optimizer_worker.main