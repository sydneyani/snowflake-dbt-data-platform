-- Grain: one accepted sales line (exclusion_reason is null).
-- Customer key is the version effective on the order date.
-- Each order in this dataset is single-plant and single-currency.

with accepted as (
    select * from {{ ref('int_sales_lines') }}
    where exclusion_reason is null
)

select
    {{ dbt_utils.generate_surrogate_key([
        'accepted.source_system',
        'accepted.sales_document',
        'accepted.line_number'
    ]) }} as sales_line_key,
    systems.source_system_key,
    customers.customer_key,
    products.product_key,
    plants.plant_key,
    accepted.order_date,
    accepted.requested_ship_date,
    accepted.source_system,
    accepted.sales_document,
    accepted.line_number,
    accepted.order_type,
    accepted.currency_code,
    accepted.ordered_qty,
    accepted.unit_price,
    accepted.net_amount_doc,
    accepted.fx_rate,
    accepted.net_amount_usd,
    accepted.is_return,
    accepted.source_customer_id,
    accepted.source_product_id,
    accepted.plant_code
from accepted
left join {{ ref('dim_source_system') }} as systems
    on accepted.source_system = systems.source_system_code
left join {{ ref('dim_customer') }} as customers
    on
        accepted.source_system = customers.source_system
        and accepted.source_customer_id = customers.source_customer_id
        and accepted.order_date >= customers.effective_from
        and (
            customers.effective_to is null
            or accepted.order_date < customers.effective_to
        )
left join {{ ref('dim_product') }} as products
    on
        accepted.source_system = products.source_system
        and accepted.source_product_id = products.source_product_id
left join {{ ref('dim_plant') }} as plants
    on
        accepted.source_system = plants.source_system
        and accepted.plant_code = plants.plant_code
left join {{ ref('dim_date') }} as order_dates
    on accepted.order_date = order_dates.date_day
left join {{ ref('dim_date') }} as ship_dates
    on accepted.requested_ship_date = ship_dates.date_day
where
    order_dates.date_day is not null
    and ship_dates.date_day is not null
