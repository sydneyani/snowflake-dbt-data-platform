from __future__ import annotations

from meridian.constants import AS_OF_T1, SAP_PIT_INDEX, SCD_NEW_CITY, sap_customer_id
from meridian.ingest.generate import generate
from meridian.ingest.lake import write_lake
from meridian.ingest.load import load_current_customers, load_foundation, reset_warehouse


def test_load_switches_customer_as_of(tmp_path):
    dataset = generate(42)
    lake = tmp_path / "lake"
    write_lake(dataset, lake)
    database = tmp_path / "warehouse" / "meridian.duckdb"
    reset_warehouse(database)
    load_foundation(database, lake)

    import duckdb

    pit = sap_customer_id(SAP_PIT_INDEX)
    with duckdb.connect(str(database)) as connection:
        city = connection.execute(
            "select ort01 from raw.sap_kna1 where kunnr = ?",
            [pit],
        ).fetchone()[0]
        assert city != SCD_NEW_CITY
        history = connection.execute(
            "select count(*) from information_schema.tables "
            "where table_schema = 'raw' and table_name = 'sap_kna1_history'"
        ).fetchone()[0]
        assert history == 0
        orders = connection.execute("select count(*) from raw.sap_vbak").fetchone()[0]
        assert orders == dataset.manifest["row_counts"]["sap_vbak"]

    load_current_customers(database, lake)
    with duckdb.connect(str(database)) as connection:
        city = connection.execute(
            "select ort01 from raw.sap_kna1 where kunnr = ? order by extracted_at desc limit 1",
            [pit],
        ).fetchone()[0]
        assert city == SCD_NEW_CITY
        versions = connection.execute(
            "select count(*) from raw.sap_kna1_history where kunnr = ?",
            [pit],
        ).fetchone()[0]
        assert versions == 2

    assert (lake / "sap" / "kna1" / f"as_of={AS_OF_T1.isoformat()}" / "part-000.parquet").exists()
