with mmm as (
    select
        spend_date as date_day,
        channel,
        spend_usd,
        impressions,
        clicks,
        platform_conversions,
        spend_adstocked,
        saturation_index,
        mmm_estimated_conversions
    from {{ ref('int_adstock_and_saturation') }}
),

mta as (
    select
        touch_date as date_day,
        channel,
        round(sum(first_touch_weight), 2) as mta_first_touch_conversions,
        round(sum(last_touch_weight), 2) as mta_last_touch_conversions,
        round(sum(linear_weight), 2) as mta_linear_conversions,
        round(sum(time_decay_weight), 2) as mta_time_decay_conversions
    from {{ ref('int_attribution_paths') }}
    group by 1, 2
),

geo as (
    select
        signup_date as date_day,
        channel,
        sum(case when experiment_cohort = 'treatment' then pro_upgrades else 0 end) as treatment_conversions,
        sum(case when experiment_cohort = 'control' then pro_upgrades else 0 end) as control_conversions,
        greatest(0, sum(case when experiment_cohort = 'treatment' then pro_upgrades else 0 end) - sum(case when experiment_cohort = 'control' then pro_upgrades else 0 end)) as geo_lift_conversions
    from {{ ref('int_geo_experiment_clusters') }}
    group by 1, 2
),

triangulated as (
    select
        m.date_day,
        m.channel,
        m.spend_usd,
        m.impressions,
        m.clicks,
        m.platform_conversions as platform_reported_conversions,
        coalesce(t.mta_first_touch_conversions, 0.0) as mta_first_touch_conversions,
        coalesce(t.mta_last_touch_conversions, 0.0) as mta_last_touch_conversions,
        coalesce(t.mta_linear_conversions, 0.0) as mta_linear_conversions,
        coalesce(t.mta_time_decay_conversions, 0.0) as mta_time_decay_conversions,
        m.mmm_estimated_conversions as mmm_estimated_incremental_conversions,
        coalesce(g.geo_lift_conversions, 0) as geo_lift_conversions,
        -- Platform over-reporting bias against causal MMM: ((Platform - MMM) / MMM) * 100
        round(((m.platform_conversions - nullif(m.mmm_estimated_conversions, 0)) / nullif(m.mmm_estimated_conversions, 0)) * 100, 2) as platform_overreporting_bias_pct,
        -- Unit Economics
        round(m.spend_usd / nullif(m.platform_conversions, 0), 2) as blended_cac_usd,
        round(m.spend_usd / nullif(m.mmm_estimated_conversions, 0), 2) as incremental_cac_usd,
        round((m.mmm_estimated_conversions * 150.0) / nullif(m.spend_usd, 0), 2) as incremental_roas
    from mmm m
    left join mta t
        on m.date_day = t.date_day and m.channel = t.channel
    left join geo g
        on m.date_day = g.date_day and m.channel = g.channel
)

select * from triangulated
