"""Independent source-to-target checks against the raw schema and the marts.

The exclusion case matches ``meridian.ingest.exclude`` and the dbt macro
``sales_exclusion_reason``. Document amounts are the primary control total.
USD amounts are recomputed in SQL with the same ``round`` expression the
mart uses, then compared to the fact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

from meridian.constants import (
    HEADER_IMBALANCE,
    ORACLE_FREIGHT_DOC,
    ORACLE_IMBALANCE_DOC,
    SAP_PIT_AFTER_DOC,
    SAP_PIT_BEFORE_DOC,
    SCD_NEW_CITY,
)

MONEY = Decimal("0.01")
QTY = Decimal("0.001")


@dataclass
class Check:
    name: str
    status: str
    detail: str
    source_value: str | None = None
    target_value: str | None = None
    variance: str | None = None


@dataclass
class ReconciliationReport:
    generated_at: str
    seed: int
    status: str
    summary: str
    checks: list[Check] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# Source-to-target reconciliation",
            "",
            f"- Generated: {self.generated_at}",
            f"- Seed: {self.seed}",
            f"- Pipeline status: {self.status}",
            "",
            self.summary,
            "",
            "| Check | Status | Source | Target | Variance | Detail |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for check in self.checks:
            lines.append(
                "| {name} | {status} | {source} | {target} | {variance} | {detail} |".format(
                    name=check.name,
                    status=check.status,
                    source=check.source_value or "",
                    target=check.target_value or "",
                    variance=check.variance or "",
                    detail=check.detail.replace("|", "/"),
                )
            )
        lines.append("")
        return "\n".join(lines)


def reconcile(db_path: Path, manifest_path: Path | None = None) -> ReconciliationReport:
    manifest = _read_manifest(manifest_path)
    seed = int(manifest.get("seed", 42)) if manifest else 42
    checks: list[Check] = []
    with duckdb.connect(str(db_path), read_only=True) as connection:
        relations = _relations(connection)
        checks.append(_sales_parity(connection, relations, manifest))
        checks.append(_usd_parity(connection, relations))
        checks.append(_work_order_parity(connection, relations, manifest))
        checks.append(_header_gap(connection, relations))
        checks.append(_duplicate_customer(connection, relations))
        checks.append(_snapshot_history(connection, relations))
        checks.append(_test_accounts(connection, relations))
        checks.append(_shared_customers(connection, relations))
        checks.append(_pit_sales(connection, relations))
        checks.append(_freight_is_explained(connection, relations))
    failed = [check.name for check in checks if check.status == "FAIL"]
    explained = [check.name for check in checks if check.status == "EXPLAINED"]
    if failed:
        status = "FAIL"
        summary = "Unexplained variance in: " + ", ".join(failed) + "."
    else:
        status = "PASS"
        summary = "Pipeline control totals tie to the raw extract."
        if explained:
            summary += " Explained source findings: " + ", ".join(explained) + "."
    return ReconciliationReport(
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        seed=seed,
        status=status,
        summary=summary,
        checks=checks,
    )


def _read_manifest(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _relations(connection: duckdb.DuckDBPyConnection) -> dict[str, str]:
    rows = connection.execute(
        """
        select lower(table_name) as table_name, table_schema
        from information_schema.tables
        where table_schema not in ('information_schema', 'pg_catalog')
        """
    ).fetchall()
    found: dict[str, str] = {}
    for name, schema in rows:
        found.setdefault(name, f"{schema}.{name}")
    return found


def _require(relations: dict[str, str], name: str) -> str:
    try:
        return relations[name]
    except KeyError as exc:
        raise RuntimeError(f"warehouse is missing {name}") from exc


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(MONEY)


def _qty(value: object) -> Decimal:
    return Decimal(str(value)).quantize(QTY)


def _pass_fail(name: str, source: Decimal, target: Decimal, tolerance: Decimal, unit: str) -> Check:
    variance = (target - source).quantize(tolerance)
    status = "PASS" if abs(variance) <= tolerance else "FAIL"
    return Check(
        name=name,
        status=status,
        detail=f"Target minus source, tolerance {tolerance} {unit}.",
        source_value=format(source, "f"),
        target_value=format(target, "f"),
        variance=format(variance, "f"),
    )


_ACCEPTED_SQL = """
with sap_customers as (
    select * from (
        select
            kunnr,
            ktokd,
            row_number() over (partition by kunnr order by extracted_at desc, name1) as row_num
        from raw.sap_kna1
    )
    where row_num = 1
),
oracle_customers as (
    select * from (
        select
            cust_account_id,
            customer_class_code,
            row_number() over (
                partition by cust_account_id
                order by extracted_at desc, party_name
            ) as row_num
        from raw.oracle_hz_cust_accounts
    )
    where row_num = 1
),
lines as (
    select
        'SAP_ECC' as source_system,
        headers.vbeln as sales_document,
        lines.netwr as net_amount_doc,
        lines.waerk as currency_code,
        headers.audat as order_date,
        case
            when customers.ktokd = 'TEST' then 'TEST_ACCOUNT'
            when headers.abstk = 'C' then 'CANCELLED'
            when lines.abgru is not null then 'REJECTED_LINE'
            when lines.waerk not in ('USD', 'EUR', 'GBP') then 'INVALID_CURRENCY'
            when lines.kwmeng is null then 'MISSING_QUANTITY'
            when fx.usd_rate is null then 'MISSING_FX'
        end as exclusion_reason,
        fx.usd_rate
    from raw.sap_vbap as lines
    inner join raw.sap_vbak as headers
        on lines.vbeln = headers.vbeln
    inner join sap_customers as customers
        on headers.kunnr = customers.kunnr
    left join raw.ref_fx_rates as fx
        on headers.audat = fx.rate_date
        and lines.waerk = fx.currency_code

    union all

    select
        'ORACLE_EBS' as source_system,
        headers.order_number as sales_document,
        lines.extended_price as net_amount_doc,
        headers.transactional_curr_code as currency_code,
        headers.ordered_date as order_date,
        case
            when customers.customer_class_code = 'TEST' then 'TEST_ACCOUNT'
            when headers.flow_status_code = 'CANCELLED'
                or lines.flow_status_code = 'CANCELLED' then 'CANCELLED'
            when headers.transactional_curr_code not in ('USD', 'EUR', 'GBP')
                then 'INVALID_CURRENCY'
            when lines.ordered_quantity is null then 'MISSING_QUANTITY'
            when fx.usd_rate is null then 'MISSING_FX'
        end as exclusion_reason,
        fx.usd_rate
    from raw.oracle_oe_order_lines_all as lines
    inner join raw.oracle_oe_order_headers_all as headers
        on lines.order_number = headers.order_number
    inner join oracle_customers as customers
        on headers.sold_to_customer_id = customers.cust_account_id
    left join raw.ref_fx_rates as fx
        on headers.ordered_date = fx.rate_date
        and headers.transactional_curr_code = fx.currency_code
)
select
    count(*) filter (where exclusion_reason is null) as accepted_lines,
    coalesce(sum(net_amount_doc) filter (where exclusion_reason is null), 0) as accepted_amount,
    coalesce(
        sum(cast(round(net_amount_doc * usd_rate, 2) as decimal(18, 2)))
            filter (where exclusion_reason is null),
        0
    ) as accepted_usd
from lines
"""


def _sales_parity(
    connection: duckdb.DuckDBPyConnection,
    relations: dict[str, str],
    manifest: dict,
) -> Check:
    fact = _require(relations, "fct_sales_order_lines")
    raw_lines, raw_amount, _raw_usd = connection.execute(_ACCEPTED_SQL).fetchone()
    fact_lines, fact_amount = connection.execute(
        f"""
        select count(*), coalesce(sum(net_amount_doc), 0)
        from {fact}
        """
    ).fetchone()
    manifest_sales = manifest.get("sales", {})
    pieces = [
        ("raw lines", Decimal(raw_lines)),
        ("fact lines", Decimal(fact_lines)),
    ]
    amounts = [
        ("raw amount", _money(raw_amount)),
        ("fact amount", _money(fact_amount)),
    ]
    if manifest_sales:
        pieces.append(("manifest lines", Decimal(manifest_sales["accepted_line_count"])))
        amounts.append(("manifest amount", _money(manifest_sales["accepted_amount_doc"])))
    line_ok = len({value for _, value in pieces}) == 1
    amount_ok = len({value for _, value in amounts}) == 1
    return Check(
        name="sales_accepted_doc_total",
        status="PASS" if line_ok and amount_ok else "FAIL",
        detail="Accepted line count and document amount across manifest, raw SQL, and the fact.",
        source_value=", ".join(f"{label}={value}" for label, value in pieces),
        target_value=", ".join(f"{label}={format(value, 'f')}" for label, value in amounts),
        variance="0.00" if line_ok and amount_ok else "mismatch",
    )


def _usd_parity(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    fact = _require(relations, "fct_sales_order_lines")
    _lines, _amount, raw_usd = connection.execute(_ACCEPTED_SQL).fetchone()
    fact_usd = connection.execute(
        f"select coalesce(sum(net_amount_usd), 0) from {fact}"
    ).fetchone()[0]
    return _pass_fail("sales_accepted_usd_total", _money(raw_usd), _money(fact_usd), MONEY, "USD")


def _work_order_parity(
    connection: duckdb.DuckDBPyConnection,
    relations: dict[str, str],
    manifest: dict,
) -> Check:
    fact = _require(relations, "fct_work_orders")
    raw_count, raw_qty = connection.execute(
        """
        select
            (select count(*) from raw.sap_afko)
                + (select count(*) from raw.oracle_wip_discrete_jobs),
            coalesce((select sum(gamng) from raw.sap_afko), 0)
                + coalesce((select sum(start_quantity) from raw.oracle_wip_discrete_jobs), 0)
        """
    ).fetchone()
    fact_count, fact_qty = connection.execute(
        f"select count(*), coalesce(sum(planned_qty), 0) from {fact}"
    ).fetchone()
    count_ok = int(raw_count) == int(fact_count)
    qty_ok = abs(_qty(raw_qty) - _qty(fact_qty)) <= QTY
    manifest_qty = manifest.get("work_orders", {}).get("planned_qty")
    manifest_ok = True
    if manifest_qty is not None:
        manifest_ok = abs(_qty(manifest_qty) - _qty(raw_qty)) <= QTY
        count_ok = count_ok and int(manifest["work_orders"]["count"]) == int(raw_count)
    return Check(
        name="work_order_planned_qty",
        status="PASS" if count_ok and qty_ok and manifest_ok else "FAIL",
        detail="Work order count and planned quantity, raw versus fact.",
        source_value=f"count={raw_count}; qty={_qty(raw_qty)}",
        target_value=f"count={fact_count}; qty={_qty(fact_qty)}",
        variance=format(_qty(fact_qty) - _qty(raw_qty), "f"),
    )


def _header_gap(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    del relations
    rows = connection.execute(
        """
        with sap_lines as (
            select vbeln, sum(netwr) as line_amount
            from raw.sap_vbap
            group by vbeln
        ),
        oracle_lines as (
            select order_number, sum(extended_price) as line_amount
            from raw.oracle_oe_order_lines_all
            group by order_number
        ),
        gaps as (
            select
                'SAP_ECC' as source_system,
                headers.vbeln as sales_document,
                headers.netwr - sap_lines.line_amount - headers.header_freight as residual
            from raw.sap_vbak as headers
            inner join sap_lines on headers.vbeln = sap_lines.vbeln
            where abs(headers.netwr - sap_lines.line_amount - headers.header_freight) > 0.01
            union all
            select
                'ORACLE_EBS' as source_system,
                headers.order_number as sales_document,
                headers.header_total - oracle_lines.line_amount - headers.freight_charge as residual
            from raw.oracle_oe_order_headers_all as headers
            inner join oracle_lines on headers.order_number = oracle_lines.order_number
            where abs(
                headers.header_total - oracle_lines.line_amount - headers.freight_charge
            ) > 0.01
        )
        select source_system, sales_document, residual
        from gaps
        order by source_system, sales_document
        """
    ).fetchall()
    expected = ("ORACLE_EBS", ORACLE_IMBALANCE_DOC, _money(HEADER_IMBALANCE))
    observed = [(row[0], row[1], _money(row[2])) for row in rows]
    if observed == [expected]:
        return Check(
            name="header_tie_out",
            status="EXPLAINED",
            detail=(
                "One source document does not tie. The line fact keeps the line amounts. "
                "This is not a pipeline variance."
            ),
            source_value=f"{expected[1]} residual {expected[2]}",
            target_value="lines + freight",
            variance=format(expected[2], "f"),
        )
    return Check(
        name="header_tie_out",
        status="FAIL",
        detail="Header residuals do not match the planted source defect.",
        source_value=str(observed),
        target_value=str([expected]),
        variance="mismatch",
    )


def _duplicate_customer(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    dim = _require(relations, "dim_customer")
    raw_rows, distinct_ids = connection.execute(
        "select count(*), count(distinct kunnr) from raw.sap_kna1"
    ).fetchone()
    current = connection.execute(
        f"""
        select count(*) from {dim}
        where source_system = 'SAP_ECC' and is_current
        """
    ).fetchone()[0]
    extra = int(raw_rows) - int(distinct_ids)
    ok = extra == 1 and int(current) == int(distinct_ids)
    return Check(
        name="sap_customer_duplicate",
        status="PASS" if ok else "FAIL",
        detail="One duplicate KUNNR is in the extract and one current dimension row remains.",
        source_value=f"raw_rows={raw_rows}; distinct={distinct_ids}",
        target_value=f"current_dim={current}",
        variance=str(extra),
    )


def _snapshot_history(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    snap = _require(relations, "snap_customer")
    closed = connection.execute(
        f"select count(*) from {snap} where dbt_valid_to is not null"
    ).fetchone()[0]
    ok = int(closed) == 30
    return Check(
        name="customer_snapshot_closed_versions",
        status="PASS" if ok else "FAIL",
        detail="Changed customers (20 SAP, 10 Oracle) have one closed snapshot version.",
        source_value="30",
        target_value=str(closed),
        variance=str(int(closed) - 30),
    )


def _test_accounts(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    fact = _require(relations, "fct_sales_order_lines")
    dim = _require(relations, "dim_customer")
    found = connection.execute(
        f"""
        select count(*)
        from {fact} as facts
        inner join {dim} as customers
            on facts.customer_key = customers.customer_key
        where customers.is_test_account
        """
    ).fetchone()[0]
    return Check(
        name="test_accounts_absent_from_fact",
        status="PASS" if int(found) == 0 else "FAIL",
        detail="Test account lines stay in the exception mart.",
        source_value="0",
        target_value=str(found),
        variance=str(found),
    )


def _shared_customers(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    bridge = _require(relations, "bridge_shared_customer")
    tax_ids, rows = connection.execute(
        f"select count(distinct global_customer_id), count(*) from {bridge}"
    ).fetchone()
    ok = int(tax_ids) == 30 and int(rows) == 60
    return Check(
        name="shared_customer_tax_ids",
        status="PASS" if ok else "FAIL",
        detail="Thirty tax ids are shared by exactly two current ERP accounts.",
        source_value="tax_ids=30; rows=60",
        target_value=f"tax_ids={tax_ids}; rows={rows}",
        variance="0" if ok else "mismatch",
    )


def _pit_sales(connection: duckdb.DuckDBPyConnection, relations: dict[str, str]) -> Check:
    fact = _require(relations, "fct_sales_order_lines")
    dim = _require(relations, "dim_customer")
    before, after = connection.execute(
        f"""
        select
            max(case when facts.sales_document = ? then customers.city end),
            max(case when facts.sales_document = ? then customers.city end)
        from {fact} as facts
        inner join {dim} as customers
            on facts.customer_key = customers.customer_key
        where facts.sales_document in (?, ?)
        """,
        [SAP_PIT_BEFORE_DOC, SAP_PIT_AFTER_DOC, SAP_PIT_BEFORE_DOC, SAP_PIT_AFTER_DOC],
    ).fetchone()
    ok = before is not None and after == SCD_NEW_CITY and before != SCD_NEW_CITY
    return Check(
        name="customer_point_in_time",
        status="PASS" if ok else "FAIL",
        detail=(
            f"SAP document {SAP_PIT_BEFORE_DOC} uses the pre-change city and "
            f"{SAP_PIT_AFTER_DOC} uses {SCD_NEW_CITY}."
        ),
        source_value=str(before),
        target_value=str(after),
        variance="0" if ok else "mismatch",
    )


def _freight_is_explained(
    connection: duckdb.DuckDBPyConnection,
    relations: dict[str, str],
) -> Check:
    del relations
    residual = connection.execute(
        """
        with lines as (
            select order_number, sum(extended_price) as line_amount
            from raw.oracle_oe_order_lines_all
            group by order_number
        )
        select headers.header_total - lines.line_amount - headers.freight_charge
        from raw.oracle_oe_order_headers_all as headers
        inner join lines on headers.order_number = lines.order_number
        where headers.order_number = ?
        """,
        [ORACLE_FREIGHT_DOC],
    ).fetchone()
    if residual is None:
        return Check(
            name="header_freight_ties",
            status="FAIL",
            detail=f"Freight document {ORACLE_FREIGHT_DOC} was not found.",
        )
    value = _money(residual[0])
    freight = connection.execute(
        "select freight_charge from raw.oracle_oe_order_headers_all where order_number = ?",
        [ORACLE_FREIGHT_DOC],
    ).fetchone()[0]
    ok = value == Decimal("0.00") and _money(freight) == Decimal("50.00")
    return Check(
        name="header_freight_ties",
        status="PASS" if ok else "FAIL",
        detail=(
            f"Document {ORACLE_FREIGHT_DOC} carries header freight that is not on the lines. "
            "Header minus lines minus freight is zero, so the line fact is not expected to "
            "include that freight."
        ),
        source_value=f"freight={_money(freight)}",
        target_value=f"residual={value}",
        variance=format(value, "f"),
    )
