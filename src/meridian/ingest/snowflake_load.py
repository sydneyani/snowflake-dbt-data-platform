"""SQL for loading the parquet lake into Snowflake RAW.

CI does not connect to Snowflake. ``copy_into_sql`` is covered by a unit test.
``load_lake`` runs only when ``dbt-snowflake`` / the connector extra is installed
and the caller passes a connection.
"""

from __future__ import annotations

from pathlib import Path

from meridian.ingest.lake import LAKE_PATHS

RAW_TABLES = tuple(LAKE_PATHS)


def copy_into_sql(table: str, stage: str) -> str:
    if table not in RAW_TABLES:
        raise ValueError(f"unknown raw table {table}")
    if not stage or any(token in stage for token in (" ", ";", "\n")):
        raise ValueError("stage name must be a single identifier path")
    return (
        f"copy into raw.{table}\n"
        f"from @{stage}/{LAKE_PATHS[table]}/\n"
        "file_format = (type = parquet)\n"
        "match_by_column_name = case_insensitive"
    )


def load_statements(stage: str = "meridian_raw") -> list[str]:
    return [copy_into_sql(table, stage) for table in RAW_TABLES]


def load_lake(connection: object, lake: Path, stage: str = "meridian_raw") -> None:
    """Execute PUT and COPY for each non-customer table.

    Customer as-of partitions are loaded by the caller with the same statement
    shape. This function is intentionally not used by the local pipeline.
    """

    cursor = connection.cursor()
    try:
        for table, relative in LAKE_PATHS.items():
            path = lake / relative / "part-000.parquet"
            cursor.execute(f"put file://{path} @{stage}/{relative}/ auto_compress=false")
            cursor.execute(copy_into_sql(table, stage))
    finally:
        cursor.close()
