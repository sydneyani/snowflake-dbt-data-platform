with source as (
    select * from {{ source('raw', 'sap_afko') }}
),

renamed as (
    select
        aufnr as work_order_number,
        plnbez as source_product_id,
        werks as plant_code,
        bukrs as company_code,
        auart as order_type_code,
        gamng as planned_qty,
        igmng as completed_qty,
        scrap_qty,
        gstrp as scheduled_start_date,
        gltrp as scheduled_finish_date,
        actual_finish as actual_finish_date,
        status as status_code,
        extracted_at,
        'SAP_ECC' as source_system
    from source
)

select * from renamed
