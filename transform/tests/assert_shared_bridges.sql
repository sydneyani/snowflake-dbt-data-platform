-- 30 tax ids are shared by exactly two ERPs. 40 GTINs are shared by exactly two ERPs.

select
    'customer' as bridge,
    count(distinct global_customer_id) as shared_keys
from {{ ref('bridge_shared_customer') }}
having
    count(distinct global_customer_id) <> 30
    or count(*) <> 60

union all

select
    'product' as bridge,
    count(distinct gtin) as shared_keys
from {{ ref('bridge_shared_product') }}
having
    count(distinct gtin) <> 40
    or count(*) <> 80
