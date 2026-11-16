-- Grain: one production order or discrete job.
-- Every work order is kept. There is no exclusion rule on this grain.

with unioned as (
    select
        source_system,
        work_order_number,
        source_product_id,
        plant_code,
        status_code,
        planned_qty,
        completed_qty,
        scrap_qty,
        scheduled_start_date,
        scheduled_finish_date,
        actual_finish_date
    from {{ ref('stg_sap__afko') }}

    union all

    select
        source_system,
        work_order_number,
        source_product_id,
        plant_code,
        status_code,
        planned_qty,
        completed_qty,
        scrap_qty,
        scheduled_start_date,
        scheduled_finish_date,
        actual_finish_date
    from {{ ref('stg_oracle__wip_discrete_jobs') }}
)

select
    source_system,
    work_order_number,
    source_product_id,
    plant_code,
    status_code,
    case
        when status_code in ('CRTD', 'Unreleased') then 'CREATED'
        when status_code in ('PCNF', 'Released') then 'IN_PROCESS'
        when status_code in ('TECO', 'Closed', 'Complete') then 'CLOSED'
    end as status_group,
    planned_qty,
    completed_qty,
    scrap_qty,
    scheduled_start_date,
    scheduled_finish_date,
    actual_finish_date,
    case
        when actual_finish_date is null then null
        when actual_finish_date <= scheduled_finish_date then true
        else false
    end as on_time
from unioned
