{% macro sales_exclusion_reason(
    is_test_account,
    is_cancelled,
    rejection_reason,
    currency_code,
    ordered_qty,
    fx_rate
) %}
    case
        when {{ is_test_account }} then 'TEST_ACCOUNT'
        when {{ is_cancelled }} then 'CANCELLED'
        when {{ rejection_reason }} is not null then 'REJECTED_LINE'
        when {{ currency_code }} not in ('USD', 'EUR', 'GBP') then 'INVALID_CURRENCY'
        when {{ ordered_qty }} is null then 'MISSING_QUANTITY'
        when {{ fx_rate }} is null then 'MISSING_FX'
    end
{% endmacro %}
