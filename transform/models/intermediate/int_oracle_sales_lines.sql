-- Grain: one Oracle order line, with header and customer attributes attached.

with headers as (
    select * from {{ ref('stg_oracle__oe_order_headers_all') }}
),

lines as (
    select * from {{ ref('stg_oracle__oe_order_lines_all') }}
),

customers as (
    select * from {{ ref('int_customer_current') }}
    where source_system = 'ORACLE_EBS'
)

select
    headers.source_system,
    lines.sales_document,
    lines.line_number,
    headers.order_date,
    headers.requested_ship_date,
    case when headers.order_type_code = 'RETURN' then 'RETURN' else 'SALE' end as order_type,
    headers.source_customer_id,
    lines.source_product_id,
    lines.plant_code,
    headers.currency_code,
    lines.ordered_qty,
    lines.unit_price,
    lines.net_amount_doc,
    headers.order_type_code = 'RETURN' as is_return,
    customers.is_test_account,
    headers.header_status = 'CANCELLED' or lines.line_status = 'CANCELLED' as is_cancelled,
    cast(null as varchar) as rejection_reason
from lines
inner join headers
    on lines.sales_document = headers.sales_document
inner join customers
    on
        headers.source_system = customers.source_system
        and headers.source_customer_id = customers.source_customer_id
