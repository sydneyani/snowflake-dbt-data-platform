-- Fail when a header does not tie to lines + freight, unless that document
-- is listed in known_header_gaps with the same residual. Also fail when a
-- listed gap is no longer present.

with line_totals as (
    select
        source_system,
        sales_document,
        sum(net_amount_doc) as line_amount
    from {{ ref('int_sales_lines') }}
    group by source_system, sales_document
),

gaps as (
    select
        headers.source_system,
        headers.sales_document,
        headers.header_net_amount
        - line_totals.line_amount
        - headers.header_freight as residual
    from {{ ref('int_sales_headers') }} as headers
    inner join line_totals
        on
            headers.source_system = line_totals.source_system
            and headers.sales_document = line_totals.sales_document
    where abs(
        headers.header_net_amount
        - line_totals.line_amount
        - headers.header_freight
    ) > 0.01
),

unexplained as (
    select
        gaps.source_system,
        gaps.sales_document,
        gaps.residual
    from gaps
    left join {{ ref('known_header_gaps') }} as known
        on
            gaps.source_system = known.source_system
            and gaps.sales_document = known.sales_document
            and abs(gaps.residual - known.expected_residual) <= 0.01
    where known.sales_document is null
),

missing_known as (
    select
        known.source_system,
        known.sales_document,
        cast(null as decimal(18, 2)) as residual
    from {{ ref('known_header_gaps') }} as known
    left join gaps
        on
            known.source_system = gaps.source_system
            and known.sales_document = gaps.sales_document
            and abs(gaps.residual - known.expected_residual) <= 0.01
    where gaps.sales_document is null
)

select * from unexplained
union all
select * from missing_known
