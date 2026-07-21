# Optimizer worker

to test locally run:

```
docker-compose up
```

The local_test service can be run multiple times.
The result exit code is printed in each `local_test` test app output.

For testing during development keep `rabbitmq` and `omotes_influxdd` running and run:

```
docker-compose up --build grow_worker local_test
```

## Just

Just is a command runner used for CI checks. This allows to run the exacts same checks locally.

### Installation

**Linux / WSL:**

```bash
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

**macOS:**

```bash
brew install just
```

**Windows (with Scoop):**

```bash
scoop install just
```

**Windows (with Chocolatey):**

```bash
choco install just
```

**Or download directly from releases:**
Visit https://github.com/casey/just/releases and download the binary for your OS.

**Verify installation:**

```bash
just --version
```

### Usage

Just commands:

```bash
just ci          # Run all checks (lint, typecheck, test)

just install     # Install dependencies
just lint        # Run linter
just format      # Fix formatting
just typecheck   # Run type checker
just test        # Run tests
just help        # Show all available tasks
```
