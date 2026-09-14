#!/usr/bin/env python3
"""
Exports analytical marts and live API telemetry from DuckDB into
dashboard/data.json and dashboard/data.js for the interactive GitHub Pages showcase.
"""

import json
import os
import duckdb

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "dev_measurement.duckdb")
DASHBOARD_DIR = os.path.join(REPO_ROOT, "dashboard")

os.makedirs(DASHBOARD_DIR, exist_ok=True)


def export_data():
    print(f"Connecting to {DB_PATH}...")
    con = duckdb.connect(DB_PATH, read_only=True)

    # 1. KPI Summary
    kpi_query = """
    select
        round(sum(spend_usd), 2) as total_spend,
        round(sum(platform_reported_conversions), 0) as total_platform_conversions,
        round(sum(mmm_estimated_incremental_conversions), 1) as total_causal_conversions,
        round(((sum(platform_reported_conversions) - sum(mmm_estimated_incremental_conversions)) / nullif(sum(mmm_estimated_incremental_conversions), 0)) * 100, 1) as platform_bias_pct,
        round(sum(spend_usd) / nullif(sum(platform_reported_conversions), 0), 2) as blended_cac,
        round(sum(spend_usd) / nullif(sum(mmm_estimated_incremental_conversions), 0), 2) as incremental_cac,
        round((sum(mmm_estimated_incremental_conversions) * 150.0) / nullif(sum(spend_usd), 0), 2) as marginal_roas,
        round((sum(spend_usd) / nullif(sum(mmm_estimated_incremental_conversions), 0)) / 25.0, 1) as payback_months
    from fct_marketing_triangulation_daily
    """
    kpi_row = con.execute(kpi_query).fetchdf().to_dict(orient="records")[0]

    # 2. Daily Triangulation
    tri_query = """
    select
        cast(date_day as varchar) as date_day,
        channel,
        round(spend_usd, 2) as spend_usd,
        platform_reported_conversions,
        mta_first_touch_conversions,
        mta_last_touch_conversions,
        mmm_estimated_incremental_conversions,
        geo_lift_conversions,
        platform_overreporting_bias_pct,
        incremental_cac_usd,
        incremental_roas
    from fct_marketing_triangulation_daily
    order by date_day desc, spend_usd desc
    """
    tri_records = con.execute(tri_query).fetchdf().to_dict(orient="records")

    # 3. Channel Totals
    channel_query = """
    select
        channel,
        round(sum(spend_usd), 2) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(total_signups) as total_signups,
        sum(total_pro_upgrades) as total_pro_upgrades,
        round(sum(spend_usd) / nullif(sum(total_pro_upgrades), 0), 2) as blended_cac,
        round(avg(cpc_usd), 2) as avg_cpc,
        round(avg(ctr_pct), 3) as avg_ctr
    from fct_channel_efficiency_daily
    group by 1
    order by spend_usd desc
    """
    channel_records = con.execute(channel_query).fetchdf().to_dict(orient="records")

    # 4. Saturation Curve (Hill Function Simulation)
    saturation_curve = []
    for spend_step in [200, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6500, 8000, 10000]:
        sat_index = round((spend_step ** 2.0) / (2500.0 ** 2.0 + spend_step ** 2.0), 4)
        conv = round(sat_index * 35.0, 1)
        saturation_curve.append({
            "spend_usd": spend_step,
            "saturation_index": sat_index,
            "estimated_conversions": conv
        })

    # 5. Cohort Retention
    cohort_query = """
    select
        cast(cohort_week as varchar) as cohort_week,
        channel,
        total_cohort_signups,
        day_7_active_count,
        day_30_active_count,
        pro_upgrade_count,
        total_mrr_usd,
        day_7_activation_rate_pct,
        day_30_retention_rate_pct,
        pro_conversion_rate_pct
    from fct_developer_cohort_retention
    order by cohort_week desc
    """
    cohort_records = con.execute(cohort_query).fetchdf().to_dict(orient="records")

    # 6. Live API Telemetry
    github_data = con.execute("select * from raw_github_telemetry limit 1").fetchdf().to_dict(orient="records")[0]
    hn_stories = con.execute("select title, points, num_comments, created_at from raw_hackernews_buzz order by points desc limit 5").fetchdf().to_dict(orient="records")
    fx_rates = con.execute("select quote_currency, rate from raw_fx_rates").fetchdf().to_dict(orient="records")

    con.close()

    payload = {
        "generated_at": str(github_data.get("fetched_at", "")),
        "kpi_summary": kpi_row,
        "channel_totals": channel_records,
        "saturation_curve": saturation_curve,
        "retention_cohorts": cohort_records,
        "triangulation_daily": tri_records,
        "live_telemetry": {
            "github": github_data,
            "hackernews_top5": hn_stories,
            "fx_rates": fx_rates
        }
    }

    # Write JSON
    json_path = os.path.join(DASHBOARD_DIR, "data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"Wrote {json_path} ({os.path.getsize(json_path)} bytes)")

    # Write JS (for local zero-CORS file:// viewing)
    js_path = os.path.join(DASHBOARD_DIR, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.__DASHBOARD_DATA__ = " + json.dumps(payload, indent=2, default=str) + ";\n")
    print(f"Wrote {js_path} ({os.path.getsize(js_path)} bytes)")

    print("Dashboard export completed successfully.")


if __name__ == "__main__":
    export_data()
