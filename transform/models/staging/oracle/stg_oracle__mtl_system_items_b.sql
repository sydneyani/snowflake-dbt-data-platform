with source as (
    select * from {{ source('raw', 'oracle_mtl_system_items_b') }}
),

renamed as (
    select
        segment1 as source_product_id,
        description as product_name,
        item_type as product_group,
        primary_uom_code as base_uom,
        gtin,
        item_type as material_type,
        organization_id,
        extracted_at,
        'ORACLE_EBS' as source_system
    from source
)

select * from renamed
