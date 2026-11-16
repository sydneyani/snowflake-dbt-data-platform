"""Exclusion rules shared by the extract manifest and the warehouse checks.

dbt model ``int_sales_lines`` repeats this priority in SQL. The integration
test fails if the two implementations disagree.

Priority (first match wins):

1. TEST_ACCOUNT — customer is a test account group / class
2. CANCELLED — header rejected or cancelled, or the line itself is cancelled
3. REJECTED_LINE — SAP item rejection reason on an otherwise open order
4. INVALID_CURRENCY — currency outside USD, EUR, GBP
5. MISSING_QUANTITY — null quantity
6. MISSING_FX — no rate for that currency on the order date
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from meridian.constants import VALID_CURRENCIES


def sap_line_exclusion(
    header: dict,
    line: dict,
    customer: dict,
    fx_rates: dict[tuple[date, str], Decimal],
) -> str | None:
    if customer["ktokd"] == "TEST":
        return "TEST_ACCOUNT"
    if header["abstk"] == "C":
        return "CANCELLED"
    if line["abgru"] is not None:
        return "REJECTED_LINE"
    if line["waerk"] not in VALID_CURRENCIES:
        return "INVALID_CURRENCY"
    if line["kwmeng"] is None:
        return "MISSING_QUANTITY"
    if (header["audat"], line["waerk"]) not in fx_rates:
        return "MISSING_FX"
    return None


def oracle_line_exclusion(
    header: dict,
    line: dict,
    customer: dict,
    fx_rates: dict[tuple[date, str], Decimal],
) -> str | None:
    if customer["customer_class_code"] == "TEST":
        return "TEST_ACCOUNT"
    if header["flow_status_code"] == "CANCELLED" or line["flow_status_code"] == "CANCELLED":
        return "CANCELLED"
    if header["transactional_curr_code"] not in VALID_CURRENCIES:
        return "INVALID_CURRENCY"
    if line["ordered_quantity"] is None:
        return "MISSING_QUANTITY"
    if (header["ordered_date"], header["transactional_curr_code"]) not in fx_rates:
        return "MISSING_FX"
    return None
