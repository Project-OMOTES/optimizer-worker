FROM python:3.11-slim-bookworm

WORKDIR /app
RUN apt update && \
    apt install -y wget && \
    apt-get clean

ENV GUROBI_HOME=/app/gurobi/
ENV PATH="/app/gurobi/bin:$PATH"
ENV LD_LIBRARY_PATH="/app/gurobi/lib"
ENV CASADI_GUROBI_VERSION="110"
ENV GUROBI_VERSION_URL="11.0.3"
ENV GUROBI_VERSION_URL_MAJOR="11.0"

# This env var is for casadi.
ENV GUROBI_VERSION="$CASADI_GUROBI_VERSION"

# This env var is for gurobi
ENV GRB_LICENSE_FILE="/app/gurobi/gurobi.lic"

RUN mkdir -p /app/gurobi && \
    wget -qO- https://packages.gurobi.com/${GUROBI_VERSION_URL_MAJOR}/gurobi${GUROBI_VERSION_URL}_linux64.tar.gz | tar xvz --strip-components=2 -C /app/gurobi

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

WORKDIR /src

# install dependencies, avoid using Gurobi's embedded python
ENV UV_PYTHON=/usr/local/bin/python3.11
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
# enable running commands without 'uv run'
ENV PATH="/src/.venv/bin:$PATH"

COPY src .
