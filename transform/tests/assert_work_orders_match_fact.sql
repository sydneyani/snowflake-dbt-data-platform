with source as (
    select
        count(*) as order_count,
        sum(planned_qty) as planned_qty
    from {{ ref('int_work_orders') }}
),

facts as (
    select
        count(*) as order_count,
        sum(planned_qty) as planned_qty
    from {{ ref('fct_work_orders') }}
)

select
    source.order_count as source_orders,
    facts.order_count as fact_orders,
    source.planned_qty as source_qty,
    facts.planned_qty as fact_qty
from source
cross join facts
where
    source.order_count <> facts.order_count
    or abs(source.planned_qty - facts.planned_qty) > 0.001
