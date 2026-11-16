"""Deterministic SAP ECC and Oracle EBS extracts.

The generator is a stand-in for the ERP extractors. Identifiers, planted
defects, and customer history are fixed. Order lines, quantities, and work
orders follow ``SEED`` so a rerun produces the same lake.

Every order is single-plant, single-customer, and single-currency. Header
amount equals the sum of line amounts plus header freight, except one planted
Oracle imbalance.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from meridian.constants import (
    CUSTOMER_CREATED,
    EXTRACTED_T1,
    EXTRACTED_T2,
    HEADER_FREIGHT,
    HEADER_IMBALANCE,
    INITIAL_UPDATED_AT,
    LATE_CUSTOMER_DATE,
    LATE_UPDATED_AT,
    ORACLE_CANCELLED_LINES,
    ORACLE_CANCELLED_ORDERS,
    ORACLE_CUSTOMER_COUNT,
    ORACLE_FREIGHT_DOC,
    ORACLE_IMBALANCE_DOC,
    ORACLE_LATE_INDEXES,
    ORACLE_ORDER_COUNT,
    ORACLE_PIT_AFTER_DOC,
    ORACLE_PIT_BEFORE_DOC,
    ORACLE_PIT_INDEX,
    ORACLE_PRODUCT_COUNT,
    ORACLE_SCD_INDEXES,
    ORACLE_TEST_INDEXES,
    ORACLE_WORK_ORDER_COUNT,
    ORDER_END,
    ORDER_START,
    PIT_AFTER_DATE,
    PIT_BEFORE_DATE,
    SAP_CUSTOMER_COUNT,
    SAP_DUPLICATE_INDEX,
    SAP_FULLY_REJECTED_ORDERS,
    SAP_INVALID_CURRENCY_DOC,
    SAP_LATE_INDEXES,
    SAP_ORDER_COUNT,
    SAP_PIT_AFTER_DOC,
    SAP_PIT_BEFORE_DOC,
    SAP_PIT_INDEX,
    SAP_PRODUCT_COUNT,
    SAP_REJECTED_LINES,
    SAP_SCD_INDEXES,
    SAP_TEST_INDEXES,
    SAP_WORK_ORDER_COUNT,
    SCD_CHANGE_DATE,
    SCD_CREDIT_DELTA,
    SCD_NEW_CITY,
    SCD_NEW_POSTAL,
    SCD_NEW_REGION,
    SCD_OLD_CITY,
    SCD_OLD_POSTAL,
    SCD_OLD_REGION,
    SCD_UPDATED_AT,
    SEED,
    SHARED_PRODUCT_COUNT,
    SHARED_TAX_COUNT,
    TEST_ORDERS_PER_CUSTOMER,
    oracle_customer_id,
    oracle_test_docs,
    sap_customer_id,
    sap_test_docs,
    shared_tax_id,
)
from meridian.ingest.manifest import build_manifest
from meridian.ingest.schemas import row

ZERO = Decimal("0.00")
ZERO_QTY = Decimal("0.000")

_CITIES = (
    ("Columbus", "OH", "43004", "US"),
    ("Dallas", "TX", "75001", "US"),
    ("Chicago", "IL", "60601", "US"),
    ("Phoenix", "AZ", "85001", "US"),
    ("Newark", "NJ", "07102", "US"),
    ("Hamburg", "HH", "20095", "DE"),
    ("Rotterdam", "ZH", "3011", "NL"),
    ("Munich", "BY", "80331", "DE"),
    ("Atlanta", "GA", "30301", "US"),
    ("Denver", "CO", "80202", "US"),
    ("Seattle", "WA", "98101", "US"),
    ("Toronto", "ON", "M5V 2T6", "CA"),
)

_NAME_A = (
    "Cedar",
    "Harbor",
    "Summit",
    "Pioneer",
    "Redwood",
    "Lakeshore",
    "Iron",
    "Prairie",
    "Cobalt",
    "Granite",
)
_NAME_B = ("Ridge", "Field", "Point", "Works", "Line", "Forge", "Gate", "Brook")
_NAME_C = ("Manufacturing", "Components", "Logistics", "Systems", "Industries")

_GROUPS = ("Bearings", "Motors", "Sensors", "Fasteners", "Hydraulics", "Electrical")
_COMPONENTS = ("Assembly", "Housing", "Kit", "Module", "Valve", "Drive")


@dataclass(frozen=True)
class Dataset:
    tables: dict[str, list[dict]]
    manifest: dict


def _q(value: Decimal | int, scale: str) -> Decimal:
    return Decimal(value).quantize(Decimal(scale))


def _company_name(index: int) -> str:
    return (
        f"{_NAME_A[index % len(_NAME_A)]} "
        f"{_NAME_B[(index * 3) % len(_NAME_B)]} "
        f"{_NAME_C[(index * 7) % len(_NAME_C)]} {index:03d}"
    )


def _price(index: int) -> Decimal:
    dollars = Decimal(10 + (index % 50))
    cents = Decimal((index % 4) * 25) / Decimal(100)
    return _q(dollars + cents, "0.01")


def _plants() -> list[dict]:
    specs = (
        ("SAP_ECC", "1000", "Chicago Plant", "US01", "US", "Midwest"),
        ("SAP_ECC", "2000", "Dallas Plant", "US01", "US", "South"),
        ("SAP_ECC", "3000", "Hamburg Plant", "DE01", "DE", "North"),
        ("ORACLE_EBS", "101", "Newark DC", "101", "US", "Northeast"),
        ("ORACLE_EBS", "202", "Phoenix DC", "202", "US", "Southwest"),
        ("ORACLE_EBS", "303", "Rotterdam DC", "303", "NL", "Europe"),
    )
    return [
        row(
            "ref_plants",
            source_system=source,
            plant_code=code,
            plant_name=name,
            company_code=company,
            country_code=country,
            region_name=region,
            extracted_at=EXTRACTED_T2,
        )
        for source, code, name, company, country, region in specs
    ]


def _sap_products() -> list[dict]:
    items = []
    for index in range(1, SAP_PRODUCT_COUNT + 1):
        gtin = (
            f"{12_345_670_00000 + index:014d}"
            if index <= SHARED_PRODUCT_COUNT
            else f"{22_345_670_00000 + index:014d}"
        )
        matnr = f"MAT-{index:06d}"
        items.append(
            {
                "id": matnr,
                "unit_price": _price(index),
                "record": row(
                    "sap_mara",
                    matnr=matnr,
                    maktx=(
                        f"{_GROUPS[index % len(_GROUPS)]} "
                        f"{_COMPONENTS[index % len(_COMPONENTS)]} {index:04d}"
                    ),
                    matkl=_GROUPS[index % len(_GROUPS)].upper(),
                    meins="EA",
                    ean11=gtin,
                    mtart="FERT",
                    extracted_at=EXTRACTED_T2,
                ),
            }
        )
    return items


def _oracle_products() -> list[dict]:
    items = []
    for index in range(1, ORACLE_PRODUCT_COUNT + 1):
        gtin = (
            f"{12_345_670_00000 + index:014d}"
            if index <= SHARED_PRODUCT_COUNT
            else f"{32_345_670_00000 + index:014d}"
        )
        segment = f"ITEM-{index:06d}"
        items.append(
            {
                "id": segment,
                "unit_price": _price(index + 3),
                "record": row(
                    "oracle_mtl_system_items_b",
                    inventory_item_id=str(800_000 + index),
                    segment1=segment,
                    description=(
                        f"{_GROUPS[(index + 1) % len(_GROUPS)]} "
                        f"{_COMPONENTS[(index + 2) % len(_COMPONENTS)]} {index:04d}"
                    ),
                    primary_uom_code="EA",
                    item_type="FG",
                    gtin=gtin,
                    organization_id="101",
                    extracted_at=EXTRACTED_T2,
                ),
            }
        )
    return items


def _fx_rates() -> list[dict]:
    rows: list[dict] = []
    day = date(2024, 1, 1)
    end = date(2026, 12, 31)
    while day <= end:
        index = (day - date(2024, 1, 1)).days
        rates = {
            "USD": Decimal("1.000000"),
            "EUR": Decimal("1.080000") + (Decimal(index % 17) / Decimal(10000)),
            "GBP": Decimal("1.270000") + (Decimal(index % 19) / Decimal(10000)),
        }
        for currency, rate in rates.items():
            rows.append(
                row(
                    "ref_fx_rates",
                    rate_date=day,
                    currency_code=currency,
                    usd_rate=_q(rate, "0.000001"),
                    extracted_at=EXTRACTED_T2,
                )
            )
        day += timedelta(days=1)
    return rows


def _city(index: int) -> tuple[str, str, str, str]:
    return _CITIES[index % len(_CITIES)]


def _credit(index: int) -> Decimal:
    return _q(Decimal(20_000 + index * 1_000), "0.01")


def _customers() -> dict[str, list[dict]]:
    sap_t1: list[dict] = []
    sap_t2: list[dict] = []
    sap_history: list[dict] = []
    for index in range(1, SAP_CUSTOMER_COUNT + 1):
        late = index in SAP_LATE_INDEXES
        changed = index in SAP_SCD_INDEXES
        account_group = "TEST" if index in SAP_TEST_INDEXES else "SOLD"
        tax = shared_tax_id(index) if index <= SHARED_TAX_COUNT else f"TAX-S-{index:05d}"
        city, region, postal, country = _city(index)
        if changed:
            city, region, postal, country = SCD_OLD_CITY, SCD_OLD_REGION, SCD_OLD_POSTAL, "US"
        created = LATE_CUSTOMER_DATE if late else CUSTOMER_CREATED
        base_name = _company_name(index)
        credit = _credit(index)
        common = {
            "kunnr": sap_customer_id(index),
            "land1": country,
            "stras": f"{100 + index} Market Street",
            "ktokd": account_group,
            "stceg": tax,
            "loevm": None,
            "erdat": created,
        }
        current = row(
            "sap_kna1",
            name1=base_name,
            regio=region,
            ort01=city,
            pstlz=postal,
            credit_limit=credit,
            updated_at=INITIAL_UPDATED_AT,
            extracted_at=EXTRACTED_T1,
            **common,
        )
        if changed:
            updated = row(
                "sap_kna1",
                name1=base_name,
                regio=SCD_NEW_REGION,
                ort01=SCD_NEW_CITY,
                pstlz=SCD_NEW_POSTAL,
                credit_limit=_q(credit + SCD_CREDIT_DELTA, "0.01"),
                updated_at=SCD_UPDATED_AT,
                extracted_at=EXTRACTED_T2,
                **common,
            )
        else:
            updated = row(
                "sap_kna1",
                name1=current["name1"],
                regio=current["regio"],
                ort01=current["ort01"],
                pstlz=current["pstlz"],
                credit_limit=current["credit_limit"],
                updated_at=LATE_UPDATED_AT if late else INITIAL_UPDATED_AT,
                extracted_at=EXTRACTED_T2,
                **common,
            )
        if not late:
            sap_t1.append(current)
            sap_history.append(_sap_history_from(current, CUSTOMER_CREATED))
        else:
            sap_history.append(_sap_history_from(updated, LATE_CUSTOMER_DATE))
        sap_t2.append(updated)
        if changed:
            sap_history.append(_sap_history_from(updated, SCD_CHANGE_DATE))

    duplicate_id = sap_customer_id(SAP_DUPLICATE_INDEX)
    for batch, extracted in ((sap_t1, EXTRACTED_T1), (sap_t2, EXTRACTED_T2)):
        original = next(item for item in batch if item["kunnr"] == duplicate_id)
        batch.append(
            row(
                "sap_kna1",
                **{
                    **original,
                    "name1": f"{original['name1']} DUP",
                    "extracted_at": extracted.replace(hour=5),
                },
            )
        )

    oracle_t1: list[dict] = []
    oracle_t2: list[dict] = []
    oracle_history: list[dict] = []
    for index in range(1, ORACLE_CUSTOMER_COUNT + 1):
        late = index in ORACLE_LATE_INDEXES
        changed = index in ORACLE_SCD_INDEXES
        customer_class = "TEST" if index in ORACLE_TEST_INDEXES else "STANDARD"
        tax = shared_tax_id(index) if index <= SHARED_TAX_COUNT else f"TAX-O-{index:05d}"
        city, region, postal, country = _city(index + 5)
        created = LATE_CUSTOMER_DATE if late else CUSTOMER_CREATED
        base_name = f"{_company_name(index + 50)} Oracle"
        credit = _credit(index + 20)
        common = {
            "cust_account_id": oracle_customer_id(index),
            "country": country,
            "state": region,
            "city": city,
            "postal_code": postal,
            "address1": f"{200 + index} Industrial Ave",
            "customer_class_code": customer_class,
            "tax_reference": tax,
            "status": "A",
            "creation_date": created,
        }
        current = row(
            "oracle_hz_cust_accounts",
            party_name=base_name,
            credit_limit=credit,
            last_update_date=INITIAL_UPDATED_AT,
            extracted_at=EXTRACTED_T1,
            **common,
        )
        if changed:
            updated = row(
                "oracle_hz_cust_accounts",
                party_name=f"{base_name} Holdings",
                credit_limit=_q(credit + SCD_CREDIT_DELTA, "0.01"),
                last_update_date=SCD_UPDATED_AT,
                extracted_at=EXTRACTED_T2,
                **common,
            )
        else:
            updated = row(
                "oracle_hz_cust_accounts",
                party_name=current["party_name"],
                credit_limit=current["credit_limit"],
                last_update_date=LATE_UPDATED_AT if late else INITIAL_UPDATED_AT,
                extracted_at=EXTRACTED_T2,
                **common,
            )
        if not late:
            oracle_t1.append(current)
            oracle_history.append(_oracle_history_from(current, CUSTOMER_CREATED))
        else:
            oracle_history.append(_oracle_history_from(updated, LATE_CUSTOMER_DATE))
        oracle_t2.append(updated)
        if changed:
            oracle_history.append(_oracle_history_from(updated, SCD_CHANGE_DATE))

    return {
        "sap_t1": sap_t1,
        "sap_t2": sap_t2,
        "sap_history": sap_history,
        "oracle_t1": oracle_t1,
        "oracle_t2": oracle_t2,
        "oracle_history": oracle_history,
    }


def _sap_history_from(current: dict, effective: date) -> dict:
    payload = {key: value for key, value in current.items() if key != "extracted_at"}
    return row(
        "sap_kna1_history",
        effective_date=effective,
        extracted_at=EXTRACTED_T2,
        **payload,
    )


def _oracle_history_from(current: dict, effective: date) -> dict:
    payload = {key: value for key, value in current.items() if key != "extracted_at"}
    return row(
        "oracle_hz_cust_accounts_history",
        effective_date=effective,
        extracted_at=EXTRACTED_T2,
        **payload,
    )


def _pick_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randrange((end - start).days + 1))


def _sap_orders(rng, customers, products, plants) -> tuple[list[dict], list[dict]]:
    headers: list[dict] = []
    lines: list[dict] = []
    sap_plants = [plant for plant in plants if plant["source_system"] == "SAP_ECC"]
    pool: dict[str, dict] = {}
    for item in customers["sap_t2"]:
        existing = pool.get(item["kunnr"])
        if existing is None or item["extracted_at"] > existing["extracted_at"]:
            pool[item["kunnr"]] = item
    late_ids = {sap_customer_id(index) for index in SAP_LATE_INDEXES}
    test_ids = {sap_customer_id(index) for index in SAP_TEST_INDEXES}
    regular = [
        pool[sap_customer_id(index)]
        for index in range(1, SAP_CUSTOMER_COUNT + 1)
        if sap_customer_id(index) not in late_ids and sap_customer_id(index) not in test_ids
    ]
    late = [pool[sap_customer_id(index)] for index in SAP_LATE_INDEXES]

    for sequence in range(1, SAP_ORDER_COUNT + 1):
        if rng.randrange(100) < 8:
            customer = late[rng.randrange(len(late))]
            order_date = _pick_date(rng, LATE_CUSTOMER_DATE, ORDER_END)
        else:
            customer = regular[rng.randrange(len(regular))]
            order_date = _pick_date(rng, ORDER_START, ORDER_END)
        plant = sap_plants[rng.randrange(len(sap_plants))]
        currency = rng.choices(("USD", "EUR", "GBP"), weights=(70, 20, 10))[0]
        order_type = "RE" if rng.randrange(100) < 4 else "TA"
        header, order_lines = _sap_document(
            rng,
            vbeln=f"{1_000_000 + sequence:010d}",
            customer=customer,
            plant=plant,
            products=products,
            currency=currency,
            order_date=order_date,
            auart=order_type,
            line_count=1 + rng.randrange(3),
        )
        headers.append(header)
        lines.extend(order_lines)
    return headers, lines


def _sap_document(
    rng: random.Random | None,
    *,
    vbeln: str,
    customer: dict,
    plant: dict,
    products: list[dict],
    currency: str,
    order_date: date,
    auart: str,
    line_count: int,
    fixed_lines: list[tuple[dict, Decimal]] | None = None,
) -> tuple[dict, list[dict]]:
    header = row(
        "sap_vbak",
        vbeln=vbeln,
        erdat=order_date,
        audat=order_date,
        vdatu=order_date + timedelta(days=7),
        auart=auart,
        vkorg=plant["company_code"],
        kunnr=customer["kunnr"],
        waerk=currency,
        netwr=ZERO,
        header_freight=ZERO,
        bukrs=plant["company_code"],
        werks=plant["plant_code"],
        gbstk="C" if order_date < date(2025, 9, 1) else "A",
        abstk="A",
        extracted_at=EXTRACTED_T2,
    )
    lines: list[dict] = []
    specs = fixed_lines
    if specs is None:
        assert rng is not None
        specs = []
        for _ in range(line_count):
            product = products[rng.randrange(len(products))]
            qty = Decimal(1 + rng.randrange(20))
            specs.append((product, qty))
    for offset, (product, qty) in enumerate(specs, start=1):
        amount = _q(qty * product["unit_price"], "0.01")
        if auart == "RE":
            amount = -amount
        lines.append(
            row(
                "sap_vbap",
                vbeln=vbeln,
                posnr=f"{offset * 10:06d}",
                matnr=product["id"],
                kwmeng=_q(qty, "0.001"),
                vrkme="EA",
                netpr=product["unit_price"],
                netwr=amount,
                waerk=currency,
                werks=plant["plant_code"],
                abgru=None,
                erdat=order_date,
                extracted_at=EXTRACTED_T2,
            )
        )
    return header, lines


def _append_explicit_sap(headers, lines, customers, products, plants) -> None:
    pool = {item["kunnr"]: item for item in customers["sap_t2"]}
    plant = next(item for item in plants if item["plant_code"] == "1000")
    product = products[0]

    def add(vbeln: str, customer_index: int, order_date: date, currency: str = "USD", qty: int = 4):
        customer = pool[sap_customer_id(customer_index)]
        header, order_lines = _sap_document(
            None,
            vbeln=vbeln,
            customer=customer,
            plant=plant,
            products=products,
            currency=currency,
            order_date=order_date,
            auart="TA",
            line_count=1,
            fixed_lines=[(product, Decimal(qty))],
        )
        headers.append(header)
        lines.extend(order_lines)
        return header, order_lines

    header, order_lines = add(SAP_INVALID_CURRENCY_DOC, 1, date(2025, 3, 12), currency="XXX")
    header["waerk"] = "XXX"
    for line in order_lines:
        line["waerk"] = "XXX"

    docs = iter(sap_test_docs())
    for index in SAP_TEST_INDEXES:
        for nth in range(TEST_ORDERS_PER_CUSTOMER):
            add(next(docs), index, date(2025, 4, 1) + timedelta(days=nth * 10), qty=2)

    add(SAP_PIT_BEFORE_DOC, SAP_PIT_INDEX, PIT_BEFORE_DATE, qty=4)
    add(SAP_PIT_AFTER_DOC, SAP_PIT_INDEX, PIT_AFTER_DATE, qty=4)


def _oracle_orders(rng, customers, products, plants) -> tuple[list[dict], list[dict]]:
    headers: list[dict] = []
    lines: list[dict] = []
    oracle_plants = [plant for plant in plants if plant["source_system"] == "ORACLE_EBS"]
    late_ids = {oracle_customer_id(index) for index in ORACLE_LATE_INDEXES}
    test_ids = {oracle_customer_id(index) for index in ORACLE_TEST_INDEXES}
    pool = {item["cust_account_id"]: item for item in customers["oracle_t2"]}
    regular = [
        pool[oracle_customer_id(index)]
        for index in range(1, ORACLE_CUSTOMER_COUNT + 1)
        if oracle_customer_id(index) not in late_ids and oracle_customer_id(index) not in test_ids
    ]
    late = [pool[oracle_customer_id(index)] for index in ORACLE_LATE_INDEXES]

    for sequence in range(1, ORACLE_ORDER_COUNT + 1):
        if rng.randrange(100) < 8:
            customer = late[rng.randrange(len(late))]
            order_date = _pick_date(rng, LATE_CUSTOMER_DATE, ORDER_END)
        else:
            customer = regular[rng.randrange(len(regular))]
            order_date = _pick_date(rng, ORDER_START, ORDER_END)
        plant = oracle_plants[rng.randrange(len(oracle_plants))]
        currency = rng.choices(("USD", "EUR", "GBP"), weights=(70, 20, 10))[0]
        order_type = "RETURN" if rng.randrange(100) < 4 else "STANDARD"
        header, order_lines = _oracle_document(
            rng,
            order_number=str(6_000_000 + sequence),
            customer=customer,
            plant=plant,
            products=products,
            currency=currency,
            order_date=order_date,
            order_type=order_type,
            line_count=1 + rng.randrange(3),
        )
        headers.append(header)
        lines.extend(order_lines)
    return headers, lines


def _oracle_document(
    rng: random.Random | None,
    *,
    order_number: str,
    customer: dict,
    plant: dict,
    products: list[dict],
    currency: str,
    order_date: date,
    order_type: str,
    line_count: int,
    fixed_lines: list[tuple[dict, Decimal]] | None = None,
) -> tuple[dict, list[dict]]:
    closed = order_date < date(2025, 9, 1)
    header = row(
        "oracle_oe_order_headers_all",
        order_number=order_number,
        ordered_date=order_date,
        request_date=order_date + timedelta(days=7),
        order_type=order_type,
        sold_to_customer_id=customer["cust_account_id"],
        transactional_curr_code=currency,
        header_total=ZERO,
        freight_charge=ZERO,
        flow_status_code="CLOSED" if closed else "BOOKED",
        ship_from_org_id=plant["plant_code"],
        extracted_at=EXTRACTED_T2,
    )
    specs = fixed_lines
    if specs is None:
        assert rng is not None
        specs = []
        for _ in range(line_count):
            product = products[rng.randrange(len(products))]
            specs.append((product, Decimal(1 + rng.randrange(20))))
    lines = []
    for offset, (product, qty) in enumerate(specs, start=1):
        amount = _q(qty * product["unit_price"], "0.01")
        if order_type == "RETURN":
            amount = -amount
        lines.append(
            row(
                "oracle_oe_order_lines_all",
                order_number=order_number,
                line_number=offset,
                ordered_item=product["id"],
                ordered_quantity=_q(qty, "0.001"),
                unit_selling_price=product["unit_price"],
                extended_price=amount,
                flow_status_code="SHIPPED" if closed else "AWAITING_SHIPPING",
                request_date=header["request_date"],
                ship_from_org_id=plant["plant_code"],
                extracted_at=EXTRACTED_T2,
            )
        )
    return header, lines


def _append_explicit_oracle(headers, lines, customers, products, plants) -> None:
    pool = {item["cust_account_id"]: item for item in customers["oracle_t2"]}
    plant = next(item for item in plants if item["plant_code"] == "101")
    product = products[0]

    def add(order_number: str, customer_index: int, order_date: date, qty: int = 4):
        header, order_lines = _oracle_document(
            None,
            order_number=order_number,
            customer=pool[oracle_customer_id(customer_index)],
            plant=plant,
            products=products,
            currency="USD",
            order_date=order_date,
            order_type="STANDARD",
            line_count=1,
            fixed_lines=[(product, Decimal(qty))],
        )
        headers.append(header)
        lines.extend(order_lines)
        return header

    freight = add(ORACLE_FREIGHT_DOC, 2, date(2025, 5, 6), qty=5)
    freight["freight_charge"] = HEADER_FREIGHT
    add(ORACLE_IMBALANCE_DOC, 3, date(2025, 5, 7), qty=6)
    docs = iter(oracle_test_docs())
    for index in ORACLE_TEST_INDEXES:
        for nth in range(TEST_ORDERS_PER_CUSTOMER):
            add(next(docs), index, date(2025, 4, 5) + timedelta(days=nth * 9), qty=2)
    add(ORACLE_PIT_BEFORE_DOC, ORACLE_PIT_INDEX, PIT_BEFORE_DATE, qty=3)
    add(ORACLE_PIT_AFTER_DOC, ORACLE_PIT_INDEX, PIT_AFTER_DATE, qty=3)


def _reserved_sap_docs() -> set[str]:
    return {
        SAP_INVALID_CURRENCY_DOC,
        SAP_PIT_BEFORE_DOC,
        SAP_PIT_AFTER_DOC,
        *sap_test_docs(),
    }


def _reserved_oracle_docs() -> set[str]:
    return {
        ORACLE_FREIGHT_DOC,
        ORACLE_IMBALANCE_DOC,
        ORACLE_PIT_BEFORE_DOC,
        ORACLE_PIT_AFTER_DOC,
        *oracle_test_docs(),
    }


def _apply_sap_line_anomalies(headers: list[dict], lines: list[dict]) -> None:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        by_doc[line["vbeln"]].append(line)
    reserved = _reserved_sap_docs()
    eligible = sorted(
        (
            header
            for header in headers
            if header["vbeln"] not in reserved and header["auart"] == "TA"
        ),
        key=lambda header: header["vbeln"],
    )
    fully = eligible[:SAP_FULLY_REJECTED_ORDERS]
    if len(fully) != SAP_FULLY_REJECTED_ORDERS:
        raise RuntimeError("not enough SAP orders to plant full rejections")
    full_ids = set()
    for header in fully:
        header["abstk"] = "C"
        header["gbstk"] = "C"
        full_ids.add(header["vbeln"])
        for line in by_doc[header["vbeln"]]:
            line["abgru"] = "Z1"
    planted = 0
    for header in eligible:
        if header["vbeln"] in full_ids:
            continue
        for line in by_doc[header["vbeln"]]:
            if line["abgru"] is None:
                line["abgru"] = "Z1"
                planted += 1
                if planted == SAP_REJECTED_LINES:
                    return
    raise RuntimeError(f"planted {planted} rejected SAP lines, needed {SAP_REJECTED_LINES}")


def _apply_oracle_line_anomalies(headers: list[dict], lines: list[dict]) -> None:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        by_doc[line["order_number"]].append(line)
    reserved = _reserved_oracle_docs()
    eligible = sorted(
        (
            header
            for header in headers
            if header["order_number"] not in reserved and header["order_type"] == "STANDARD"
        ),
        key=lambda header: header["order_number"],
    )
    fully = eligible[:ORACLE_CANCELLED_ORDERS]
    if len(fully) != ORACLE_CANCELLED_ORDERS:
        raise RuntimeError("not enough Oracle orders to plant cancellations")
    full_ids = set()
    for header in fully:
        header["flow_status_code"] = "CANCELLED"
        full_ids.add(header["order_number"])
        for line in by_doc[header["order_number"]]:
            line["flow_status_code"] = "CANCELLED"
    planted = 0
    for header in eligible:
        if header["order_number"] in full_ids:
            continue
        for line in by_doc[header["order_number"]]:
            if line["flow_status_code"] != "CANCELLED":
                line["flow_status_code"] = "CANCELLED"
                planted += 1
                if planted == ORACLE_CANCELLED_LINES:
                    return
    raise RuntimeError(f"planted {planted} cancelled Oracle lines, needed {ORACLE_CANCELLED_LINES}")


def _finalize_sap(headers: list[dict], lines: list[dict]) -> None:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        by_doc[line["vbeln"]].append(line)
    for header in headers:
        total = sum((line["netwr"] for line in by_doc[header["vbeln"]]), ZERO)
        header["netwr"] = _q(total + header["header_freight"], "0.01")


def _finalize_oracle(headers: list[dict], lines: list[dict]) -> None:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        by_doc[line["order_number"]].append(line)
    for header in headers:
        total = sum((line["extended_price"] for line in by_doc[header["order_number"]]), ZERO)
        header["header_total"] = _q(total + header["freight_charge"], "0.01")
        if header["order_number"] == ORACLE_IMBALANCE_DOC:
            header["header_total"] = _q(header["header_total"] + HEADER_IMBALANCE, "0.01")


def _sap_work_orders(rng, products, plants) -> list[dict]:
    sap_plants = [plant for plant in plants if plant["source_system"] == "SAP_ECC"]
    rows = []
    for sequence in range(1, SAP_WORK_ORDER_COUNT + 1):
        product = products[rng.randrange(len(products))]
        plant = sap_plants[rng.randrange(len(sap_plants))]
        start = _pick_date(rng, ORDER_START, date(2025, 11, 15))
        finish = start + timedelta(days=5 + rng.randrange(35))
        planned = _q(Decimal(10 + rng.randrange(190)), "0.001")
        roll = rng.randrange(100)
        if roll < 15:
            status, completed, scrap, actual = "CRTD", ZERO_QTY, ZERO_QTY, None
        elif roll < 40:
            status = "PCNF"
            completed = _q(planned / 2, "0.001")
            scrap = ZERO_QTY
            actual = None
        else:
            status = "TECO"
            scrap = _q(Decimal(rng.randrange(3)), "0.001")
            completed = _q(planned - scrap, "0.001")
            actual = finish + timedelta(days=rng.randrange(-3, 8))
        rows.append(
            row(
                "sap_afko",
                aufnr=f"WO1{sequence:07d}",
                plnbez=product["id"],
                werks=plant["plant_code"],
                bukrs=plant["company_code"],
                auart="PP01",
                gamng=planned,
                igmng=completed,
                scrap_qty=scrap,
                gstrp=start,
                gltrp=finish,
                actual_finish=actual,
                status=status,
                extracted_at=EXTRACTED_T2,
            )
        )
    return rows


def _oracle_work_orders(rng, products, plants) -> list[dict]:
    oracle_plants = [plant for plant in plants if plant["source_system"] == "ORACLE_EBS"]
    rows = []
    for sequence in range(1, ORACLE_WORK_ORDER_COUNT + 1):
        product = products[rng.randrange(len(products))]
        plant = oracle_plants[rng.randrange(len(oracle_plants))]
        start = _pick_date(rng, ORDER_START, date(2025, 11, 15))
        finish = start + timedelta(days=5 + rng.randrange(35))
        planned = _q(Decimal(10 + rng.randrange(190)), "0.001")
        roll = rng.randrange(100)
        if roll < 15:
            status, completed, scrap, actual = "Unreleased", ZERO_QTY, ZERO_QTY, None
        elif roll < 40:
            status = "Released"
            completed = _q(planned / 2, "0.001")
            scrap = ZERO_QTY
            actual = None
        else:
            status = "Closed"
            scrap = _q(Decimal(rng.randrange(3)), "0.001")
            completed = _q(planned - scrap, "0.001")
            actual = finish + timedelta(days=rng.randrange(-3, 8))
        rows.append(
            row(
                "oracle_wip_discrete_jobs",
                wip_entity_name=f"WIP{sequence:07d}",
                organization_id=plant["plant_code"],
                primary_item_segment=product["id"],
                class_code="Discrete",
                status_type=status,
                start_quantity=planned,
                quantity_completed=completed,
                quantity_scrapped=scrap,
                scheduled_start_date=start,
                scheduled_completion_date=finish,
                date_completed=actual,
                extracted_at=EXTRACTED_T2,
            )
        )
    return rows


def generate(seed: int = SEED) -> Dataset:
    rng = random.Random(seed)
    plants = _plants()
    sap_products = _sap_products()
    oracle_products = _oracle_products()
    customers = _customers()
    fx_rates = _fx_rates()

    sap_headers, sap_lines = _sap_orders(rng, customers, sap_products, plants)
    _append_explicit_sap(sap_headers, sap_lines, customers, sap_products, plants)
    oracle_headers, oracle_lines = _oracle_orders(rng, customers, oracle_products, plants)
    _append_explicit_oracle(oracle_headers, oracle_lines, customers, oracle_products, plants)
    _apply_sap_line_anomalies(sap_headers, sap_lines)
    _apply_oracle_line_anomalies(oracle_headers, oracle_lines)
    _finalize_sap(sap_headers, sap_lines)
    _finalize_oracle(oracle_headers, oracle_lines)

    parts: dict[str, list[dict]] = {
        "sap_vbak": sap_headers,
        "sap_vbap": sap_lines,
        "sap_kna1_t1": customers["sap_t1"],
        "sap_kna1_t2": customers["sap_t2"],
        "sap_kna1_history": customers["sap_history"],
        "sap_mara": [item["record"] for item in sap_products],
        "sap_afko": _sap_work_orders(rng, sap_products, plants),
        "oracle_oe_order_headers_all": oracle_headers,
        "oracle_oe_order_lines_all": oracle_lines,
        "oracle_hz_cust_accounts_t1": customers["oracle_t1"],
        "oracle_hz_cust_accounts_t2": customers["oracle_t2"],
        "oracle_hz_cust_accounts_history": customers["oracle_history"],
        "oracle_mtl_system_items_b": [item["record"] for item in oracle_products],
        "oracle_wip_discrete_jobs": _oracle_work_orders(rng, oracle_products, plants),
        "ref_plants": plants,
        "ref_fx_rates": fx_rates,
    }
    manifest = build_manifest(parts)
    manifest["seed"] = seed
    return Dataset(tables=parts, manifest=manifest)
