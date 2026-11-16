with source as (
    select * from {{ source('raw', 'oracle_hz_cust_accounts') }}
),

renamed as (
    select
        cust_account_id as source_customer_id,
        party_name as customer_name,
        country as country_code,
        state as region_code,
        city,
        postal_code,
        address1 as street,
        customer_class_code as account_group,
        tax_reference as tax_id,
        credit_limit,
        status = 'I' as is_deleted,
        customer_class_code = 'TEST' as is_test_account,
        creation_date as created_on,
        last_update_date as updated_at,
        extracted_at,
        'ORACLE_EBS' as source_system
    from source
)

select * from renamed
