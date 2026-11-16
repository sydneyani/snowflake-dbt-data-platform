-- Grain: one calendar day. Fiscal year starts 1 July (July is fiscal month 1).

with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2024-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
)

select
    date_day,
    cast(extract(year from date_day) as int) as calendar_year,
    cast(extract(quarter from date_day) as int) as calendar_quarter,
    cast(extract(month from date_day) as int) as calendar_month,
    dayname(date_day) as day_name,
    cast(extract(dow from date_day) as int) in (0, 6) as is_weekend,
    cast(
        case
            when extract(month from date_day) >= 7 then extract(year from date_day) + 1
            else extract(year from date_day)
        end as int
    ) as fiscal_year,
    case
        when extract(month from date_day) in (7, 8, 9) then 1
        when extract(month from date_day) in (10, 11, 12) then 2
        when extract(month from date_day) in (1, 2, 3) then 3
        else 4
    end as fiscal_quarter
from spine
