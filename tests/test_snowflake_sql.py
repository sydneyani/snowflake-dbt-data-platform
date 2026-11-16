from meridian.ingest.snowflake_load import copy_into_sql, load_statements


def test_copy_into_names_the_table_and_parquet_format():
    sql = copy_into_sql("sap_vbak", "meridian_raw")
    assert "copy into raw.sap_vbak" in sql
    assert "from @meridian_raw/sap/vbak/" in sql
    assert "type = parquet" in sql
    assert "match_by_column_name = case_insensitive" in sql


def test_every_lake_table_has_a_statement():
    statements = load_statements()
    assert any("raw.sap_vbak" in statement for statement in statements)
    assert any("raw.oracle_wip_discrete_jobs" in statement for statement in statements)


def test_unknown_table_is_rejected():
    try:
        copy_into_sql("not_a_table", "meridian_raw")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("expected ValueError")
