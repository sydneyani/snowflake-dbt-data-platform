with source as (
    select * from {{ source('raw', 'oracle_wip_discrete_jobs') }}
),

renamed as (
    select
        wip_entity_name as work_order_number,
        primary_item_segment as source_product_id,
        organization_id as plant_code,
        class_code,
        status_type as status_code,
        start_quantity as planned_qty,
        quantity_completed as completed_qty,
        quantity_scrapped as scrap_qty,
        scheduled_start_date,
        scheduled_completion_date as scheduled_finish_date,
        date_completed as actual_finish_date,
        extracted_at,
        'ORACLE_EBS' as source_system
    from source
)

select * from renamed
