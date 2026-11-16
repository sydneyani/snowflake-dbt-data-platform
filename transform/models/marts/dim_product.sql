-- Grain: one item in one source system. Not slowly changing.
-- The same GTIN can appear once per ERP. See bridge_shared_product.

select
    {{ dbt_utils.generate_surrogate_key(['product_business_key']) }} as product_key,
    product_business_key,
    source_system,
    source_product_id,
    product_name,
    product_group,
    base_uom,
    gtin,
    material_type
from {{ ref('int_products') }}
