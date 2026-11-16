-- Grain: one ERP that contributed a sales line or a work order.

with systems as (
    select source_system from {{ ref('int_sales_lines') }}
    union
    select source_system from {{ ref('int_work_orders') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['source_system']) }} as source_system_key,
    source_system as source_system_code,
    case source_system
        when 'SAP_ECC' then 'SAP ECC'
        when 'ORACLE_EBS' then 'Oracle E-Business Suite'
    end as source_system_name
from systems
