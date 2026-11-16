select facts.sales_line_key
from {{ ref('fct_sales_order_lines') }} as facts
inner join {{ ref('dim_customer') }} as customers
    on facts.customer_key = customers.customer_key
where customers.is_test_account
