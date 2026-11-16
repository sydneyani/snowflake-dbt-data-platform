-- Grain: one SAP sales line, with header and customer attributes attached.
-- Exclusion rules are applied after the union, in int_sales_lines.

with headers as (
    select * from {{ ref('stg_sap__vbak') }}
),

lines as (
    select * from {{ ref('stg_sap__vbap') }}
),

customers as (
    select * from {{ ref('int_customer_current') }}
    where source_system = 'SAP_ECC'
)

select
    lines.source_system,
    lines.sales_document,
    lines.line_number,
    headers.order_date,
    headers.requested_ship_date,
    case when headers.order_type_code = 'RE' then 'RETURN' else 'SALE' end as order_type,
    headers.source_customer_id,
    lines.source_product_id,
    lines.plant_code,
    lines.currency_code,
    lines.ordered_qty,
    lines.unit_price,
    lines.net_amount_doc,
    headers.order_type_code = 'RE' as is_return,
    customers.is_test_account,
    headers.rejection_status = 'C' as is_cancelled,
    lines.rejection_reason
from lines
inner join headers
    on lines.sales_document = headers.sales_document
inner join customers
    on
        lines.source_system = customers.source_system
        and headers.source_customer_id = customers.source_customer_id
