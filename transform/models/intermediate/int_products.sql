-- Grain: one item per source system. GTIN is the cross-ERP match key.
-- Quantities are already in the item base unit. This dataset uses EA only.

with products as (
    select
        source_system,
        source_product_id,
        product_name,
        product_group,
        base_uom,
        gtin,
        material_type
    from {{ ref('stg_sap__mara') }}

    union all

    select
        source_system,
        source_product_id,
        product_name,
        product_group,
        base_uom,
        gtin,
        material_type
    from {{ ref('stg_oracle__mtl_system_items_b') }}
)

select
    source_system || '|' || source_product_id as product_business_key,
    source_system,
    source_product_id,
    product_name,
    product_group,
    base_uom,
    gtin,
    material_type
from products
