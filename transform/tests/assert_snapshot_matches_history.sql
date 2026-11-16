-- Current snapshot attributes must match the latest history-extract version.

with history_current as (
    select * from {{ ref('int_customer_versions') }}
    where effective_to is null
),

snapshot_current as (
    select * from {{ ref('dim_customer') }}
    where is_current
)

select history_current.customer_business_key
from history_current
inner join snapshot_current
    on history_current.customer_business_key = snapshot_current.customer_business_key
where
    history_current.customer_name <> snapshot_current.customer_name
    or history_current.city <> snapshot_current.city
    or history_current.credit_limit <> snapshot_current.credit_limit
    or history_current.effective_from <> snapshot_current.effective_from
