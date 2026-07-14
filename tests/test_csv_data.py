"""Tests for the precomputed CSV data files.

These tests verify that the pipeline CSVs have the correct structure
and can be parsed by the frontend. Only tax year 2027 is meaningful
for the Texas rebate dashboard.
"""

import csv
from pathlib import Path

import pytest


DATA_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data"
EXPECTED_YEARS = [2027]
EXPECTED_BRACKETS = {
    "$25k or less",
    "$25k - $50k",
    "$50k - $75k",
    "$75k - $100k",
    "$100k - $150k",
    "$150k - $200k",
    "Over $200k",
}


def _load_csv(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not generated yet")
    with open(path, "r") as f:
        return list(csv.DictReader(f))


class TestDistributionalImpactCSV:
    """Tests for distributional_impact.csv."""

    def test_has_required_columns(self):
        data = _load_csv("distributional_impact.csv")
        required = ["year", "decile", "average_change", "relative_change"]
        for row in data:
            for col in required:
                assert col in row, f"Missing column: {col}"

    def test_has_all_deciles(self):
        data = _load_csv("distributional_impact.csv")
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            deciles = {r["decile"] for r in year_data}
            expected = {str(d) for d in range(1, 11)}
            assert deciles == expected, f"Missing deciles for year {year}"

    def test_flat_rebate_average(self):
        """A universal $1,500/household rebate must average $1,500 in
        every decile."""
        data = _load_csv("distributional_impact.csv")
        for row in data:
            assert abs(float(row["average_change"]) - 1500) < 0.01


class TestMetricsCSV:
    """Tests for metrics.csv."""

    def test_has_required_metrics(self):
        data = _load_csv("metrics.csv")
        required_metrics = [
            "budgetary_impact",
            "total_cost",
            "households",
            "winners_rate",
            "winners_rate_residents",
            "poverty_baseline_rate",
            "poverty_reform_rate",
        ]
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            metrics = {r["metric"] for r in year_data}
            for metric in required_metrics:
                assert metric in metrics, (
                    f"Missing metric '{metric}' for year {year}"
                )

    def test_cost_matches_fund_math(self):
        """One check per household should cost roughly the ~$17B the
        press release's fund arithmetic implies."""
        data = _load_csv("metrics.csv")
        m = {r["metric"]: float(r["value"]) for r in data}
        assert 12e9 < m["total_cost"] < 22e9
        assert abs(m["total_cost"] - m["households"] * 1500) < 1e6

    def test_universal_winners(self):
        data = _load_csv("metrics.csv")
        m = {r["metric"]: float(r["value"]) for r in data}
        assert m["winners_rate"] == 100.0
        assert m["winners_rate_residents"] == 100.0
        assert m["losers"] == 0.0

    def test_poverty_falls(self):
        data = _load_csv("metrics.csv")
        m = {r["metric"]: float(r["value"]) for r in data}
        assert m["poverty_reform_rate"] < m["poverty_baseline_rate"]


class TestWinnersLosersCSV:
    """Tests for winners_losers.csv."""

    def test_values_sum_to_one(self):
        data = _load_csv("winners_losers.csv")
        for row in data:
            total = (
                float(row["gain_more_5pct"])
                + float(row["gain_less_5pct"])
                + float(row["no_change"])
                + float(row["lose_less_5pct"])
                + float(row["lose_more_5pct"])
            )
            assert abs(total - 1.0) < 0.01, f"Row does not sum to 1: {row}"

    def test_no_losers(self):
        data = _load_csv("winners_losers.csv")
        for row in data:
            assert float(row["lose_less_5pct"]) == 0.0
            assert float(row["lose_more_5pct"]) == 0.0


class TestIncomeBracketsCSV:
    """Tests for income_brackets.csv."""

    def test_has_all_brackets(self):
        data = _load_csv("income_brackets.csv")
        for year in EXPECTED_YEARS:
            year_data = [r for r in data if int(r["year"]) == year]
            brackets = {r["bracket"] for r in year_data}
            assert brackets == EXPECTED_BRACKETS, (
                f"Missing brackets for year {year}"
            )

    def test_flat_average(self):
        data = _load_csv("income_brackets.csv")
        for row in data:
            if float(row["beneficiaries"]) > 0:
                assert abs(float(row["avg_benefit"]) - 1500.0) < 0.01


class TestCongressionalDistrictsCSV:
    """Tests for congressional_districts.csv (TX only)."""

    def test_texas_only(self):
        data = _load_csv("congressional_districts.csv")
        states = {r["state"] for r in data}
        assert states == {"TX"}, f"Expected only TX rows, got {states}"

    def test_thirty_eight_districts(self):
        """Texas has 38 congressional districts."""
        data = _load_csv("congressional_districts.csv")
        districts = {r["district"] for r in data}
        expected = {f"TX-{d:02d}" for d in range(1, 39)}
        assert districts == expected, (
            f"Expected TX-01..TX-38, got {sorted(districts)[:5]}..."
        )

    def test_flat_average_change(self):
        data = _load_csv("congressional_districts.csv")
        for row in data:
            assert abs(float(row["average_household_income_change"]) - 1500.0) < 0.01
