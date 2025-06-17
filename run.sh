#!/bin/bash

. .venv/bin/activate
. ci/linux/_load_dot_env.sh .env.local

export DIR_TO_ROOT="$PWD"

export GUROBI_HOME="${DIR_TO_ROOT}/gurobi"
export PATH="${GUROBI_HOME}/bin:$PATH"
export LD_LIBRARY_PATH="${GUROBI_HOME}/lib"
export CASADI_GUROBI_VERSION="110"
export GUROBI_VERSION_URL="11.0.3"
export GUROBI_VERSION_URL_MAJOR="11.0"

export GUROBI_VERSION="$CASADI_GUROBI_VERSION"
export GRB_LICENSE_FILE="${DIR_TO_ROOT}/gurobi.lic"

PYTHONPATH="src/" python3 -m grow_worker.worker
