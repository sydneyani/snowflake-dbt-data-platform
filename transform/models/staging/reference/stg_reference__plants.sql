with source as (
    select * from {{ source('raw', 'ref_plants') }}
),

renamed as (
    select
        source_system,
        plant_code,
        plant_name,
        company_code,
        country_code,
        region_name,
        extracted_at
    from source
)

select * from renamed
