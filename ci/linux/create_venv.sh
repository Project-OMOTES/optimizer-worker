#!/usr/bin/env bash

python3.10 -m venv ./.venv
if [[ "$OSTYPE" != "win32" && "$OSTYPE" != "msys" ]]; then
  echo "Activating .venv first."
  . .venv/bin/activate
fi
# install the missing dep alongside pip-tools
pip3 install pip-tools typing_extensions
