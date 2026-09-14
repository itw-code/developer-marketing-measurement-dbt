with converted_accounts as (
    select
        account_id,
        pro_upgrade_date,
        monthly_invoice_usd
    from {{ ref('stg_developer_plg_events') }}
    where is_pro_upgrade = true
),

touchpoints as (
    select
        t.account_id,
        t.touch_id,
        t.touch_timestamp,
        t.touch_date,
        t.channel,
        t.campaign_id,
        c.pro_upgrade_date,
        c.monthly_invoice_usd,
        row_number() over (partition by t.account_id order by t.touch_timestamp asc) as touch_order_asc,
        row_number() over (partition by t.account_id order by t.touch_timestamp desc) as touch_order_desc,
        count(*) over (partition by t.account_id) as total_touches
    from {{ ref('stg_touchpoints') }} t
    inner join converted_accounts c
        on t.account_id = c.account_id
    where t.touch_date <= c.pro_upgrade_date
),

weighted as (
    select
        account_id,
        touch_id,
        touch_timestamp,
        touch_date,
        channel,
        campaign_id,
        pro_upgrade_date,
        monthly_invoice_usd,
        touch_order_asc,
        touch_order_desc,
        total_touches,
        case when touch_order_asc = 1 then 1.0 else 0.0 end as first_touch_weight,
        case when touch_order_desc = 1 then 1.0 else 0.0 end as last_touch_weight,
        round(1.0 / cast(total_touches as double), 4) as linear_weight,
        round(exp(-0.05 * greatest(0, date_diff('day', touch_date, pro_upgrade_date))), 4) as time_decay_raw
    from touchpoints
),

normalized as (
    select
        w.*,
        sum(time_decay_raw) over (partition by account_id) as sum_decay_raw
    from weighted w
)

select
    account_id,
    touch_id,
    touch_timestamp,
    touch_date,
    channel,
    campaign_id,
    pro_upgrade_date,
    monthly_invoice_usd,
    touch_order_asc,
    touch_order_desc,
    total_touches,
    first_touch_weight,
    last_touch_weight,
    linear_weight,
    round(time_decay_raw / nullif(sum_decay_raw, 0), 4) as time_decay_weight
from normalized
