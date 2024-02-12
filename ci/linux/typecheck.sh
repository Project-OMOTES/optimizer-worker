#!/usr/bin/env sh

. .venv/bin/activate
python -m mypy ./src/grow_worker ./unit_test/
