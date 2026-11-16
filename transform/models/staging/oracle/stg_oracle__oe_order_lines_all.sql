with source as (
    select * from {{ source('raw', 'oracle_oe_order_lines_all') }}
),

renamed as (
    select
        order_number as sales_document,
        cast(line_number as varchar) as line_number,
        ordered_item as source_product_id,
        ordered_quantity as ordered_qty,
        unit_selling_price as unit_price,
        extended_price as net_amount_doc,
        flow_status_code as line_status,
        request_date as requested_ship_date,
        ship_from_org_id as plant_code,
        extracted_at,
        'ORACLE_EBS' as source_system
    from source
)

select * from renamed
