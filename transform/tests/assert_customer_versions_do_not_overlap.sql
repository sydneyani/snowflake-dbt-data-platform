select left_side.customer_business_key
from {{ ref('dim_customer') }} as left_side
inner join {{ ref('dim_customer') }} as right_side
    on
        left_side.customer_business_key = right_side.customer_business_key
        and left_side.customer_key < right_side.customer_key
        and left_side.effective_from < coalesce(right_side.effective_to, date '9999-12-31')
        and right_side.effective_from < coalesce(left_side.effective_to, date '9999-12-31')
