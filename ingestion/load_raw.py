#!/usr/bin/env python3
"""
Ingestion script for developer-marketing-measurement-dbt.

Fetches live data from GitHub, Hacker News, and Frankfurter APIs,
generates synthetic marketing and product telemetry data,
and writes all raw CSV files to the seeds/ directory.
"""

import csv
import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
SEED_DIR = "seeds"
RANDOM_SEED = 42
DAYS_OF_DATA = 90
NUM_ACCOUNTS = 1200
CHANNELS = [
    "paid_search",
    "paid_social",
    "developer_sponsorship",
    "community_events",
    "organic_direct",
]
REGIONS = ["US-East", "US-West", "EU-Central", "APAC-SG", "LATAM"]
SIGNUP_METHODS = ["github_oauth", "email"]

# API endpoints
GITHUB_API_URL = "https://api.github.com/repos/supabase/supabase"
HN_API_URL = "https://hn.algolia.com/api/v1/search?query=supabase&tags=story&hitsPerPage=20"
FX_API_URL = "https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,IDR,CAD"

# Fallback data (used if API calls fail)
FALLBACK_GITHUB = {
    "stargazers_count": 72000,
    "forks_count": 4500,
    "open_issues_count": 120,
    "subscribers_count": 1800,
}

FALLBACK_HN_STORIES = [
    {
        "title": "Show HN: Supabase – The Open Source Firebase Alternative",
        "points": 1200,
        "num_comments": 350,
        "created_at": "2023-05-15T10:00:00Z",
    },
    {
        "title": "Supabase raises $80M Series C",
        "points": 800,
        "num_comments": 200,
        "created_at": "2023-08-01T14:30:00Z",
    },
    {
        "title": "Supabase launches pgvector support",
        "points": 650,
        "num_comments": 150,
        "created_at": "2023-11-20T09:15:00Z",
    },
    {
        "title": "Supabase vs Firebase: A developer's perspective",
        "points": 500,
        "num_comments": 120,
        "created_at": "2024-01-10T16:45:00Z",
    },
    {
        "title": "Supabase Edge Functions now in beta",
        "points": 420,
        "num_comments": 90,
        "created_at": "2024-03-05T11:00:00Z",
    },
    {
        "title": "Supabase Storage: S3-compatible object storage",
        "points": 380,
        "num_comments": 70,
        "created_at": "2024-04-12T08:30:00Z",
    },
    {
        "title": "Supabase Auth: Built-in user management",
        "points": 340,
        "num_comments": 60,
        "created_at": "2024-05-22T13:20:00Z",
    },
    {
        "title": "Supabase Realtime: Multiplayer for your database",
        "points": 300,
        "num_comments": 55,
        "created_at": "2024-06-18T17:10:00Z",
    },
    {
        "title": "Supabase CLI 2.0 released",
        "points": 280,
        "num_comments": 45,
        "created_at": "2024-07-01T09:00:00Z",
    },
    {
        "title": "Supabase launches SOC2 compliance",
        "points": 260,
        "num_comments": 40,
        "created_at": "2024-08-14T12:00:00Z",
    },
    {
        "title": "Supabase introduces Branching",
        "points": 240,
        "num_comments": 35,
        "created_at": "2024-09-02T15:30:00Z",
    },
    {
        "title": "Supabase partners with Vercel",
        "points": 220,
        "num_comments": 30,
        "created_at": "2024-10-10T10:00:00Z",
    },
    {
        "title": "Supabase adds Postgres extensions marketplace",
        "points": 200,
        "num_comments": 25,
        "created_at": "2024-11-05T14:00:00Z",
    },
    {
        "title": "Supabase reaches 1M developers",
        "points": 180,
        "num_comments": 20,
        "created_at": "2024-12-01T18:00:00Z",
    },
    {
        "title": "Supabase launches AI toolkit",
        "points": 160,
        "num_comments": 15,
        "created_at": "2025-01-15T11:30:00Z",
    },
    {
        "title": "Supabase raises $120M Series D",
        "points": 140,
        "num_comments": 10,
        "created_at": "2025-02-20T09:45:00Z",
    },
    {
        "title": "Supabase introduces read replicas",
        "points": 120,
        "num_comments": 8,
        "created_at": "2025-03-10T16:20:00Z",
    },
    {
        "title": "Supabase launches Postgres Functions",
        "points": 100,
        "num_comments": 5,
        "created_at": "2025-04-01T12:00:00Z",
    },
    {
        "title": "Supabase adds vector search improvements",
        "points": 80,
        "num_comments": 3,
        "created_at": "2025-04-15T10:00:00Z",
    },
    {
        "title": "Supabase community meetup recap",
        "points": 60,
        "num_comments": 2,
        "created_at": "2025-04-20T14:00:00Z",
    },
]

FALLBACK_FX = {
    "EUR": 0.92,
    "GBP": 0.79,
    "IDR": 16000.0,
    "CAD": 1.36,
}


# ------------------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------------------
def ensure_seed_dir():
    """Create seeds directory if it doesn't exist."""
    os.makedirs(SEED_DIR, exist_ok=True)


def log_warning(message):
    """Print warning to stderr."""
    print(f"WARNING: {message}", file=sys.stderr)


def fetch_json(url, timeout=10):
    """
    Fetch JSON from a URL using urllib.
    Raises exception on failure.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ------------------------------------------------------------------------------
# API data fetching
# ------------------------------------------------------------------------------
def fetch_github_data():
    """
    Fetch GitHub repo stats for supabase/supabase.
    Returns dict with stars, forks, open_issues, watchers.
    Falls back to realistic data on error.
    """
    try:
        data = fetch_json(GITHUB_API_URL)
        return {
            "stars": data.get("stargazers_count", FALLBACK_GITHUB["stargazers_count"]),
            "forks": data.get("forks_count", FALLBACK_GITHUB["forks_count"]),
            "open_issues": data.get("open_issues_count", FALLBACK_GITHUB["open_issues_count"]),
            "watchers": data.get("subscribers_count", FALLBACK_GITHUB["subscribers_count"]),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log_warning(f"GitHub API failed ({e}). Using fallback data.")
        return FALLBACK_GITHUB


def fetch_hackernews_data():
    """
    Fetch top 20 Hacker News stories about Supabase.
    Returns list of dicts with title, points, num_comments, created_at.
    Falls back to realistic data on error.
    """
    try:
        data = fetch_json(HN_API_URL)
        hits = data.get("hits", [])
        stories = []
        for hit in hits[:20]:
            stories.append({
                "title": hit.get("title", ""),
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "created_at": hit.get("created_at", ""),
            })
        if not stories:
            log_warning("Hacker News API returned no stories. Using fallback.")
            return FALLBACK_HN_STORIES
        return stories
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log_warning(f"Hacker News API failed ({e}). Using fallback data.")
        return FALLBACK_HN_STORIES


def fetch_fx_rates():
    """
    Fetch USD to EUR, GBP, IDR, CAD exchange rates.
    Returns dict with currency -> rate.
    Falls back to realistic data on error.
    """
    try:
        data = fetch_json(FX_API_URL)
        rates = data.get("rates", {})
        if not rates:
            log_warning("Frankfurter API returned no rates. Using fallback.")
            return FALLBACK_FX
        # Ensure all required currencies are present
        required = ["EUR", "GBP", "IDR", "CAD"]
        for cur in required:
            if cur not in rates:
                log_warning(f"Missing rate for {cur}. Using fallback.")
                rates[cur] = FALLBACK_FX[cur]
        return rates
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log_warning(f"Frankfurter API failed ({e}). Using fallback data.")
        return FALLBACK_FX


# ------------------------------------------------------------------------------
# Synthetic data generation
# ------------------------------------------------------------------------------
def generate_marketing_spend():
    """
    Generate 90 days of daily marketing spend across channels and regions.
    Returns list of dicts with date, channel, region, spend, impressions, clicks, conversions.
    """
    random.seed(RANDOM_SEED)
    start_date = datetime.now().date() - timedelta(days=DAYS_OF_DATA - 1)
    rows = []
    for day_offset in range(DAYS_OF_DATA):
        date = start_date + timedelta(days=day_offset)
        for channel in CHANNELS:
            for region in REGIONS:
                # Base spend varies by channel and region
                base_spend = {
                    "paid_search": 500,
                    "paid_social": 300,
                    "developer_sponsorship": 200,
                    "community_events": 150,
                    "organic_direct": 50,
                }[channel]
                # Regional multiplier
                region_mult = {
                    "US-East": 1.2,
                    "US-West": 1.1,
                    "EU-Central": 0.9,
                    "APAC-SG": 0.8,
                    "LATAM": 0.7,
                }[region]
                # Daily noise
                noise = random.uniform(0.7, 1.3)
                spend = round(base_spend * region_mult * noise, 2)
                # Impressions, clicks, conversions based on spend
                impressions = int(spend * random.uniform(50, 100))
                ctr = random.uniform(0.01, 0.05)
                clicks = int(impressions * ctr)
                conversion_rate = random.uniform(0.02, 0.08)
                conversions = int(clicks * conversion_rate)
                rows.append({
                    "date": date.isoformat(),
                    "channel": channel,
                    "region": region,
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "platform_reported_conversions": conversions,
                })
    return rows


def generate_developer_accounts():
    """
    Generate 1200 developer accounts.
    Returns list of dicts with account_id, signup_date, channel, region, is_holdout, signup_method.
    """
    random.seed(RANDOM_SEED)
    start_date = datetime.now().date() - timedelta(days=DAYS_OF_DATA - 1)
    accounts = []
    for i in range(1, NUM_ACCOUNTS + 1):
        # Random signup date within the last 90 days
        signup_date = start_date + timedelta(days=random.randint(0, DAYS_OF_DATA - 1))
        channel = random.choice(CHANNELS)
        region = random.choice(REGIONS)
        is_holdout = random.random() < 0.1
        signup_method = random.choice(SIGNUP_METHODS)
        accounts.append({
            "account_id": f"acct_{i:04d}",
            "signup_date": signup_date.isoformat(),
            "channel": channel,
            "region": region,
            "is_holdout": is_holdout,
            "signup_method": signup_method,
        })
    return accounts


def generate_project_telemetry(accounts):
    """
    Generate project telemetry for each account.
    Returns list of dicts with project_id, account_id, provisioned_at, has_auth, has_storage,
    has_edge_functions, has_pgvector, time_to_first_query_min, compute_hours, db_size_mb,
    egress_gb, is_pro_upgrade, pro_upgrade_date, monthly_invoice_usd.
    """
    random.seed(RANDOM_SEED)
    projects = []
    for idx, acct in enumerate(accounts, start=1):
        account_id = acct["account_id"]
        signup_date = datetime.strptime(acct["signup_date"], "%Y-%m-%d").date()
        # Provisioned a few days after signup
        provisioned_at = signup_date + timedelta(days=random.randint(0, 7))
        has_auth = random.random() < 0.8
        has_storage = random.random() < 0.6
        has_edge_functions = random.random() < 0.4
        has_pgvector = random.random() < 0.3
        time_to_first_query_min = round(random.uniform(1, 30), 1)
        compute_hours = round(random.uniform(0, 500), 2)
        db_size_mb = round(random.uniform(10, 5000), 2)
        egress_gb = round(random.uniform(0, 100), 2)
        is_pro_upgrade = random.random() < 0.15
        pro_upgrade_date = None
        monthly_invoice_usd = 0.0
        if is_pro_upgrade:
            # Upgrade date after provisioned_at
            pro_upgrade_date = provisioned_at + timedelta(days=random.randint(1, 60))
            monthly_invoice_usd = round(random.uniform(25, 500), 2)
        projects.append({
            "project_id": f"proj_{idx:04d}",
            "account_id": account_id,
            "provisioned_at": provisioned_at.isoformat(),
            "has_auth": has_auth,
            "has_storage": has_storage,
            "has_edge_functions": has_edge_functions,
            "has_pgvector": has_pgvector,
            "time_to_first_query_min": time_to_first_query_min,
            "compute_hours": compute_hours,
            "db_size_mb": db_size_mb,
            "egress_gb": egress_gb,
            "is_pro_upgrade": is_pro_upgrade,
            "pro_upgrade_date": pro_upgrade_date.isoformat() if pro_upgrade_date else "",
            "monthly_invoice_usd": monthly_invoice_usd,
        })
    return projects


def generate_touchpoints(accounts):
    """
    Generate multi-touch touchpoint logs for each account.
    Returns list of dicts with account_id, touch_id, touch_timestamp, channel, campaign_id.
    """
    random.seed(RANDOM_SEED)
    touchpoints = []
    touch_counter = 1
    start_date = datetime.now().date() - timedelta(days=DAYS_OF_DATA - 1)
    for acct in accounts:
        account_id = acct["account_id"]
        signup_date = datetime.strptime(acct["signup_date"], "%Y-%m-%d").date()
        # Number of touchpoints per account: 1-5
        num_touches = random.randint(1, 5)
        for _ in range(num_touches):
            # Touch timestamp can be before or after signup, but within the 90-day window
            touch_date = start_date + timedelta(days=random.randint(0, DAYS_OF_DATA - 1))
            # Ensure timestamp is datetime
            touch_timestamp = datetime.combine(touch_date, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23), minutes=random.randint(0, 59)
            )
            channel = random.choice(CHANNELS)
            campaign_id = f"camp_{random.randint(1, 20):03d}"
            touchpoints.append({
                "account_id": account_id,
                "touch_id": f"touch_{touch_counter:04d}",
                "touch_timestamp": touch_timestamp.isoformat(),
                "channel": channel,
                "campaign_id": campaign_id,
            })
            touch_counter += 1
    return touchpoints


# ------------------------------------------------------------------------------
# CSV writing
# ------------------------------------------------------------------------------
def write_csv(filename, fieldnames, rows):
    """Write rows to a CSV file in seeds/ directory."""
    filepath = os.path.join(SEED_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {filepath}")


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    ensure_seed_dir()

    # 1. Fetch live API data
    print("Fetching GitHub data...")
    github_data = fetch_github_data()
    print("Fetching Hacker News data...")
    hn_stories = fetch_hackernews_data()
    print("Fetching FX rates...")
    fx_rates = fetch_fx_rates()

    # 2. Generate synthetic data
    print("Generating marketing spend...")
    marketing_spend = generate_marketing_spend()
    print("Generating developer accounts...")
    developer_accounts = generate_developer_accounts()
    print("Generating project telemetry...")
    project_telemetry = generate_project_telemetry(developer_accounts)
    print("Generating touchpoints...")
    touchpoints = generate_touchpoints(developer_accounts)

    # 3. Write CSV files
    # GitHub telemetry (single row)
    github_rows = [{
        "stars": github_data["stars"],
        "forks": github_data["forks"],
        "open_issues": github_data["open_issues"],
        "watchers": github_data["watchers"],
        "fetched_at": datetime.now().isoformat(),
    }]
    write_csv("raw_github_telemetry.csv", ["stars", "forks", "open_issues", "watchers", "fetched_at"], github_rows)

    # Hacker News buzz
    hn_rows = []
    for story in hn_stories:
        hn_rows.append({
            "title": story["title"],
            "points": story["points"],
            "num_comments": story["num_comments"],
            "created_at": story["created_at"],
        })
    write_csv("raw_hackernews_buzz.csv", ["title", "points", "num_comments", "created_at"], hn_rows)

    # FX rates
    fx_rows = []
    for currency, rate in fx_rates.items():
        fx_rows.append({
            "base_currency": "USD",
            "quote_currency": currency,
            "rate": rate,
            "fetched_at": datetime.now().isoformat(),
        })
    write_csv("raw_fx_rates.csv", ["base_currency", "quote_currency", "rate", "fetched_at"], fx_rows)

    # Marketing spend
    write_csv(
        "raw_marketing_spend.csv",
        ["date", "channel", "region", "spend", "impressions", "clicks", "platform_reported_conversions"],
        marketing_spend,
    )

    # Developer accounts
    write_csv(
        "raw_developer_accounts.csv",
        ["account_id", "signup_date", "channel", "region", "is_holdout", "signup_method"],
        developer_accounts,
    )

    # Project telemetry
    write_csv(
        "raw_project_telemetry.csv",
        [
            "project_id", "account_id", "provisioned_at", "has_auth", "has_storage",
            "has_edge_functions", "has_pgvector", "time_to_first_query_min",
            "compute_hours", "db_size_mb", "egress_gb", "is_pro_upgrade",
            "pro_upgrade_date", "monthly_invoice_usd",
        ],
        project_telemetry,
    )

    # Touchpoints
    write_csv(
        "raw_touchpoints.csv",
        ["account_id", "touch_id", "touch_timestamp", "channel", "campaign_id"],
        touchpoints,
    )

    print("All raw data files written successfully.")


if __name__ == "__main__":
    main()