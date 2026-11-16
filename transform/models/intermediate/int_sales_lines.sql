-- Grain: one sales line from either ERP, with an exclusion reason and a USD amount.
-- Lines are not dropped. Marts decide which reasons reach a fact.

with unioned as (
    select * from {{ ref('int_sap_sales_lines') }}
    union all
    select * from {{ ref('int_oracle_sales_lines') }}
),

rated as (
    select
        unioned.source_system,
        unioned.sales_document,
        unioned.line_number,
        unioned.order_date,
        unioned.requested_ship_date,
        unioned.order_type,
        unioned.source_customer_id,
        unioned.source_product_id,
        unioned.plant_code,
        unioned.currency_code,
        unioned.ordered_qty,
        unioned.unit_price,
        unioned.net_amount_doc,
        unioned.is_return,
        unioned.is_test_account,
        unioned.is_cancelled,
        unioned.rejection_reason,
        fx.usd_rate as fx_rate
    from unioned
    left join {{ ref('stg_reference__fx_rates') }} as fx
        on
            unioned.order_date = fx.rate_date
            and unioned.currency_code = fx.currency_code
)

select
    source_system,
    sales_document,
    line_number,
    order_date,
    requested_ship_date,
    order_type,
    source_customer_id,
    source_product_id,
    plant_code,
    currency_code,
    ordered_qty,
    unit_price,
    net_amount_doc,
    is_return,
    is_test_account,
    is_cancelled,
    rejection_reason,
    fx_rate,
    {{ sales_exclusion_reason(
        'is_test_account',
        'is_cancelled',
        'rejection_reason',
        'currency_code',
        'ordered_qty',
        'fx_rate'
    ) }} as exclusion_reason,
    cast(round(net_amount_doc * fx_rate, 2) as decimal(18, 2)) as net_amount_usd
from rated
