-- Grain: one source item whose GTIN is used by more than one ERP.

with shared as (
    select gtin
    from {{ ref('dim_product') }}
    where gtin is not null
    group by gtin
    having count(*) > 1
)

select
    products.gtin,
    products.source_system,
    products.source_product_id,
    products.product_name,
    products.product_key
from {{ ref('dim_product') }} as products
inner join shared
    on products.gtin = shared.gtin
