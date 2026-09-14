select
    account_id,
    project_id,
    signup_date,
    channel,
    region,
    signup_method,
    is_holdout,
    provisioned_at,
    has_auth,
    has_storage,
    has_edge_functions,
    has_pgvector,
    case
        when has_pgvector then 'AI Vector Platform'
        when has_auth and has_storage and has_edge_functions then 'Full Stack BaaS'
        when has_auth or has_storage then 'Core Features'
        else 'Raw Postgres DB'
    end as feature_adoption_tier,
    time_to_first_query_min,
    case
        when time_to_first_query_min <= 15 then 'Rapid Activation (<15m)'
        when time_to_first_query_min <= 60 then 'Standard Activation (15-60m)'
        else 'Slow / Lagged (>60m)'
    end as activation_speed,
    compute_hours,
    db_size_mb,
    egress_gb,
    case
        when compute_hours > 100 and db_size_mb > 500 then 'High Consumption'
        when compute_hours > 20 or db_size_mb > 50 then 'Moderate Consumption'
        else 'Light Evaluation'
    end as usage_tier,
    is_pro_upgrade,
    pro_upgrade_date,
    case
        when is_pro_upgrade then date_diff('day', signup_date, pro_upgrade_date)
        else null
    end as days_to_upgrade,
    monthly_invoice_usd
from {{ ref('stg_developer_plg_events') }}
