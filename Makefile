ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export PATH := $(HOME)/.local/bin:$(PATH)
export MERIDIAN_ROOT := $(ROOT)
export MERIDIAN_DUCKDB_PATH := $(ROOT)/data/warehouse/meridian.duckdb
export DBT_SEND_ANONYMOUS_USAGE_STATS := false

.DEFAULT_GOAL := help

.PHONY: help setup extract pipeline test lint sqlfluff dagster ci

help:
	@printf '%s\n' \
		'setup      Install dependencies with uv' \
		'extract    Write the parquet lake' \
		'pipeline   Extract, snapshot, dbt build, reconcile' \
		'test       Run unit and integration tests' \
		'lint       Ruff check and format check' \
		'sqlfluff   Lint dbt SQL' \
		'dagster    Open the Dagster UI' \
		'ci         lint, test, and sqlfluff'

setup:
	uv sync --frozen --all-groups

extract:
	uv run meridian-extract --root $(ROOT)

pipeline:
	uv run meridian-pipeline --root $(ROOT)

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

sqlfluff:
	uv run sqlfluff lint transform/models transform/macros transform/snapshots transform/tests

dagster:
	uv run dagster dev -m meridian.orchestration.definitions

ci: lint test sqlfluff
