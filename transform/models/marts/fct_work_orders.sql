-- Grain: one work order. All statuses are included.

select
    {{ dbt_utils.generate_surrogate_key([
        'orders.source_system',
        'orders.work_order_number'
    ]) }} as work_order_key,
    systems.source_system_key,
    products.product_key,
    plants.plant_key,
    orders.source_system,
    orders.work_order_number,
    orders.status_code,
    orders.status_group,
    orders.planned_qty,
    orders.completed_qty,
    orders.scrap_qty,
    orders.scheduled_start_date,
    orders.scheduled_finish_date,
    orders.actual_finish_date,
    orders.on_time,
    case
        when orders.actual_finish_date is null then null
        else datediff('day', orders.scheduled_start_date, orders.actual_finish_date)
    end as cycle_time_days,
    orders.source_product_id,
    orders.plant_code
from {{ ref('int_work_orders') }} as orders
left join {{ ref('dim_source_system') }} as systems
    on orders.source_system = systems.source_system_code
left join {{ ref('dim_product') }} as products
    on
        orders.source_system = products.source_system
        and orders.source_product_id = products.source_product_id
left join {{ ref('dim_plant') }} as plants
    on
        orders.source_system = plants.source_system
        and orders.plant_code = plants.plant_code
