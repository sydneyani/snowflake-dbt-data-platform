"""Fixed dataset contract shared by the generator, tests, and reconciler.

Transactional noise follows ``SEED``. Identifiers below are reserved so tests
can point at a specific document without depending on the random stream.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

SEED = 42

AS_OF_T1 = date(2025, 6, 30)
AS_OF_T2 = date(2025, 12, 15)
SCD_CHANGE_DATE = date(2025, 11, 1)
LATE_CUSTOMER_DATE = date(2025, 10, 1)
CUSTOMER_CREATED = date(2024, 1, 1)

ORDER_START = date(2024, 1, 8)
ORDER_END = date(2025, 12, 10)

EXTRACTED_T1 = datetime(2025, 6, 30, 6, 0, 0)
EXTRACTED_T2 = datetime(2025, 12, 15, 6, 0, 0)
SCD_UPDATED_AT = datetime(2025, 11, 1, 0, 0, 0)
LATE_UPDATED_AT = datetime(2025, 10, 1, 0, 0, 0)
INITIAL_UPDATED_AT = datetime(2024, 1, 1, 0, 0, 0)

SAP_CUSTOMER_COUNT = 200
ORACLE_CUSTOMER_COUNT = 200
SHARED_TAX_COUNT = 30
SAP_PRODUCT_COUNT = 120
ORACLE_PRODUCT_COUNT = 120
SHARED_PRODUCT_COUNT = 40

SAP_ORDER_COUNT = 2500
ORACLE_ORDER_COUNT = 2000
SAP_WORK_ORDER_COUNT = 800
ORACLE_WORK_ORDER_COUNT = 600

SAP_FULLY_REJECTED_ORDERS = 25
SAP_REJECTED_LINES = 40
ORACLE_CANCELLED_ORDERS = 30
ORACLE_CANCELLED_LINES = 20
TEST_ORDERS_PER_CUSTOMER = 3

HEADER_FREIGHT = Decimal("50.00")
HEADER_IMBALANCE = Decimal("25.00")

VALID_CURRENCIES = frozenset({"USD", "EUR", "GBP"})

SAP_TEST_INDEXES = (199, 200)
SAP_LATE_INDEXES = (194, 195, 196, 197, 198)
SAP_SCD_INDEXES = tuple(range(17, 37))
SAP_DUPLICATE_INDEX = 42
SAP_PIT_INDEX = 17

ORACLE_TEST_INDEXES = (199, 200)
ORACLE_LATE_INDEXES = (194, 195, 196, 197, 198)
ORACLE_SCD_INDEXES = tuple(range(40, 50))
ORACLE_PIT_INDEX = 40

SAP_INVALID_CURRENCY_DOC = "0000042000"
SAP_PIT_BEFORE_DOC = "0000042201"
SAP_PIT_AFTER_DOC = "0000042202"
ORACLE_FREIGHT_DOC = "500420"
ORACLE_IMBALANCE_DOC = "500421"
ORACLE_PIT_BEFORE_DOC = "500422"
ORACLE_PIT_AFTER_DOC = "500423"

SCD_OLD_CITY = "Columbus"
SCD_OLD_REGION = "OH"
SCD_OLD_POSTAL = "43004"
SCD_NEW_CITY = "Austin"
SCD_NEW_REGION = "TX"
SCD_NEW_POSTAL = "78701"
SCD_CREDIT_DELTA = Decimal("5000.00")

PIT_BEFORE_DATE = date(2025, 6, 15)
PIT_AFTER_DATE = date(2025, 11, 20)


def sap_customer_id(index: int) -> str:
    return f"{index:010d}"


def oracle_customer_id(index: int) -> str:
    return str(300_000 + index)


def shared_tax_id(index: int) -> str:
    return f"TAX-{index:05d}"


def sap_test_docs() -> tuple[str, ...]:
    return tuple(
        f"00000421{n:02d}" for n in range(1, len(SAP_TEST_INDEXES) * TEST_ORDERS_PER_CUSTOMER + 1)
    )


def oracle_test_docs() -> tuple[str, ...]:
    start = 500431
    count = len(ORACLE_TEST_INDEXES) * TEST_ORDERS_PER_CUSTOMER
    return tuple(str(start + offset) for offset in range(count))
