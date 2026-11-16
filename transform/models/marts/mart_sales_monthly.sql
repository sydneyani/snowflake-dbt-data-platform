-- Grain: month, source system, plant, and document currency.
-- order_count is safe at plant grain because each order has one plant.
-- Do not sum net_amount_doc across currency_code.

select
    date_trunc('month', order_date) as sales_month,
    source_system,
    plant_code,
    currency_code,
    count(distinct sales_document) as order_count,
    count(*) as line_count,
    sum(net_amount_doc) as net_amount_doc,
    sum(net_amount_usd) as net_amount_usd
from {{ ref('fct_sales_order_lines') }}
group by
    date_trunc('month', order_date),
    source_system,
    plant_code,
    currency_code
