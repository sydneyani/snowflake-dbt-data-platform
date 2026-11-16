"""Load the parquet lake into the DuckDB ``raw`` schema.

The loader is the only component that knows the warehouse file. dbt reads
tables; it does not read the lake directly. That is the same boundary a
Snowflake ``COPY INTO raw.*`` job would sit on.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from meridian.ingest.lake import AS_OF, CUSTOMER_PARTITIONS, LAKE_PATHS

FOUNDATION_TABLES = (
    "sap_vbak",
    "sap_vbap",
    "sap_mara",
    "sap_afko",
    "oracle_oe_order_headers_all",
    "oracle_oe_order_lines_all",
    "oracle_mtl_system_items_b",
    "oracle_wip_discrete_jobs",
    "ref_plants",
    "ref_fx_rates",
)


def reset_warehouse(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    wal = Path(str(db_path) + ".wal")
    if wal.exists():
        wal.unlink()


def load_foundation(db_path: Path, lake: Path) -> None:
    """Load facts, products, reference data, and the T1 customer masters."""

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as connection:
        connection.execute("create schema if not exists raw")
        for table in FOUNDATION_TABLES:
            _load(connection, table, lake / LAKE_PATHS[table] / "part-000.parquet")
        _load_customers(connection, lake, "t1")


def load_current_customers(db_path: Path, lake: Path) -> None:
    """Replace customer masters with the T2 image and load attribute history.

    History is loaded here, with the second extract, so the snapshot baseline
    (taken while the current tables still show T1) cannot see the later
    attribute values.
    """

    with duckdb.connect(str(db_path)) as connection:
        _load_customers(connection, lake, "t2")
        _load(
            connection,
            "sap_kna1_history",
            lake / LAKE_PATHS["sap_kna1_history"] / "part-000.parquet",
        )
        _load(
            connection,
            "oracle_hz_cust_accounts_history",
            lake / LAKE_PATHS["oracle_hz_cust_accounts_history"] / "part-000.parquet",
        )


def _load_customers(connection: duckdb.DuckDBPyConnection, lake: Path, label: str) -> None:
    for table, (relative, _parts) in CUSTOMER_PARTITIONS.items():
        path = lake / relative / f"as_of={AS_OF[label]}" / "part-000.parquet"
        _load(connection, table, path)


def _load(connection: duckdb.DuckDBPyConnection, table: str, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    connection.execute(
        f"create or replace table raw.{table} as select * from read_parquet(?)",
        [str(path)],
    )
