select
    a.account_id,
    p.project_id,
    cast(a.signup_date as date) as signup_date,
    a.channel,
    a.region,
    cast(a.is_holdout as boolean) as is_holdout,
    a.signup_method,
    cast(p.provisioned_at as date) as provisioned_at,
    cast(p.has_auth as boolean) as has_auth,
    cast(p.has_storage as boolean) as has_storage,
    cast(p.has_edge_functions as boolean) as has_edge_functions,
    cast(p.has_pgvector as boolean) as has_pgvector,
    cast(p.time_to_first_query_min as double) as time_to_first_query_min,
    cast(p.compute_hours as double) as compute_hours,
    cast(p.db_size_mb as double) as db_size_mb,
    cast(p.egress_gb as double) as egress_gb,
    cast(p.is_pro_upgrade as boolean) as is_pro_upgrade,
    cast(p.pro_upgrade_date as date) as pro_upgrade_date,
    cast(p.monthly_invoice_usd as double) as monthly_invoice_usd
from {{ ref('raw_developer_accounts') }} a
left join {{ ref('raw_project_telemetry') }} p
    on a.account_id = p.account_id
