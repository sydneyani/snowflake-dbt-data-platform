import pytest

pytest.importorskip("dagster")


@pytest.mark.integration
def test_definitions_include_ingest_and_marts():
    from meridian.orchestration.definitions import defs

    keys = {key.to_user_string() for key in defs.resolve_all_asset_keys()}
    assert "lake_extract" in keys
    assert "raw_foundation" in keys
    assert "customer_snapshot_baseline" in keys
    assert "raw_customers_current" in keys
    assert "reconciliation_report" in keys
    assert any(key.endswith("fct_sales_order_lines") for key in keys)
    assert defs.resolve_job_def("daily_erp_refresh").name == "daily_erp_refresh"
