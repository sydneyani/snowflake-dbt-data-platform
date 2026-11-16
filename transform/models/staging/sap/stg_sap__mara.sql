with source as (
    select * from {{ source('raw', 'sap_mara') }}
),

renamed as (
    select
        matnr as source_product_id,
        maktx as product_name,
        matkl as product_group,
        meins as base_uom,
        ean11 as gtin,
        mtart as material_type,
        extracted_at,
        'SAP_ECC' as source_system
    from source
)

select * from renamed
