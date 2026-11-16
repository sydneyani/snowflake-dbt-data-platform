"""Paths and runtime configuration.

The warehouse file and the lake live under ``data/`` and are generated, not
committed. ``MERIDIAN_ROOT`` overrides discovery when the package is imported
from a virtualenv.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    override = os.environ.get("MERIDIAN_ROOT")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "meridian").exists():
            return candidate
    return Path.cwd().resolve()


def lake_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "data" / "lake"


def warehouse_path(root: Path | None = None) -> Path:
    override = os.environ.get("MERIDIAN_DUCKDB_PATH")
    if override:
        return Path(override).resolve()
    return (root or repo_root()) / "data" / "warehouse" / "meridian.duckdb"


def reports_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "data" / "reports"


def transform_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "transform"
