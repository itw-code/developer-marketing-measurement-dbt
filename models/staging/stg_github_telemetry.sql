select
    'supabase/supabase' as repo_name,
    cast(stars as integer) as stars_count,
    cast(forks as integer) as forks_count,
    cast(open_issues as integer) as open_issues_count,
    cast(watchers as integer) as watchers_count,
    cast(fetched_at as timestamp) as fetched_at
from {{ ref('raw_github_telemetry') }}
