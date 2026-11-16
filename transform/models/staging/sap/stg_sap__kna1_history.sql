with source as (
    select * from {{ source('raw', 'sap_kna1_history') }}
),

renamed as (
    select
        kunnr as source_customer_id,
        name1 as customer_name,
        land1 as country_code,
        regio as region_code,
        ort01 as city,
        pstlz as postal_code,
        stras as street,
        ktokd as account_group,
        stceg as tax_id,
        credit_limit,
        coalesce(loevm, '') = 'X' as is_deleted,
        ktokd = 'TEST' as is_test_account,
        erdat as created_on,
        updated_at,
        effective_date,
        extracted_at,
        'SAP_ECC' as source_system
    from source
)

select * from renamed
