"""Re-run reconciliation against an existing warehouse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from meridian.config import lake_dir, repo_root, reports_dir, warehouse_path
from meridian.quality.reconcile import reconcile
from meridian.quality.report import write_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reconcile raw tables to marts.")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    report = reconcile(warehouse_path(root), lake_dir(root) / "manifest.json")
    paths = write_report(report, reports_dir(root))
    sys.stdout.write(report.to_markdown())
    print(f"wrote {paths['markdown']}")
    if report.status != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
