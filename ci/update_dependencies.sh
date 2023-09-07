#!/bin/bash
. .venv/bin/activate
pip-compile -o requirements.txt ./pyproject.toml
