# Optimizer worker

Prefect flow repo for the NWN optimizer.\
This defines the prefect flow function which is the entry function for prefect runs.\
There is a [prefect_deploy_flow.py](src/omotes_optimizer_worker/prefect_deploy_flow.py) script to create/update a
prefect deployment which can be used for runs.

## Development

### Tools

This project uses:

- **uv**: Fast Python package manager and resolver. Install via [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- **just**: Command runner for common tasks (similar to Make). Install via
  [https://github.com/casey/just](https://github.com/casey/just)

### Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Copy [.env.template](.env.template) to [.env](.env)

**Note** to use local code for sdk run `.venv/bin/pip install -e ../omotes-sdk-python/`.

### Run/debug the prefect flow function locally

In vscode go to the debug view and run `run_optimizer_flow_function`. This runs the function without prefect.

### Lint/typecheck/test locally

Run via just (also used in in github actions):

```bash
just ci            # run all CI checks (lint, security, format-check, typecheck, test)

just lint          # ruff checks
just security      # ruff security
just format        # ruff format
just format-check  # verify formatting
just typecheck     # ty type checking
just test          # pytest
```

To debug test go to the debug view in vscode and run "pytest".\
When using an editable install of the sdk, don't use the just command as `uv run ...` will remove this editable install.

### Deploy flow to prefect

There are different ways to deploy prefect flow.

- to a local prefect instance using local code
- automatic on github CI
- manual via omotes-system repo: https://github.com/Project-OMOTES/omotes-system

#### local prefect deployment

In vscode go to the debug view and run `prefect_deploy_flow`.\
This will create a deployment on prefect (to the prefect instance on `PREFECT_API_URL`).\

During development you may want to deploy local code of this repo instead of an already published image, then set
`PREFECT_USE_LOCAL_CODE_AND_IMAGE=true` in [.env](.env). To also use local code for the omotes-sdk-python and mesido set
`PREFECT_USE_LOCAL_SDK_AND_MESIDO=true` as well.

#### deployment via Github CI

On git tag the prefect flow is deployed to the NWN TEST MapEditor. The deployment to the NWN PROD MapEditor needs
confirmation which can be set on clicking the deploy action: https://github.com/Project-OMOTES/optimizer-worker/actions.

### Update mesido version and deploy flow on NWN MapEditor environments

Update the mesido version in [pyproject.toml](pyproject.toml), then update [uv.lock](uv.lock) and run the checks:

```bash
uv lock
uv sync --locked --group dev
just ci
```

Commit both [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock) to a PR and merge into main.

Next create a new release on https://github.com/Project-OMOTES/optimizer-worker/releases:

1. Tag: Select tag: Create new tag
2. Previous tag: Select previous
3. Generate release notes
4. Publish release

This will publish a new docker image and deploy to NWN MapEditor TEST, approval is needed to deploy to PROD:
https://github.com/Project-OMOTES/optimizer-worker/actions.

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
│   ├── test_prefect_flow.py        # Tests for optimizer flow behavior
│   ├── data/
│   │   └── esdl/
│   │       ├── Delft_T.esdl         # Successful optimizer flow input
│   │       └── Delft_T_feedback.esdl # Feedback/error flow input
│   └── test_worker_types.py         # Tests for worker type mapping logic
├── local_run/
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
