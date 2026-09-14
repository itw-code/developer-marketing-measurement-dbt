# Developer Marketing Measurement dbt Pipeline
## Causal Attribution Triangulation, Media Mix Modeling & Developer PLG Telemetry

[![CI Pipeline](https://github.com/itw-code/developer-marketing-measurement-dbt/actions/workflows/dbt.yml/badge.svg)](https://github.com/itw-code/developer-marketing-measurement-dbt/actions)
[![dbt-duckdb](https://img.shields.io/badge/dbt--duckdb-1.10.1-blue.svg)](https://github.com/duckdb/dbt-duckdb)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Author: itw-code](https://img.shields.io/badge/Author-Ihsan%20Tri%20Wanda-059669.svg)](https://github.com/itw-code)

An open-source, production-grade analytics engineering pipeline built to solve the **marketing measurement crisis in developer tooling, open-source ecosystems, and Backend-as-a-Service (BaaS) platforms**.

Rather than relying on platform-reported vanity metrics from walled gardens (Google Ads, Meta, LinkedIn) that over-claim conversions by 300%–700%, this project implements **Attribution Triangulation**: reconciling Multi-Touch Attribution (MTA), Media Mix Modeling (MMM with adstock and saturation dynamics), and always-on Incrementality experiments (geo-lift and universal holdouts) into a unified, tested semantic layer.

---

## Telemetry Architecture

```
+---------------------------------------------------------------------------------------------------------------+
|                                    DATA INGESTION & PIPELINE ARCHITECTURE                                     |
+---------------------------------------------------------------------------------------------------------------+
| LIVE FREE APIS                         SYNTHETIC CAMPAIGN & PLG TELEMETRY                                     |
|  - GitHub REST API (Supabase stats)     - 90-Day Multi-Channel Spend (5 Channels, 5 Matched Geo Regions)      |
|  - Hacker News Algolia (Dev sentiment)  - 1,200 Developer Accounts (GitHub OAuth vs Email, 10% Holdout)       |
|  - Frankfurter ECB API (FX rates)       - 3,544 Multi-Touch Attribution Touchpoint Event Logs                 |
+---------------------------------------------------------------------------------------------------------------+
                                                       |
                                                       v
+---------------------------------------------------------------------------------------------------------------+
| STAGING LAYER (`models/staging/` - Views)                                                                     |
|  - `stg_github_telemetry`: Repo star velocity, forks, and open issue backlog                                 |
|  - `stg_hackernews_buzz`: Weighted developer sentiment score: (points * 1.5 + comments * 2.0)                 |
|  - `stg_fx_rates`: Daily currency exchange normalization to USD                                              |
|  - `stg_marketing_ad_spend`: Clean daily spend, impressions, clicks, CPC, CTR, platform claims                |
|  - `stg_developer_plg_events`: Account provisioning, feature flags (Auth, DB, Vector), Pro tier conversions   |
|  - `stg_touchpoints`: Multi-touch campaign events ordered by timestamp                                        |
+---------------------------------------------------------------------------------------------------------------+
                                                       |
                                                       v
+---------------------------------------------------------------------------------------------------------------+
| INTERMEDIATE LAYER (`models/intermediate/` - Views)                                                           |
|  - `int_adstock_and_saturation`: Geometric adstock carryover (alpha = 0.70) + Hill function saturation curve  |
|  - `int_attribution_paths`: First-Touch (1.0), Last-Touch (1.0), Linear, and 7-day half-life Time-Decay       |
|  - `int_geo_experiment_clusters`: Matched-market geo testing (Treatment vs Control vs Holdout cohorts)        |
|  - `int_developer_lifecycle_states`: Time-to-first-query (TTFQ) speed, feature adoption tiers, usage health  |
+---------------------------------------------------------------------------------------------------------------+
                                                       |
                                                       v
+---------------------------------------------------------------------------------------------------------------+
| MARTS LAYER (`models/marts/` - Materialized Tables)                                                           |
|  - `fct_marketing_triangulation_daily`: Side-by-side reconciliation of Platform vs MTA vs MMM vs Geo-Lift     |
|  - `fct_channel_efficiency_daily`: Blended CAC, CPC, CTR, Pro upgrades, and Payback Period in months          |
|  - `fct_developer_cohort_retention`: Weekly signup cohorts tracking 7-day and 30-day project retention       |
|  - `dim_campaigns`: Campaign taxonomy mapped to developer personas (Indie Hacker, Startup, Enterprise)       |
|  - `dim_developer_projects`: Dimensional grain of developer projects, feature tiers, and MRR contribution     |
+---------------------------------------------------------------------------------------------------------------+
                                                       |
                                                       v
+---------------------------------------------------------------------------------------------------------------+
| CONTINUOUS ASSURANCE & QA SUITE                                                                               |
|  - 2 Singular dbt Invariant Tests (`assert_attribution_weights_sum_to_one`, `assert_spend_matches_staging...`)  |
|  - Standalone Invariant Verification Runner (`test_pipeline.py`): 20 automated checks with ZERO spend drift   |
|  - GitHub Actions CI/CD (`.github/workflows/dbt.yml`): automated build & test on every push                   |
+---------------------------------------------------------------------------------------------------------------+
```

---

## Core Mathematical Models

### 1. Geometric Adstock Carryover
Developer marketing creates lingering awareness rather than instant impulsive conversions. We model memory carryover across daily spend:
$$\text{Adstock}(x_t, \alpha) = x_t + \sum_{i=1}^{4} \alpha^i \cdot x_{t-i}, \quad \alpha = 0.70$$

### 2. Hill Function Diminishing Returns (Saturation)
Marketing channels experience diminishing marginal returns at scale. We model response saturation using a generalized Hill function:
$$\text{Response}(S) = \frac{S^2}{K^2 + S^2}$$
Where $K = \$2,500$ represents the half-saturation point and $S$ is adstocked spend.

### 3. Multi-Touch Attribution (MTA) Formulations
For each converted paying developer project $p$, attribution weights across historical touchpoints $t \in T_p$ are calculated:
- **First-Touch**: $W_{t,\text{first}} = 1$ if $t = 1$, else $0$.
- **Last-Touch**: $W_{t,\text{last}} = 1$ if $t = |T_p|$, else $0$.
- **Linear**: $W_{t,\text{linear}} = \frac{1}{|T_p|}$.
- **Exponential Time-Decay**: $W_{t,\text{decay}} = \frac{e^{-\lambda \cdot \Delta d_t}}{\sum_{j} e^{-\lambda \cdot \Delta d_j}}$, with $\lambda = 0.05$ (approx. 14-day half-life).

### 4. Platform Over-Reporting Bias
Quantifies the systematic inflation in platform-reported numbers compared to causal MMM estimations:
$$\text{Bias}_{\text{Platform}} = \left( \frac{\text{Conversions}_{\text{Platform}} - \text{Conversions}_{\text{Causal MMM}}}{\text{Conversions}_{\text{Causal MMM}}} \right) \times 100\%$$

---

## Live Triangulation Output (Sample Mart)

Queried directly from `fct_marketing_triangulation_daily`:

| Channel | Daily Spend | Platform Claim | MTA First-Touch | MTA Last-Touch | Causal MMM | Platform Bias | Incremental CAC | Incremental ROAS |
|---|---|---|---|---|---|---|---|---|
| **paid_search** | $2,174.09 | 241.0 | 1.0 | 2.0 | 30.2 | **+698.0%** | $71.99 | 2.08x |
| **paid_social** | $1,468.07 | 180.0 | 0.0 | 0.0 | 25.6 | **+603.1%** | $57.35 | 2.62x |
| **developer_sponsorship** | $864.82 | 127.0 | 0.0 | 1.0 | 17.6 | **+621.6%** | $49.14 | 3.05x |
| **community_events** | $704.88 | 55.0 | 0.0 | 0.0 | 13.6 | **+304.4%** | $51.83 | 2.89x |
| **organic_direct** | $217.51 | 22.0 | 0.0 | 0.0 | 2.1 | **+947.6%** | $103.58 | 1.45x |

---

## Quickstart & Local Reproduction

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/itw-code/developer-marketing-measurement-dbt.git
cd developer-marketing-measurement-dbt
pip install -r requirements.txt
```

### 2. Fetch Live Data & Generate Telemetry
Queries live GitHub, Hacker News, and Frankfurter APIs, writing CSV seeds into `seeds/`:
```bash
python ingestion/load_raw.py
```

### 3. Build & Test dbt Models
Executes seeds, views, table marts, and data tests in an embedded DuckDB database (`dev_measurement.duckdb`):
```bash
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

### 4. Run Automated Invariant QA Suite
Runs 20 automated data quality checks, validating seed row counts, mathematical grain uniqueness, non-negative spend, and zero drift:
```bash
python test_pipeline.py
```

Expected output:
```text
========================================
  PIPELINE TEST SUMMARY
========================================
  Total : 20
  Passed: 20
  Failed: 0
  Result: ALL TESTS PASSED
========================================
```

---

## Repository Structure

```
.
├── .github/workflows/
│   └── dbt.yml                          # Automated CI/CD GitHub Actions workflow
├── ingestion/
│   └── load_raw.py                      # Live API fetcher & synthetic telemetry generator
├── macros/
│   ├── non_negative.sql                 # Generic schema test for non-negative values
│   └── unique_grain.sql                 # Composite grain uniqueness test
├── models/
│   ├── staging/                         # Clean casts & renames from raw seeds
│   │   ├── _staging__models.yml
│   │   ├── stg_developer_plg_events.sql
│   │   ├── stg_fx_rates.sql
│   │   ├── stg_github_telemetry.sql
│   │   ├── stg_hackernews_buzz.sql
│   │   ├── stg_marketing_ad_spend.sql
│   │   └── stg_touchpoints.sql
│   ├── intermediate/                    # Core mathematical transformations
│   │   ├── _intermediate__models.yml
│   │   ├── int_adstock_and_saturation.sql
│   │   ├── int_attribution_paths.sql
│   │   ├── int_developer_lifecycle_states.sql
│   │   └── int_geo_experiment_clusters.sql
│   └── marts/                           # Final consumption marts
│       ├── _marts__models.yml
│       ├── dim_campaigns.sql
│       ├── dim_developer_projects.sql
│       ├── fct_channel_efficiency_daily.sql
│       ├── fct_developer_cohort_retention.sql
│       └── fct_marketing_triangulation_daily.sql
├── seeds/                               # Ingested & generated CSV seeds
├── tests/                               # Singular dbt tests
│   ├── assert_attribution_weights_sum_to_one.sql
│   └── assert_spend_matches_staging_to_marts.sql
├── dbt_project.yml                      # dbt configuration
├── profiles.yml                         # DuckDB profile configuration
├── requirements.txt                     # Python dependencies
├── test_pipeline.py                     # Standalone Python + DuckDB invariant test runner
├── LICENSE                              # MIT License
└── README.md
```

---

## Author

**Ihsan Tri Wanda**  
Senior Data Analyst & Analytics Engineering Lead  
- **GitHub**: [@itw-code](https://github.com/itw-code)  
- **LinkedIn**: [linkedin.com/in/ihsan3wanda](https://www.linkedin.com/in/ihsan3wanda/)  
- **Email**: [ihsantriwanda@gmail.com](mailto:ihsantriwanda@gmail.com)  
