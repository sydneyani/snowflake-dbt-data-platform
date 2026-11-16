-- Grain: one business-dated version per source customer, from the history extract.
-- This is independent of snap_customer. A singular test checks that the two agree.

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
        effective_date
    from {{ ref('stg_sap__kna1_history') }}

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
        effective_date
    from {{ ref('stg_oracle__hz_cust_accounts_history') }}
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
    effective_date as effective_from,
    lead(effective_date) over (
        partition by source_system, source_customer_id
        order by effective_date
    ) as effective_to
from unioned
