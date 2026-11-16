-- Grain: one SCD2 version of a source customer.
-- effective_from is the snapshot updated_at, which this project sets to the
-- business effective timestamp. Facts point-in-time join on these dates.

select
    {{ dbt_utils.generate_surrogate_key(['customer_business_key', 'dbt_valid_from']) }}
        as customer_key,
    customer_business_key,
    source_system,
    source_customer_id,
    customer_name,
    country_code,
    region_code,
    city,
    postal_code,
    street,
    account_group,
    tax_id,
    credit_limit,
    is_deleted,
    is_test_account,
    cast(dbt_valid_from as date) as effective_from,
    cast(dbt_valid_to as date) as effective_to,
    dbt_valid_to is null as is_current
from {{ ref('snap_customer') }}
