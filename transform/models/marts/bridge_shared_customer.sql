-- Grain: one current source customer whose tax id is used by more than one ERP account.
-- The fact keeps the selling ERP's customer. This bridge is how an analyst rolls them together.

with current_customers as (
    select
        tax_id,
        source_system,
        source_customer_id,
        customer_name,
        customer_key
    from {{ ref('dim_customer') }}
    where
        is_current
        and tax_id is not null
),

shared as (
    select tax_id
    from current_customers
    group by tax_id
    having count(*) > 1
)

select
    current_customers.tax_id as global_customer_id,
    current_customers.source_system,
    current_customers.source_customer_id,
    current_customers.customer_name,
    current_customers.customer_key
from current_customers
inner join shared
    on current_customers.tax_id = shared.tax_id
