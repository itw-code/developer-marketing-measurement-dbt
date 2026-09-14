select
    row_number() over (order by created_at desc) as story_id,
    title,
    cast(points as integer) as points,
    cast(num_comments as integer) as num_comments,
    cast(created_at as timestamp) as created_at,
    round(cast(points as double) * 1.5 + cast(num_comments as double) * 2.0, 2) as buzz_score
from {{ ref('raw_hackernews_buzz') }}
