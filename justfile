# Development tasks

# Install dependencies with dev group
install:
    uv sync --locked --group dev

# Run linter checks
lint:
    uv run ruff check ./src ./unit_test

# Fix linting issues
format:
    uv run ruff format ./src ./unit_test

# Check formatting without modifying files
format-check:
    uv run ruff format --check ./src ./unit_test

# Run type checker
typecheck:
    uv run ty check ./src ./unit_test

# Run unit tests
test:
    uv run pytest --junit-xml=test-results.xml unit_test/

# Run integration tests explicitly
test-integration:
    uv run pytest -m integration --no-cov --junit-xml=test-results.xml unit_test/

# Run all checks (install, lint, format-check, typecheck, test)
ci: install lint format-check typecheck test

# Show this help message
help:
    @just --list
