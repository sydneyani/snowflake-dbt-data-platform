with accepted as (
    select
        count(*) as line_count,
        sum(net_amount_doc) as amount_doc,
        sum(net_amount_usd) as amount_usd
    from {{ ref('int_sales_lines') }}
    where exclusion_reason is null
),

facts as (
    select
        count(*) as line_count,
        sum(net_amount_doc) as amount_doc,
        sum(net_amount_usd) as amount_usd
    from {{ ref('fct_sales_order_lines') }}
)

select
    accepted.line_count as accepted_lines,
    facts.line_count as fact_lines,
    accepted.amount_doc as accepted_amount_doc,
    facts.amount_doc as fact_amount_doc
from accepted
cross join facts
where
    accepted.line_count <> facts.line_count
    or abs(accepted.amount_doc - facts.amount_doc) > 0.01
    or abs(accepted.amount_usd - facts.amount_usd) > 0.01
