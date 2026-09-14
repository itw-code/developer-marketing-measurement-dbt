with spend as (
    select
        spend_date as date_day,
        channel,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(platform_conversions) as platform_conversions
    from {{ ref('stg_marketing_ad_spend') }}
    group by 1, 2
),

signups as (
    select
        signup_date as date_day,
        channel,
        count(*) as total_signups,
        sum(case when is_pro_upgrade then 1 else 0 end) as total_pro_upgrades,
        sum(monthly_invoice_usd) as total_revenue_usd
    from {{ ref('stg_developer_plg_events') }}
    group by 1, 2
)

select
    s.date_day,
    s.channel,
    s.spend_usd,
    s.impressions,
    s.clicks,
    s.platform_conversions,
    round(s.spend_usd / nullif(s.clicks, 0), 2) as cpc_usd,
    round(cast(s.clicks as double) / nullif(s.impressions, 0) * 100, 4) as ctr_pct,
    coalesce(u.total_signups, 0) as total_signups,
    coalesce(u.total_pro_upgrades, 0) as total_pro_upgrades,
    coalesce(u.total_revenue_usd, 0.0) as total_revenue_usd,
    round(s.spend_usd / nullif(u.total_pro_upgrades, 0), 2) as blended_cac_usd,
    -- Payback period: CAC / Monthly ARPU ($25 base)
    round((s.spend_usd / nullif(u.total_pro_upgrades, 0)) / 25.0, 1) as payback_period_months
from spend s
left join signups u
    on s.date_day = u.date_day and s.channel = u.channel
