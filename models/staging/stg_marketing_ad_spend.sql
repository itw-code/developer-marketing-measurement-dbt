select
    cast(date as date) as spend_date,
    channel,
    region,
    cast(spend as double) as spend_usd,
    cast(impressions as integer) as impressions,
    cast(clicks as integer) as clicks,
    cast(platform_reported_conversions as integer) as platform_conversions,
    round(cast(spend as double) / nullif(cast(clicks as double), 0), 2) as cpc_usd,
    round(cast(clicks as double) / nullif(cast(impressions as double), 0) * 100, 4) as ctr_pct
from {{ ref('raw_marketing_spend') }}
