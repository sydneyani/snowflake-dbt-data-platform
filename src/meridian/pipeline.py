"""Run extract, the two snapshot passes, dbt build, and reconciliation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from meridian.config import lake_dir, repo_root, reports_dir, transform_dir
from meridian.ingest.generate import generate
from meridian.ingest.lake import write_lake
from meridian.ingest.load import load_current_customers, load_foundation, reset_warehouse
from meridian.quality.reconcile import ReconciliationReport, reconcile
from meridian.quality.report import write_report


def run_pipeline(root: Path | None = None, seed: int = 42) -> ReconciliationReport:
    root = (root or repo_root()).resolve()
    transform = transform_dir()
    database = (root / "data" / "warehouse" / "meridian.duckdb").resolve()
    previous_db = os.environ.get("MERIDIAN_DUCKDB_PATH")
    previous_root = os.environ.get("MERIDIAN_ROOT")
    os.environ["MERIDIAN_DUCKDB_PATH"] = str(database)
    os.environ["MERIDIAN_ROOT"] = str(root)
    try:
        dataset = generate(seed)
        lake = lake_dir(root)
        write_lake(dataset, lake)
        reset_warehouse(database)
        load_foundation(database, lake)
        _dbt(["deps"], transform)
        # The closed-row test is a child of the snapshot, so a plain
        # `+snap_customer` build would run it before the second extract.
        _dbt(
            [
                "build",
                "--select",
                "+snap_customer",
                "--exclude",
                "assert_snapshot_closed_rows",
            ],
            transform,
        )
        load_current_customers(database, lake)
        _dbt(["build"], transform)
        report = reconcile(database, lake / "manifest.json")
        write_report(report, reports_dir(root))
        return report
    finally:
        _restore("MERIDIAN_DUCKDB_PATH", previous_db)
        _restore("MERIDIAN_ROOT", previous_root)


def _restore(name: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def _dbt(args: list[str], transform: Path) -> None:
    command = [
        "dbt",
        *args,
        "--project-dir",
        str(transform),
        "--profiles-dir",
        str(transform),
        "--target",
        "duckdb",
    ]
    env = os.environ.copy()
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    env["DO_NOT_TRACK"] = "1"
    subprocess.run(command, check=True, env=env, cwd=transform.parent)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Meridian ELT pipeline.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run_pipeline(args.root, args.seed)
    sys.stdout.write(report.to_markdown())
    if report.status != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
