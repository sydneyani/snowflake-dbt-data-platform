-- Grain: one current row per source system and source customer id.
-- The duplicate SAP extract row is removed here. Staging still shows it.

with unioned as (
    select
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
        created_on,
        updated_at,
        extracted_at
    from {{ ref('stg_sap__kna1') }}

    union all

    select
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
        created_on,
        updated_at,
        extracted_at
    from {{ ref('stg_oracle__hz_cust_accounts') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by source_system, source_customer_id
            order by extracted_at desc, customer_name asc
        ) as row_num
    from unioned
)

select
    source_system || '|' || source_customer_id as customer_business_key,
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
    created_on,
    updated_at,
    extracted_at
from ranked
where row_num = 1
