with distinct_campaigns as (
    select
        campaign_id,
        min(channel) as channel
    from {{ ref('stg_touchpoints') }}
    group by campaign_id
)

select
    campaign_id,
    channel,
    case
        when channel = 'paid_search' then 'Paid Inbound'
        when channel = 'paid_social' then 'Paid Outbound'
        when channel = 'developer_sponsorship' then 'Influencer & Media'
        when channel = 'community_events' then 'Developer Relations'
        else 'Organic & Viral'
    end as channel_category,
    case
        when campaign_id in ('camp_001', 'camp_002') then 'Indie Hacker & Solopreneur'
        when campaign_id in ('camp_003', 'camp_004', 'camp_005') then 'Fast-Growing Startup Lead'
        else 'Enterprise Architect'
    end as target_developer_persona
from distinct_campaigns
