-- Singular test: total spend must reconcile with zero calculation drift
-- between the staging layer and the downstream mart.

with staging_total as (

    select
        coalesce(sum(spend_usd), 0) as total_spend
    from {{ ref('stg_marketing_ad_spend') }}

),

mart_total as (

    select
        coalesce(sum(spend_usd), 0) as total_spend
    from {{ ref('fct_channel_efficiency_daily') }}

),

drift as (

    select
        abs(staging_total.total_spend - mart_total.total_spend) as spend_drift
    from staging_total
    cross join mart_total

)

select *
from drift
where spend_drift >= 0.01
