-- Grain: one plant or inventory organization in one source system.

select
    {{ dbt_utils.generate_surrogate_key(['source_system', 'plant_code']) }} as plant_key,
    source_system,
    plant_code,
    plant_name,
    company_code,
    country_code,
    region_name
from {{ ref('stg_reference__plants') }}
