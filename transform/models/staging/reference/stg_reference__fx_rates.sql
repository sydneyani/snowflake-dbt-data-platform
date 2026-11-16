with source as (
    select * from {{ source('raw', 'ref_fx_rates') }}
),

renamed as (
    select
        rate_date,
        currency_code,
        usd_rate,
        extracted_at
    from source
)

select * from renamed
