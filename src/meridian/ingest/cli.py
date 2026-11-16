"""Write the raw lake. Does not load the warehouse or run dbt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from meridian.config import lake_dir, repo_root
from meridian.ingest.generate import generate
from meridian.ingest.lake import write_lake


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the Meridian raw lake (parquet).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    dataset = generate(args.seed)
    manifest_path = write_lake(dataset, lake_dir(root))
    sales = dataset.manifest["sales"]
    print(f"lake: {manifest_path.parent}")
    print(f"manifest: {manifest_path}")
    print(
        "accepted lines: "
        f"{sales['accepted_line_count']}  "
        f"amount_doc: {sales['accepted_amount_doc']}"
    )
    print("exclusion counts: " + json.dumps(sales["exclusion_counts"]))
    print("header gaps: " + json.dumps(dataset.manifest["headers"]["unexplained"]))


if __name__ == "__main__":
    main()
