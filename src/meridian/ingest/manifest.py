"""Control totals computed from the in-memory extract, before dbt runs."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from meridian.constants import (
    ORACLE_IMBALANCE_DOC,
    SAP_DUPLICATE_INDEX,
    sap_customer_id,
)
from meridian.ingest.exclude import oracle_line_exclusion, sap_line_exclusion


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _dedupe_customers(rows: list[dict], key: str) -> dict[str, dict]:
    chosen: dict[str, dict] = {}
    for row in rows:
        current = chosen.get(row[key])
        if current is None or row["extracted_at"] >= current["extracted_at"]:
            chosen[row[key]] = row
    return chosen


def header_gaps(
    sap_headers: list[dict],
    sap_lines: list[dict],
    oracle_headers: list[dict],
    oracle_lines: list[dict],
) -> list[dict[str, str]]:
    """Orders whose header amount is not lines + freight.

    A residual of zero means the header ties. Non-zero residuals are source
    defects, not pipeline defects: the line grain is still loaded faithfully.
    """

    sap_by: dict[str, list[dict]] = defaultdict(list)
    for line in sap_lines:
        sap_by[line["vbeln"]].append(line)
    oracle_by: dict[str, list[dict]] = defaultdict(list)
    for line in oracle_lines:
        oracle_by[line["order_number"]].append(line)

    gaps: list[dict[str, str]] = []
    for header in sap_headers:
        line_sum = sum((line["netwr"] for line in sap_by[header["vbeln"]]), Decimal("0.00"))
        residual = (header["netwr"] - line_sum - header["header_freight"]).quantize(Decimal("0.01"))
        if residual != 0:
            gaps.append(
                {
                    "source_system": "SAP_ECC",
                    "sales_document": header["vbeln"],
                    "residual": _money(residual),
                }
            )
    for header in oracle_headers:
        line_sum = sum(
            (line["extended_price"] for line in oracle_by[header["order_number"]]),
            Decimal("0.00"),
        )
        residual = (header["header_total"] - line_sum - header["freight_charge"]).quantize(
            Decimal("0.01")
        )
        if residual != 0:
            gaps.append(
                {
                    "source_system": "ORACLE_EBS",
                    "sales_document": header["order_number"],
                    "residual": _money(residual),
                }
            )
    return sorted(gaps, key=lambda item: (item["source_system"], item["sales_document"]))


def build_manifest(parts: dict[str, list[dict]]) -> dict:
    fx_rates = {
        (row["rate_date"], row["currency_code"]): row["usd_rate"] for row in parts["ref_fx_rates"]
    }
    sap_customers = _dedupe_customers(parts["sap_kna1_t2"], "kunnr")
    oracle_customers = _dedupe_customers(parts["oracle_hz_cust_accounts_t2"], "cust_account_id")

    exclusion_counts: dict[str, int] = defaultdict(int)
    exclusion_amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    accepted_amount = Decimal("0.00")
    accepted_lines = 0
    gross_lines = 0

    sap_by = {header["vbeln"]: header for header in parts["sap_vbak"]}
    for line in parts["sap_vbap"]:
        header = sap_by[line["vbeln"]]
        reason = sap_line_exclusion(header, line, sap_customers[header["kunnr"]], fx_rates)
        gross_lines += 1
        if reason is None:
            accepted_lines += 1
            accepted_amount += line["netwr"]
        else:
            exclusion_counts[reason] += 1
            exclusion_amounts[reason] += line["netwr"]

    oracle_by = {header["order_number"]: header for header in parts["oracle_oe_order_headers_all"]}
    for line in parts["oracle_oe_order_lines_all"]:
        header = oracle_by[line["order_number"]]
        reason = oracle_line_exclusion(
            header,
            line,
            oracle_customers[header["sold_to_customer_id"]],
            fx_rates,
        )
        gross_lines += 1
        if reason is None:
            accepted_lines += 1
            accepted_amount += line["extended_price"]
        else:
            exclusion_counts[reason] += 1
            exclusion_amounts[reason] += line["extended_price"]

    planned_qty = sum((row["gamng"] for row in parts["sap_afko"]), Decimal("0.000"))
    planned_qty += sum(
        (row["start_quantity"] for row in parts["oracle_wip_discrete_jobs"]),
        Decimal("0.000"),
    )

    gaps = header_gaps(
        parts["sap_vbak"],
        parts["sap_vbap"],
        parts["oracle_oe_order_headers_all"],
        parts["oracle_oe_order_lines_all"],
    )

    row_counts = {name: len(rows) for name, rows in parts.items()}
    return {
        "seed": 42,
        "as_of": {"t1": "2025-06-30", "t2": "2025-12-15", "scd_change": "2025-11-01"},
        "row_counts": row_counts,
        "sales": {
            "gross_line_count": gross_lines,
            "accepted_line_count": accepted_lines,
            "accepted_amount_doc": _money(accepted_amount),
            "exclusion_counts": dict(sorted(exclusion_counts.items())),
            "exclusion_amounts_doc": {
                key: _money(value) for key, value in sorted(exclusion_amounts.items())
            },
        },
        "headers": {"unexplained": gaps},
        "work_orders": {
            "count": len(parts["sap_afko"]) + len(parts["oracle_wip_discrete_jobs"]),
            "planned_qty": format(planned_qty.quantize(Decimal("0.001")), "f"),
        },
        "customers": {
            "sap_duplicate_id": sap_customer_id(SAP_DUPLICATE_INDEX),
            "sap_t1_rows": len(parts["sap_kna1_t1"]),
            "sap_t2_rows": len(parts["sap_kna1_t2"]),
            "sap_history_rows": len(parts["sap_kna1_history"]),
            "oracle_t1_rows": len(parts["oracle_hz_cust_accounts_t1"]),
            "oracle_t2_rows": len(parts["oracle_hz_cust_accounts_t2"]),
            "oracle_history_rows": len(parts["oracle_hz_cust_accounts_history"]),
        },
        "anomalies": {
            "invalid_currency_document": "0000042000",
            "freight_document": "500420",
            "imbalance_document": ORACLE_IMBALANCE_DOC,
            "imbalance_amount": _money(Decimal("25.00")),
            "freight_amount": _money(Decimal("50.00")),
        },
    }
