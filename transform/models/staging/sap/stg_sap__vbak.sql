with source as (
    select * from {{ source('raw', 'sap_vbak') }}
),

renamed as (
    select
        vbeln as sales_document,
        erdat as created_on,
        audat as order_date,
        vdatu as requested_ship_date,
        auart as order_type_code,
        vkorg as sales_org,
        kunnr as source_customer_id,
        waerk as currency_code,
        netwr as header_net_amount,
        header_freight,
        bukrs as company_code,
        werks as plant_code,
        gbstk as overall_status,
        abstk as rejection_status,
        extracted_at,
        'SAP_ECC' as source_system
    from source
)

select * from renamed
