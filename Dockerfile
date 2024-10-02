FROM python:3.8-slim-bookworm

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

COPY requirements.txt /app/grow_worker/requirements.txt
RUN pip install -r /app/grow_worker/requirements.txt --no-cache-dir

COPY src/grow_worker                 /app/grow_worker/

CMD ["python3", "-m", "grow_worker.worker"]
