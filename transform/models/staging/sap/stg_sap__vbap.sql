with source as (
    select * from {{ source('raw', 'sap_vbap') }}
),

renamed as (
    select
        vbeln as sales_document,
        posnr as line_number,
        matnr as source_product_id,
        kwmeng as ordered_qty,
        vrkme as unit_of_measure,
        netpr as unit_price,
        netwr as net_amount_doc,
        waerk as currency_code,
        werks as plant_code,
        abgru as rejection_reason,
        erdat as created_on,
        extracted_at,
        'SAP_ECC' as source_system
    from source
)

select * from renamed
