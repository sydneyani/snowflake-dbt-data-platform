import os
from pathlib import Path

import pytest

from meridian.constants import SAP_PIT_AFTER_DOC, SCD_NEW_CITY
from meridian.pipeline import run_pipeline


@pytest.mark.integration
def test_pipeline_ties_and_writes_a_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    report = run_pipeline(tmp_path, seed=42)
    assert report.status == "PASS"
    names = {check.name: check for check in report.checks}
    assert names["sales_accepted_doc_total"].status == "PASS"
    assert names["header_tie_out"].status == "EXPLAINED"
    assert names["header_tie_out"].variance == "25.00"
    assert names["customer_point_in_time"].status == "PASS"
    assert names["customer_point_in_time"].target_value == SCD_NEW_CITY
    assert names["customer_snapshot_closed_versions"].target_value == "30"
    markdown = tmp_path / "data" / "reports" / "reconciliation.md"
    assert markdown.exists()
    assert "Pipeline status: PASS" in markdown.read_text(encoding="utf-8")
    assert SAP_PIT_AFTER_DOC
    assert "MERIDIAN_DUCKDB_PATH" not in os.environ or not str(
        os.environ["MERIDIAN_DUCKDB_PATH"]
    ).startswith(str(tmp_path))
