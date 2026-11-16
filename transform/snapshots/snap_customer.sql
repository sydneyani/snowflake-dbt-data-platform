{% snapshot snap_customer %}

{{
    config(
        unique_key='customer_business_key',
        strategy='check',
        check_cols=['customer_name', 'city', 'region_code', 'postal_code', 'credit_limit', 'is_deleted'],
        updated_at='updated_at',
        hard_deletes='ignore',
    )
}}

    select * from {{ ref('int_customer_current') }}  -- noqa: AM04

{% endsnapshot %}
