select
    account_id,
    touch_id,
    cast(touch_timestamp as timestamp) as touch_timestamp,
    cast(touch_timestamp as date) as touch_date,
    channel,
    campaign_id
from {{ ref('raw_touchpoints') }}
