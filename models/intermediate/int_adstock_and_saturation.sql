with daily_channel_spend as (
    select
        spend_date,
        channel,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(platform_conversions) as platform_conversions
    from {{ ref('stg_marketing_ad_spend') }}
    group by 1, 2
),

lagged as (
    select
        spend_date,
        channel,
        spend_usd,
        impressions,
        clicks,
        platform_conversions,
        coalesce(lag(spend_usd, 1) over (partition by channel order by spend_date), 0) as lag1,
        coalesce(lag(spend_usd, 2) over (partition by channel order by spend_date), 0) as lag2,
        coalesce(lag(spend_usd, 3) over (partition by channel order by spend_date), 0) as lag3,
        coalesce(lag(spend_usd, 4) over (partition by channel order by spend_date), 0) as lag4
    from daily_channel_spend
),

adstocked as (
    select
        spend_date,
        channel,
        spend_usd,
        impressions,
        clicks,
        platform_conversions,
        round(spend_usd + 0.70 * lag1 + 0.49 * lag2 + 0.343 * lag3 + 0.24 * lag4, 2) as spend_adstocked
    from lagged
),

saturated as (
    select
        spend_date,
        channel,
        spend_usd,
        impressions,
        clicks,
        platform_conversions,
        spend_adstocked,
        -- Hill function saturation curve: Response = S^2 / (K^2 + S^2) where K=2500 half-saturation
        round(power(spend_adstocked, 2.0) / (power(2500.0, 2.0) + power(spend_adstocked, 2.0)), 4) as saturation_index,
        -- Calibrated MMM incremental conversions
        round((power(spend_adstocked, 2.0) / (power(2500.0, 2.0) + power(spend_adstocked, 2.0))) * 35.0, 1) as mmm_estimated_conversions
    from adstocked
)

select * from saturated
