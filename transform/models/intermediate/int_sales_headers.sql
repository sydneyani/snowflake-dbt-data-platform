-- Grain: one sales document. Header freight is not allocated to lines.

with headers as (
    select
        source_system,
        sales_document,
        order_date,
        source_customer_id,
        currency_code,
        header_net_amount,
        header_freight,
        plant_code
    from {{ ref('stg_sap__vbak') }}

    union all

    select
        source_system,
        sales_document,
        order_date,
        source_customer_id,
        currency_code,
        header_net_amount,
        header_freight,
        plant_code
    from {{ ref('stg_oracle__oe_order_headers_all') }}
)

select * from headers
