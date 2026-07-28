# Optimizer worker

Prefect flow repo for the NWN optimizer.\
This defines the prefect flow function which is the entry function for prefect runs.\
There is a `prefect_deploy_flow` script to create/update a prefect deployment which can be used for runs.

## Development

### Tools

This project uses:

- **uv**: Fast Python package manager and resolver. Install via [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- **just**: Command runner for common tasks (similar to Make). Install via [https://github.com/casey/just](https://github.com/casey/just)

### Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Copy `.env.template` to `.env`

**Note** to use local code for sdk run `.venv/bin/pip install -e ../omotes-sdk-python/`.

### Run/debug the prefect flow function locally

In vscode go to the debug view and run `run_optimizer_flow_function`. This runs the function without prefect.

### Lint/typecheck/test locally

Run via just (also used in in github actions):

```bash
just ci            # run all CI checks (lint, format-check, typecheck, test)

just lint          # ruff checks
just format        # ruff format
just format-check  # verify formatting
just typecheck     # ty type checking
just test          # pytest
```

To debug test go to the debug view in vscode and run "pytest".\
When using an editable install of the sdk, don't use the just command as `uv run ...` will remove this editable install.

### Deploy flow to prefect

In vscode go to the debug view and run `prefect_deploy_flow`.\
This will create a deployment on prefect (to the prefect instance on `PREFECT_API_URL`).\

During development you may want to deploy local code of this repo instead of an already published image, then set `PREFECT_USE_LOCAL_CODE_AND_IMAGE=true` in `.env`.
To also use local code for the omoted-sdk-python and mesido set `PREFECT_USE_LOCAL_SDK_AND_MESIDO=true` as well.

## Project Structure

```text
optimizer-worker/
├── src/
│   └── omotes_optimizer_worker/
│       ├── __init__.py             # Package initialization
│       ├── env.py                  # Environment configuration helpers
│       ├── prefect_deploy_flow.py  # Registers/updates Prefect deployment
│       ├── prefect_flow.py         # Main Prefect flow implementation
│       └── worker_types.py         # Workflow/solver mapping utilities
├── tests/
│   ├── test_prefect_deploy_flow.py # Tests for deploy flow module behavior
│   └── test_worker_types.py        # Tests for worker type mapping logic
├── local_test/
│   ├── Delft_T.esdl                # Local test input ESDL
│   ├── Delft_T feedback.esdl       # Local test output/feedback ESDL
│   └── run_optimizer_flow_function.py # Run flow function locally without Prefect
├── doc/                            # Project documentation assets
├── gurobi/
│   └── gurobi.lic                  # Local Gurobi license file
├── Dockerfile                      # Runtime image for optimizer worker
├── dev.Dockerfile                  # Local development image (monorepo/local SDK mode)
├── justfile                        # Task runner commands (ci, lint, typecheck, test)
├── pyproject.toml                  # Dependencies and project metadata
└── README.md
```
