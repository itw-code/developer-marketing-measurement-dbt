with weekly_cohorts as (
    select
        date_trunc('week', signup_date) as cohort_week,
        channel,
        count(*) as total_cohort_signups,
        sum(case when compute_hours > 5 then 1 else 0 end) as day_7_active_count,
        sum(case when compute_hours > 20 then 1 else 0 end) as day_30_active_count,
        sum(case when is_pro_upgrade then 1 else 0 end) as pro_upgrade_count,
        sum(monthly_invoice_usd) as total_mrr_usd
    from {{ ref('stg_developer_plg_events') }}
    group by 1, 2
)

select
    cohort_week,
    channel,
    total_cohort_signups,
    day_7_active_count,
    day_30_active_count,
    pro_upgrade_count,
    total_mrr_usd,
    round(day_7_active_count / nullif(total_cohort_signups, 0) * 100, 2) as day_7_activation_rate_pct,
    round(day_30_active_count / nullif(total_cohort_signups, 0) * 100, 2) as day_30_retention_rate_pct,
    round(pro_upgrade_count / nullif(total_cohort_signups, 0) * 100, 2) as pro_conversion_rate_pct
from weekly_cohorts
