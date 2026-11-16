-- Grain: one excluded sales line. Rows are classified, not deleted.

select
    source_system,
    sales_document,
    line_number,
    order_date,
    source_customer_id,
    source_product_id,
    currency_code,
    ordered_qty,
    net_amount_doc,
    exclusion_reason
from {{ ref('int_sales_lines') }}
where exclusion_reason is not null
