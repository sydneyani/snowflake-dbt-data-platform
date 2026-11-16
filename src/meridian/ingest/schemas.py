"""PyArrow schemas for raw extracts.

Column order is the contract ``row()`` enforces. Staging models rename these
fields; they do not invent new source columns.
"""

from __future__ import annotations

import pyarrow as pa

STRING = pa.string()
DATE = pa.date32()
TS = pa.timestamp("us")
MONEY = pa.decimal128(18, 2)
QTY = pa.decimal128(18, 3)
PRICE = pa.decimal128(18, 4)
RATE = pa.decimal128(18, 6)
INT = pa.int64()


def _schema(fields: list[tuple[str, pa.DataType]]) -> pa.Schema:
    return pa.schema(fields)


SCHEMAS: dict[str, pa.Schema] = {
    "sap_vbak": _schema(
        [
            ("vbeln", STRING),
            ("erdat", DATE),
            ("audat", DATE),
            ("vdatu", DATE),
            ("auart", STRING),
            ("vkorg", STRING),
            ("kunnr", STRING),
            ("waerk", STRING),
            ("netwr", MONEY),
            ("header_freight", MONEY),
            ("bukrs", STRING),
            ("werks", STRING),
            ("gbstk", STRING),
            ("abstk", STRING),
            ("extracted_at", TS),
        ]
    ),
    "sap_vbap": _schema(
        [
            ("vbeln", STRING),
            ("posnr", STRING),
            ("matnr", STRING),
            ("kwmeng", QTY),
            ("vrkme", STRING),
            ("netpr", PRICE),
            ("netwr", MONEY),
            ("waerk", STRING),
            ("werks", STRING),
            ("abgru", STRING),
            ("erdat", DATE),
            ("extracted_at", TS),
        ]
    ),
    "sap_kna1": _schema(
        [
            ("kunnr", STRING),
            ("name1", STRING),
            ("land1", STRING),
            ("regio", STRING),
            ("ort01", STRING),
            ("pstlz", STRING),
            ("stras", STRING),
            ("ktokd", STRING),
            ("stceg", STRING),
            ("credit_limit", MONEY),
            ("loevm", STRING),
            ("erdat", DATE),
            ("updated_at", TS),
            ("extracted_at", TS),
        ]
    ),
    "sap_kna1_history": _schema(
        [
            ("kunnr", STRING),
            ("name1", STRING),
            ("land1", STRING),
            ("regio", STRING),
            ("ort01", STRING),
            ("pstlz", STRING),
            ("stras", STRING),
            ("ktokd", STRING),
            ("stceg", STRING),
            ("credit_limit", MONEY),
            ("loevm", STRING),
            ("erdat", DATE),
            ("updated_at", TS),
            ("effective_date", DATE),
            ("extracted_at", TS),
        ]
    ),
    "sap_mara": _schema(
        [
            ("matnr", STRING),
            ("maktx", STRING),
            ("matkl", STRING),
            ("meins", STRING),
            ("ean11", STRING),
            ("mtart", STRING),
            ("extracted_at", TS),
        ]
    ),
    "sap_afko": _schema(
        [
            ("aufnr", STRING),
            ("plnbez", STRING),
            ("werks", STRING),
            ("bukrs", STRING),
            ("auart", STRING),
            ("gamng", QTY),
            ("igmng", QTY),
            ("scrap_qty", QTY),
            ("gstrp", DATE),
            ("gltrp", DATE),
            ("actual_finish", DATE),
            ("status", STRING),
            ("extracted_at", TS),
        ]
    ),
    "oracle_oe_order_headers_all": _schema(
        [
            ("order_number", STRING),
            ("ordered_date", DATE),
            ("request_date", DATE),
            ("order_type", STRING),
            ("sold_to_customer_id", STRING),
            ("transactional_curr_code", STRING),
            ("header_total", MONEY),
            ("freight_charge", MONEY),
            ("flow_status_code", STRING),
            ("ship_from_org_id", STRING),
            ("extracted_at", TS),
        ]
    ),
    "oracle_oe_order_lines_all": _schema(
        [
            ("order_number", STRING),
            ("line_number", INT),
            ("ordered_item", STRING),
            ("ordered_quantity", QTY),
            ("unit_selling_price", PRICE),
            ("extended_price", MONEY),
            ("flow_status_code", STRING),
            ("request_date", DATE),
            ("ship_from_org_id", STRING),
            ("extracted_at", TS),
        ]
    ),
    "oracle_hz_cust_accounts": _schema(
        [
            ("cust_account_id", STRING),
            ("party_name", STRING),
            ("country", STRING),
            ("state", STRING),
            ("city", STRING),
            ("postal_code", STRING),
            ("address1", STRING),
            ("customer_class_code", STRING),
            ("tax_reference", STRING),
            ("credit_limit", MONEY),
            ("status", STRING),
            ("creation_date", DATE),
            ("last_update_date", TS),
            ("extracted_at", TS),
        ]
    ),
    "oracle_hz_cust_accounts_history": _schema(
        [
            ("cust_account_id", STRING),
            ("party_name", STRING),
            ("country", STRING),
            ("state", STRING),
            ("city", STRING),
            ("postal_code", STRING),
            ("address1", STRING),
            ("customer_class_code", STRING),
            ("tax_reference", STRING),
            ("credit_limit", MONEY),
            ("status", STRING),
            ("creation_date", DATE),
            ("last_update_date", TS),
            ("effective_date", DATE),
            ("extracted_at", TS),
        ]
    ),
    "oracle_mtl_system_items_b": _schema(
        [
            ("inventory_item_id", STRING),
            ("segment1", STRING),
            ("description", STRING),
            ("primary_uom_code", STRING),
            ("item_type", STRING),
            ("gtin", STRING),
            ("organization_id", STRING),
            ("extracted_at", TS),
        ]
    ),
    "oracle_wip_discrete_jobs": _schema(
        [
            ("wip_entity_name", STRING),
            ("organization_id", STRING),
            ("primary_item_segment", STRING),
            ("class_code", STRING),
            ("status_type", STRING),
            ("start_quantity", QTY),
            ("quantity_completed", QTY),
            ("quantity_scrapped", QTY),
            ("scheduled_start_date", DATE),
            ("scheduled_completion_date", DATE),
            ("date_completed", DATE),
            ("extracted_at", TS),
        ]
    ),
    "ref_plants": _schema(
        [
            ("source_system", STRING),
            ("plant_code", STRING),
            ("plant_name", STRING),
            ("company_code", STRING),
            ("country_code", STRING),
            ("region_name", STRING),
            ("extracted_at", TS),
        ]
    ),
    "ref_fx_rates": _schema(
        [
            ("rate_date", DATE),
            ("currency_code", STRING),
            ("usd_rate", RATE),
            ("extracted_at", TS),
        ]
    ),
}

# Partitioned customer masters are the same shape as the current tables.
SCHEMAS["sap_kna1_t1"] = SCHEMAS["sap_kna1"]
SCHEMAS["sap_kna1_t2"] = SCHEMAS["sap_kna1"]
SCHEMAS["oracle_hz_cust_accounts_t1"] = SCHEMAS["oracle_hz_cust_accounts"]
SCHEMAS["oracle_hz_cust_accounts_t2"] = SCHEMAS["oracle_hz_cust_accounts"]


def row(table: str, **values: object) -> dict[str, object]:
    """Return a dict whose keys match ``table`` exactly, in schema order."""

    names = list(SCHEMAS[table].names)
    missing = [name for name in names if name not in values]
    extra = [name for name in values if name not in names]
    if missing or extra:
        raise KeyError(f"{table} missing={missing} extra={extra}")
    return {name: values[name] for name in names}
