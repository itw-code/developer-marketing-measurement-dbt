with daily_geo_activity as (
    select
        signup_date,
        channel,
        region,
        case
            when region in ('US-East', 'EU-Central') then 'treatment'
            when region in ('US-West', 'APAC-SG') then 'control'
            else 'holdout'
        end as experiment_cohort,
        count(*) as total_signups,
        sum(case when is_holdout then 1 else 0 end) as holdout_signups,
        sum(case when is_pro_upgrade then 1 else 0 end) as pro_upgrades
    from {{ ref('stg_developer_plg_events') }}
    group by 1, 2, 3, 4
)

select * from daily_geo_activity
