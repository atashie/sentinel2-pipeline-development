---
name: check
description: Run the CI gate locally (uv sync, ruff check, ruff format --check, pytest). Use before finishing any code or docs change.
allowed-tools: Bash(uv sync:*), Bash(uv run:*)
---

Run the same steps as `.github/workflows/ci.yml`, in this order. Stop at the first failure and report it.

1. `uv sync --locked`
2. `uv run ruff check .`
3. `uv run ruff format --check .`
4. `uv run pytest -q`

If step 3 fails, run `uv run ruff format .` and rerun from step 2.
If a test fails, report the test name and the assertion. Do not change a test to make it pass without saying so.
When every step passes, report the test count and the time.
