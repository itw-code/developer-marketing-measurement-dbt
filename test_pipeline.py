#!/usr/bin/env python3
"""
Standalone QA test suite for the developer-marketing-measurement-dbt pipeline.

Runs against a DuckDB database (default: dev.duckdb) or validates seed presence
and row-level invariants. Designed to be runnable both locally and in CI:

    python test_pipeline.py

Exits with code 0 on success, non-zero on any failure.
"""

from __future__ import annotations

import os
import sys
import csv
from pathlib import Path
from typing import Callable

try:
    import duckdb
except ImportError:  # pragma: no cover - dependency guard
    duckdb = None


# ---------------------------------------------------------------------------
# Terminal formatting
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TestSummary:
    """Collects pass/fail results and prints a formatted summary."""

    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append((name, passed, detail))
        status = f"{GREEN}\u2713 PASS{RESET}" if passed else f"{RED}\u2717 FAIL{RESET}"
        suffix = f"  ({detail})" if detail else ""
        print(f"  {status}  {name}{suffix}")

    @property
    def passed(self) -> bool:
        return all(passed for _, passed, _ in self.results)

    def print_summary(self) -> None:
        total = len(self.results)
        n_pass = sum(1 for _, passed, _ in self.results if passed)
        n_fail = total - n_pass

        print()
        print(f"{BOLD}========================================{RESET}")
        print(f"{BOLD}  PIPELINE TEST SUMMARY{RESET}")
        print(f"{BOLD}========================================{RESET}")
        print(f"  Total : {total}")
        print(f"  {GREEN}Passed{RESET}: {n_pass}")
        if n_fail:
            print(f"  {RED}Failed{RESET}: {n_fail}")
        else:
            print(f"  Failed: 0")

        overall = (
            f"{GREEN}{BOLD}ALL TESTS PASSED{RESET}"
            if self.passed
            else f"{RED}{BOLD}TESTS FAILED{RESET}"
        )
        print(f"  Result: {overall}")
        print(f"{BOLD}========================================{RESET}")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
SEEDS_DIR = REPO_ROOT / "seeds"
DEFAULT_DB = REPO_ROOT / "dev_measurement.duckdb"

REQUIRED_SEEDS = [
    "raw_marketing_spend.csv",
    "raw_touchpoints.csv",
    "raw_developer_accounts.csv",
    "raw_project_telemetry.csv",
    "raw_github_telemetry.csv",
    "raw_hackernews_buzz.csv",
    "raw_fx_rates.csv",
]


def _connect(db_path: Path):
    if duckdb is None:
        return None
    if not db_path.exists():
        return None
    # Read-write connection is safe; tests only run read queries.
    return duckdb.connect(str(db_path), read_only=True)


def _table_exists(con, table_name: str) -> bool:
    try:
        rows = con.execute(
            "select 1 from information_schema.tables where table_name = ? limit 1",
            [table_name],
        ).fetchall()
        return len(rows) > 0
    except Exception:
        return False


def _scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_seeds_exist(summary: TestSummary) -> None:
    print(f"{BOLD}Seed file presence{RESET}")
    for fname in REQUIRED_SEEDS:
        path = SEEDS_DIR / fname
        summary.record(
            f"seeds/{fname} exists",
            path.exists(),
            "" if path.exists() else "missing",
        )


def test_seed_row_counts(summary: TestSummary) -> None:
    print(f"{BOLD}Seed row counts{RESET}")
    for fname in REQUIRED_SEEDS:
        path = SEEDS_DIR / fname
        if not path.exists():
            summary.record(f"seeds/{fname} row count > 0", False, "file missing")
            continue
        try:
            with path.open("r", newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                header = next(reader, None)
                if header is None:
                    summary.record(f"seeds/{fname} row count > 0", False, "no header")
                    continue
                row_count = sum(1 for _ in reader)
            summary.record(
                f"seeds/{fname} row count > 0",
                row_count > 0,
                f"{row_count} rows",
            )
        except Exception as exc:  # pragma: no cover
            summary.record(f"seeds/{fname} row count > 0", False, str(exc))


def test_raw_spend_matches_seed(summary: TestSummary, con) -> None:
    """Raw staging spend must reconcile with the raw seed spend."""
    print(f"{BOLD}Spend reconciliation (raw seed vs staging){RESET}")

    seed_path = SEEDS_DIR / "raw_marketing_spend.csv"
    if not seed_path.exists():
        summary.record("raw seed spend present", False, "file missing")
        return

    try:
        seed_rows = con.execute(
            "select coalesce(sum(spend), 0) from read_csv_auto(?)",
            [str(seed_path)],
        ).fetchone()[0]
    except Exception as exc:
        summary.record("raw seed spend readable", False, str(exc))
        return

    if not _table_exists(con, "stg_marketing_ad_spend"):
        summary.record(
            "stg_marketing_ad_spend exists for reconciliation",
            False,
            "run dbt first",
        )
        return

    staging_spend = _scalar(con, "select coalesce(sum(spend_usd), 0) from stg_marketing_ad_spend")
    drift = abs(float(seed_rows) - float(staging_spend))
    summary.record(
        "seed spend == stg_marketing_ad_spend spend",
        drift < 0.01,
        f"drift={drift:.6f}",
    )


def test_mart_spend_drift(summary: TestSummary, con) -> None:
    """Zero calculation drift between staging and marts for total spend."""
    print(f"{BOLD}Spend reconciliation (staging vs marts){RESET}")

    if not _table_exists(con, "stg_marketing_ad_spend"):
        summary.record("stg_marketing_ad_spend exists", False, "run dbt first")
        return
    if not _table_exists(con, "fct_channel_efficiency_daily"):
        summary.record("fct_channel_efficiency_daily exists", False, "run dbt first")
        return

    staging_spend = float(
        _scalar(con, "select coalesce(sum(spend_usd), 0) from stg_marketing_ad_spend")
    )
    mart_spend = float(
        _scalar(con, "select coalesce(sum(spend_usd), 0) from fct_channel_efficiency_daily")
    )
    drift = abs(staging_spend - mart_spend)
    summary.record(
        "staging spend == mart spend",
        drift < 0.01,
        f"drift={drift:.6f}",
    )


def test_attribution_weights(summary: TestSummary, con) -> None:
    """Attribution weights sum to 1.0 per account (linear within tolerance)."""
    print(f"{BOLD}Attribution weight invariants{RESET}")

    if not _table_exists(con, "int_attribution_paths"):
        summary.record("int_attribution_paths exists", False, "run dbt first")
        return

    try:
        row = con.execute(
            """
            select
                count(*) as n_accounts,
                sum(
                    case
                        when abs(total_ft - 1.0) > 0.001
                          or abs(total_lt - 1.0) > 0.001
                          or total_lin < 0.999
                          or total_lin > 1.001
                        then 1 else 0
                    end
                ) as n_violations
            from (
                select
                    account_id,
                    sum(first_touch_weight) as total_ft,
                    sum(last_touch_weight) as total_lt,
                    sum(linear_weight) as total_lin
                from int_attribution_paths
                group by account_id
            )
            """
        ).fetchone()
    except Exception as exc:
        summary.record("attribution weights query", False, str(exc))
        return

    n_accounts, n_violations = int(row[0]), int(row[1])
    if n_accounts == 0:
        summary.record("attribution paths have accounts", False, "0 accounts")
        return

    summary.record(
        "attribution weights sum to 1.0 per account",
        n_violations == 0,
        f"{n_violations}/{n_accounts} violating accounts",
    )


def test_composite_grain_uniqueness(summary: TestSummary, con) -> None:
    """fct_channel_efficiency_daily must be unique on its natural grain."""
    print(f"{BOLD}Composite grain uniqueness{RESET}")

    if not _table_exists(con, "fct_channel_efficiency_daily"):
        summary.record("fct_channel_efficiency_daily exists", False, "run dbt first")
        return

    try:
        dupes = _scalar(
            con,
            """
            select count(*) from (
                select channel, date_day, count(*) as c
                from fct_channel_efficiency_daily
                group by channel, date_day
                having count(*) > 1
            )
            """,
        )
    except Exception as exc:
        summary.record("grain uniqueness query", False, str(exc))
        return

    summary.record(
        "fct_channel_efficiency_daily unique on (channel, report_date)",
        int(dupes) == 0,
        f"{dupes} duplicate groups",
    )


def test_non_negative_spend(summary: TestSummary, con) -> None:
    """No negative spend in either staging or mart spend columns."""
    print(f"{BOLD}Non-negative spend{RESET}")

    checks = [
        ("stg_marketing_ad_spend", "spend_usd"),
        ("fct_channel_efficiency_daily", "spend_usd"),
    ]
    for table, col in checks:
        if not _table_exists(con, table):
            summary.record(f"{table}.{col} non-negative", False, "table missing")
            continue
        try:
            neg = _scalar(
                con,
                f"select count(*) from {table} where {col} < 0",
            )
        except Exception as exc:
            summary.record(f"{table}.{col} non-negative", False, str(exc))
            continue
        summary.record(
            f"{table}.{col} non-negative",
            int(neg) == 0,
            f"{neg} negative rows",
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"{BOLD}developer-marketing-measurement-dbt :: pipeline QA{RESET}")
    print(f"Repo root : {REPO_ROOT}")
    print(f"Database  : {DEFAULT_DB}")
    print()

    summary = TestSummary()

    test_seeds_exist(summary)
    test_seed_row_counts(summary)

    con = _connect(DEFAULT_DB)
    if con is None:
        if duckdb is None:
            print(f"{YELLOW}duckdb not installed; skipping DB-backed tests.{RESET}")
        else:
            print(
                f"{YELLOW}DuckDB database not found at {DEFAULT_DB}; "
                f"skipping DB-backed tests (run dbt first).{RESET}"
            )
        summary.record("DuckDB database available", False, "database missing")
    else:
        try:
            test_raw_spend_matches_seed(summary, con)
            test_mart_spend_drift(summary, con)
            test_attribution_weights(summary, con)
            test_composite_grain_uniqueness(summary, con)
            test_non_negative_spend(summary, con)
        finally:
            con.close()

    summary.print_summary()
    return 0 if summary.passed else 1


if __name__ == "__main__":
    sys.exit(main())
