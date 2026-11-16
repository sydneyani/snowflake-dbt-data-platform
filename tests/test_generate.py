from __future__ import annotations

from datetime import date
from decimal import Decimal

from meridian.constants import (
    ORACLE_CANCELLED_LINES,
    ORACLE_CANCELLED_ORDERS,
    ORACLE_FREIGHT_DOC,
    ORACLE_IMBALANCE_DOC,
    ORACLE_PIT_INDEX,
    SAP_DUPLICATE_INDEX,
    SAP_FULLY_REJECTED_ORDERS,
    SAP_PIT_INDEX,
    SAP_REJECTED_LINES,
    SCD_NEW_CITY,
    TEST_ORDERS_PER_CUSTOMER,
    oracle_customer_id,
    sap_customer_id,
)
from meridian.ingest.exclude import oracle_line_exclusion, sap_line_exclusion
from meridian.ingest.generate import generate
from meridian.ingest.manifest import header_gaps


def test_same_seed_is_deterministic():
    first = generate(42)
    second = generate(42)
    assert first.manifest == second.manifest
    assert len(first.tables["sap_vbap"]) == len(second.tables["sap_vbap"])


def test_different_seed_changes_accepted_amount():
    first = Decimal(generate(42).manifest["sales"]["accepted_amount_doc"])
    second = Decimal(generate(7).manifest["sales"]["accepted_amount_doc"])
    assert first != second


def test_planted_exclusions_and_header_gap():
    dataset = generate(42)
    counts = dataset.manifest["sales"]["exclusion_counts"]
    assert counts["TEST_ACCOUNT"] == 2 * 2 * TEST_ORDERS_PER_CUSTOMER
    assert counts["INVALID_CURRENCY"] == 1
    assert counts["REJECTED_LINE"] == SAP_REJECTED_LINES
    assert counts["CANCELLED"] > ORACLE_CANCELLED_ORDERS
    gaps = dataset.manifest["headers"]["unexplained"]
    assert gaps == [
        {
            "source_system": "ORACLE_EBS",
            "sales_document": ORACLE_IMBALANCE_DOC,
            "residual": "25.00",
        }
    ]
    freight = next(
        header
        for header in dataset.tables["oracle_oe_order_headers_all"]
        if header["order_number"] == ORACLE_FREIGHT_DOC
    )
    assert freight["freight_charge"] == Decimal("50.00")
    assert (
        header_gaps(
            dataset.tables["sap_vbak"],
            dataset.tables["sap_vbap"],
            dataset.tables["oracle_oe_order_headers_all"],
            dataset.tables["oracle_oe_order_lines_all"],
        )
        == gaps
    )


def test_customer_history_and_duplicate_extract_row():
    dataset = generate(42)
    duplicate = sap_customer_id(SAP_DUPLICATE_INDEX)
    current = [row for row in dataset.tables["sap_kna1_t2"] if row["kunnr"] == duplicate]
    assert len(current) == 2
    history = [row for row in dataset.tables["sap_kna1_history"] if row["kunnr"] == duplicate]
    assert len(history) == 1

    pit = sap_customer_id(SAP_PIT_INDEX)
    versions = sorted(
        (row for row in dataset.tables["sap_kna1_history"] if row["kunnr"] == pit),
        key=lambda row: row["effective_date"],
    )
    assert [row["effective_date"] for row in versions] == [date(2024, 1, 1), date(2025, 11, 1)]
    assert versions[0]["ort01"] != SCD_NEW_CITY
    assert versions[1]["ort01"] == SCD_NEW_CITY

    oracle_id = oracle_customer_id(ORACLE_PIT_INDEX)
    oracle_versions = [
        row
        for row in dataset.tables["oracle_hz_cust_accounts_history"]
        if row["cust_account_id"] == oracle_id
    ]
    assert len(oracle_versions) == 2
    latest = max(oracle_versions, key=lambda row: row["effective_date"])
    assert latest["party_name"].endswith(" Holdings")

    t1_ids = {row["kunnr"] for row in dataset.tables["sap_kna1_t1"]}
    assert sap_customer_id(194) not in t1_ids
    assert sap_customer_id(194) in {row["kunnr"] for row in dataset.tables["sap_kna1_t2"]}


def test_orders_are_single_plant_single_currency():
    dataset = generate(42)
    lines: dict[str, list] = {}
    for line in dataset.tables["sap_vbap"]:
        lines.setdefault(line["vbeln"], []).append(line)
    headers = {header["vbeln"]: header for header in dataset.tables["sap_vbak"]}
    fully_rejected = 0
    for document, header in headers.items():
        group = lines[document]
        assert len({line["werks"] for line in group}) == 1
        assert len({line["waerk"] for line in group}) == 1
        assert header["werks"] == group[0]["werks"]
        assert header["waerk"] == group[0]["waerk"]
        if header["abstk"] == "C":
            fully_rejected += 1
            assert all(line["abgru"] == "Z1" for line in group)
    assert fully_rejected == SAP_FULLY_REJECTED_ORDERS


def test_exclusion_priority_test_account_wins():
    header = {"abstk": "C", "audat": date(2025, 1, 1)}
    line = {"abgru": "Z1", "waerk": "XXX", "kwmeng": None}
    customer = {"ktokd": "TEST"}
    assert sap_line_exclusion(header, line, customer, {}) == "TEST_ACCOUNT"

    oracle_header = {
        "flow_status_code": "CANCELLED",
        "ordered_date": date(2025, 1, 1),
        "transactional_curr_code": "XXX",
    }
    oracle_line = {"flow_status_code": "CANCELLED", "ordered_quantity": None}
    assert (
        oracle_line_exclusion(
            oracle_header,
            oracle_line,
            {"customer_class_code": "STANDARD"},
            {},
        )
        == "CANCELLED"
    )


def test_oracle_cancelled_line_quota():
    dataset = generate(42)
    cancelled_orders = {
        header["order_number"]
        for header in dataset.tables["oracle_oe_order_headers_all"]
        if header["flow_status_code"] == "CANCELLED"
    }
    assert len(cancelled_orders) == ORACLE_CANCELLED_ORDERS
    partial = [
        line
        for line in dataset.tables["oracle_oe_order_lines_all"]
        if line["flow_status_code"] == "CANCELLED" and line["order_number"] not in cancelled_orders
    ]
    assert len(partial) == ORACLE_CANCELLED_LINES
