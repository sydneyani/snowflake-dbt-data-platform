"""Write the generated extracts to a parquet lake."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from meridian.constants import AS_OF_T1, AS_OF_T2
from meridian.ingest.generate import Dataset
from meridian.ingest.schemas import SCHEMAS

# Logical table -> lake directory. Customer masters are partitioned by as-of.
LAKE_PATHS: dict[str, str] = {
    "sap_vbak": "sap/vbak",
    "sap_vbap": "sap/vbap",
    "sap_kna1_history": "sap/kna1_history",
    "sap_mara": "sap/mara",
    "sap_afko": "sap/afko",
    "oracle_oe_order_headers_all": "oracle/oe_order_headers_all",
    "oracle_oe_order_lines_all": "oracle/oe_order_lines_all",
    "oracle_hz_cust_accounts_history": "oracle/hz_cust_accounts_history",
    "oracle_mtl_system_items_b": "oracle/mtl_system_items_b",
    "oracle_wip_discrete_jobs": "oracle/wip_discrete_jobs",
    "ref_plants": "reference/plants",
    "ref_fx_rates": "reference/fx_rates",
}

CUSTOMER_PARTITIONS: dict[str, tuple[str, dict[str, str]]] = {
    "sap_kna1": (
        "sap/kna1",
        {"t1": "sap_kna1_t1", "t2": "sap_kna1_t2"},
    ),
    "oracle_hz_cust_accounts": (
        "oracle/hz_cust_accounts",
        {"t1": "oracle_hz_cust_accounts_t1", "t2": "oracle_hz_cust_accounts_t2"},
    ),
}

AS_OF = {"t1": AS_OF_T1.isoformat(), "t2": AS_OF_T2.isoformat()}


def write_lake(dataset: Dataset, lake: Path) -> Path:
    if lake.exists():
        for child in lake.rglob("*"):
            if child.is_file():
                child.unlink()
    for table, relative in LAKE_PATHS.items():
        schema_name = table
        _write(lake / relative / "part-000.parquet", dataset.tables[table], SCHEMAS[schema_name])
    for _table, (relative, parts) in CUSTOMER_PARTITIONS.items():
        for label, source_name in parts.items():
            destination = lake / relative / f"as_of={AS_OF[label]}" / "part-000.parquet"
            _write(destination, dataset.tables[source_name], SCHEMAS[source_name])
    manifest_path = lake / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(dataset.manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _write(path: Path, rows: list[dict], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        missing = [name for name in schema.names if name not in rows[0]]
        if missing:
            raise KeyError(f"{path} missing columns {missing}")
    arrays = [pa.array([row[field.name] for row in rows], type=field.type) for field in schema]
    pq.write_table(pa.Table.from_arrays(arrays, schema=schema), path)
