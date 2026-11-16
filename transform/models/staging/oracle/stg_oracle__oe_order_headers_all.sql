with source as (
    select * from {{ source('raw', 'oracle_oe_order_headers_all') }}
),

renamed as (
    select
        order_number as sales_document,
        ordered_date as order_date,
        request_date as requested_ship_date,
        order_type as order_type_code,
        sold_to_customer_id as source_customer_id,
        transactional_curr_code as currency_code,
        header_total as header_net_amount,
        freight_charge as header_freight,
        flow_status_code as header_status,
        ship_from_org_id as plant_code,
        extracted_at,
        'ORACLE_EBS' as source_system
    from source
)

select * from renamed
