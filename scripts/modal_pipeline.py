"""Modal-based state-level data generation pipeline for the Texas
$1,500 rebate check dashboard ("Money in Your Pocket" proposal).

The proposal sends one $1,500 check per household (assumption — the
press release does not specify eligibility; this reading matches the
stated Economic Stabilization Fund draw of ~$17 billion). Because the
rebate is a flat, universal transfer with no phase-out, the pipeline
runs a single current-law simulation and applies the rebate
arithmetically:

- every household's net income rises by exactly $1,500, and
- poverty impacts add each household's rebate to its members' SPM
  unit resources (allocated per person, so multi-SPM-unit households
  split the check in proportion to their members).

Runs against the ECPS state file (``states/TX.h5``), the same dataset
family as the district pipeline, and writes CSVs to
``frontend/public/data/``.

Usage:
    modal run scripts/modal_pipeline.py
"""

import os

import modal


app = modal.App("tx-rebate-checks-pipeline")

POLICYENGINE_US_PIN = "policyengine-us==1.768.2"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        POLICYENGINE_US_PIN,
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "huggingface_hub",
    )
)

# Matches tx_rebate_calc.rebate (the Modal worker only sees this file).
REBATE_PER_HOUSEHOLD = 1_500
YEAR = 2027
ESF_AVAILABLE = 17_000_000_000  # $27B fund minus $10B retained

TX_DATASET = "hf://policyengine/policyengine-us-data/states/TX.h5"


def _spm_rebate(sim, year: int):
    """Allocate the per-household rebate to SPM units.

    The check is per household; each member carries an equal share, and
    an SPM unit receives the sum of its members' shares (identical to
    the full check for the vast majority of households, which contain a
    single SPM unit).

    Returns (spm_rebate, person_to_spm_index) so callers can also map
    SPM-level results back to persons.
    """
    import numpy as np

    spm_ids = np.array(sim.calculate("spm_unit_id", period=year))
    spm_ids_person = np.array(
        sim.calculate("spm_unit_id", period=year, map_to="person")
    )
    hh_size_person = np.array(
        sim.calculate("household_count_people", period=year, map_to="person")
    )
    share_person = REBATE_PER_HOUSEHOLD / np.maximum(hh_size_person, 1)

    order = np.argsort(spm_ids)
    person_to_spm = order[np.searchsorted(spm_ids[order], spm_ids_person)]
    spm_rebate = np.zeros(len(spm_ids))
    np.add.at(spm_rebate, person_to_spm, share_person)
    return spm_rebate, person_to_spm


@app.function(
    image=image,
    memory=32768,
    timeout=3600,
    retries=1,
)
def calculate_impacts() -> dict:
    """Run the TX state-level analysis and return distributional /
    fiscal / poverty / bracket breakdowns."""
    import numpy as np
    from policyengine_us import Microsimulation

    print(f"Starting TX rebate calculation for {YEAR}...")

    sim = Microsimulation(dataset=TX_DATASET)

    # ===== FISCAL IMPACT =====
    household_weight = np.array(sim.calculate("household_weight", period=YEAR))
    total_households = float(household_weight.sum())
    total_cost = total_households * REBATE_PER_HOUSEHOLD

    # Sanity: the universal per-household reading should land near the
    # press release's implied $17B fund draw.
    if not (12e9 < total_cost < 22e9):
        raise RuntimeError(
            f"Total cost ${total_cost/1e9:.1f}B is far from the ~$17B "
            "ESF draw the proposal implies — check the dataset/weights."
        )
    print(
        f"  {total_households:,.0f} households x ${REBATE_PER_HOUSEHOLD:,} "
        f"= ${total_cost/1e9:.1f}B (ESF available: ${ESF_AVAILABLE/1e9:.0f}B)"
    )

    budgetary_impact = -total_cost

    baseline_net_income = np.array(
        sim.calculate("household_net_income", period=YEAR, map_to="household")
    )
    change_arr = np.full_like(baseline_net_income, float(REBATE_PER_HOUSEHOLD))
    weight_arr = household_weight

    person_weight = np.array(sim.calculate("person_weight", period=YEAR))
    total_residents = float(person_weight.sum())

    # ===== INCOME DECILE =====
    decile = np.array(
        sim.calculate("household_income_decile", period=YEAR, map_to="household")
    )
    decile_average = {}
    decile_relative = {}
    for d in range(1, 11):
        dmask = decile == d
        d_weight = weight_arr[dmask]
        d_count = float(d_weight.sum())
        if d_count > 0:
            d_baseline_sum = float(
                (baseline_net_income[dmask] * d_weight).sum()
            )
            d_change_sum = float((change_arr[dmask] * d_weight).sum())
            decile_average[str(d)] = d_change_sum / d_count
            decile_relative[str(d)] = (
                d_change_sum / d_baseline_sum if d_baseline_sum != 0 else 0.0
            )
        else:
            decile_average[str(d)] = 0.0
            decile_relative[str(d)] = 0.0

    intra_bounds = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
    intra_labels = [
        "Lose more than 5%",
        "Lose less than 5%",
        "No change",
        "Gain less than 5%",
        "Gain more than 5%",
    ]
    people_per_hh = np.array(
        sim.calculate("household_count_people", period=YEAR, map_to="household")
    )
    capped_baseline = np.maximum(baseline_net_income, 1)
    rel_change_arr = change_arr / capped_baseline
    people_weighted = people_per_hh * weight_arr

    intra_decile_deciles = {label: [] for label in intra_labels}
    for d in range(1, 11):
        dmask = decile == d
        d_people = people_weighted[dmask]
        d_total_people = d_people.sum()
        d_rel = rel_change_arr[dmask]
        for lower, upper, label in zip(
            intra_bounds[:-1], intra_bounds[1:], intra_labels
        ):
            in_group = (d_rel > lower) & (d_rel <= upper)
            proportion = (
                float(d_people[in_group].sum() / d_total_people)
                if d_total_people > 0
                else 0.0
            )
            intra_decile_deciles[label].append(proportion)
    intra_decile_all = {
        label: sum(intra_decile_deciles[label]) / 10 for label in intra_labels
    }

    # ===== POVERTY =====
    # Baseline and reform both computed from SPM resources vs threshold
    # so the two scenarios use an identical definition.
    spm_rebate, person_to_spm = _spm_rebate(sim, YEAR)
    resources = np.array(sim.calculate("spm_unit_net_income", period=YEAR))
    threshold = np.array(sim.calculate("spm_unit_spm_threshold", period=YEAR))

    pov_bl_spm = resources < threshold
    pov_rf_spm = (resources + spm_rebate) < threshold
    deep_bl_spm = resources < 0.5 * threshold
    deep_rf_spm = (resources + spm_rebate) < 0.5 * threshold

    age_arr = np.array(sim.calculate("age", period=YEAR))
    is_child = age_arr < 18
    pw_arr = person_weight

    def _person_rate(spm_status, mask=None):
        person_status = spm_status[person_to_spm]
        if mask is None:
            return float((person_status * pw_arr).sum() / pw_arr.sum() * 100)
        denom = pw_arr[mask].sum()
        return (
            float((person_status[mask] * pw_arr[mask]).sum() / denom * 100)
            if denom > 0
            else 0.0
        )

    poverty_baseline_rate = _person_rate(pov_bl_spm)
    poverty_reform_rate = _person_rate(pov_rf_spm)
    poverty_rate_change = poverty_reform_rate - poverty_baseline_rate
    poverty_percent_change = (
        poverty_rate_change / poverty_baseline_rate * 100
        if poverty_baseline_rate > 0
        else 0.0
    )

    child_poverty_baseline_rate = _person_rate(pov_bl_spm, is_child)
    child_poverty_reform_rate = _person_rate(pov_rf_spm, is_child)
    child_poverty_rate_change = (
        child_poverty_reform_rate - child_poverty_baseline_rate
    )
    child_poverty_percent_change = (
        child_poverty_rate_change / child_poverty_baseline_rate * 100
        if child_poverty_baseline_rate > 0
        else 0.0
    )

    deep_poverty_baseline_rate = _person_rate(deep_bl_spm)
    deep_poverty_reform_rate = _person_rate(deep_rf_spm)
    deep_poverty_rate_change = (
        deep_poverty_reform_rate - deep_poverty_baseline_rate
    )
    deep_poverty_percent_change = (
        deep_poverty_rate_change / deep_poverty_baseline_rate * 100
        if deep_poverty_baseline_rate > 0
        else 0.0
    )

    deep_child_poverty_baseline_rate = _person_rate(deep_bl_spm, is_child)
    deep_child_poverty_reform_rate = _person_rate(deep_rf_spm, is_child)
    deep_child_poverty_rate_change = (
        deep_child_poverty_reform_rate - deep_child_poverty_baseline_rate
    )
    deep_child_poverty_percent_change = (
        deep_child_poverty_rate_change / deep_child_poverty_baseline_rate * 100
        if deep_child_poverty_baseline_rate > 0
        else 0.0
    )

    print(
        f"  poverty {poverty_baseline_rate:.2f}% -> {poverty_reform_rate:.2f}%"
        f"  child {child_poverty_baseline_rate:.2f}% -> "
        f"{child_poverty_reform_rate:.2f}%"
    )

    # ===== INCOME BRACKETS =====
    # Households grouped by AGI (Texas has no state income tax, so there
    # is no state taxable-income measure to key on). Every household is
    # affected — the rebate is universal.
    agi = np.array(
        sim.calculate("adjusted_gross_income", period=YEAR, map_to="household")
    )
    income_brackets = [
        (-float("inf"), 25_000, "$25k or less"),
        (25_000, 50_000, "$25k - $50k"),
        (50_000, 75_000, "$50k - $75k"),
        (75_000, 100_000, "$75k - $100k"),
        (100_000, 150_000, "$100k - $150k"),
        (150_000, 200_000, "$150k - $200k"),
        (200_000, float("inf"), "Over $200k"),
    ]
    by_income_bracket = []
    for min_inc, max_inc, label in income_brackets:
        mask = (agi > min_inc) & (agi <= max_inc)
        n = float(weight_arr[mask].sum())
        by_income_bracket.append({
            "bracket": label,
            "beneficiaries": n,
            "total_cost": n * REBATE_PER_HOUSEHOLD,
            "avg_benefit": float(REBATE_PER_HOUSEHOLD) if n > 0 else 0.0,
        })

    print("  Done.")
    return {
        "year": YEAR,
        "budget": {
            "budgetary_impact": budgetary_impact,
            "federal_tax_revenue_impact": 0.0,
            "state_tax_revenue_impact": 0.0,
            "tax_revenue_impact": 0.0,
            "households": total_households,
        },
        "decile": {"average": decile_average, "relative": decile_relative},
        "intra_decile": {"all": intra_decile_all, "deciles": intra_decile_deciles},
        "total_cost": total_cost,
        "beneficiaries": total_households,
        "avg_benefit": float(REBATE_PER_HOUSEHOLD),
        "winners": total_households,
        "losers": 0.0,
        "winners_rate": 100.0,
        "losers_rate": 0.0,
        "residents": total_residents,
        "winners_residents": total_residents,
        "losers_residents": 0.0,
        "winners_rate_residents": 100.0,
        "losers_rate_residents": 0.0,
        "poverty_baseline_rate": poverty_baseline_rate,
        "poverty_reform_rate": poverty_reform_rate,
        "poverty_rate_change": poverty_rate_change,
        "poverty_percent_change": poverty_percent_change,
        "child_poverty_baseline_rate": child_poverty_baseline_rate,
        "child_poverty_reform_rate": child_poverty_reform_rate,
        "child_poverty_rate_change": child_poverty_rate_change,
        "child_poverty_percent_change": child_poverty_percent_change,
        "deep_poverty_baseline_rate": deep_poverty_baseline_rate,
        "deep_poverty_reform_rate": deep_poverty_reform_rate,
        "deep_poverty_rate_change": deep_poverty_rate_change,
        "deep_poverty_percent_change": deep_poverty_percent_change,
        "deep_child_poverty_baseline_rate": deep_child_poverty_baseline_rate,
        "deep_child_poverty_reform_rate": deep_child_poverty_reform_rate,
        "deep_child_poverty_rate_change": deep_child_poverty_rate_change,
        "deep_child_poverty_percent_change": deep_child_poverty_percent_change,
        "by_income_bracket": by_income_bracket,
    }


def _save_csvs(result: dict, output_dir: str) -> None:
    """Write the dashboard CSVs."""
    import pandas as pd

    year = result["year"]

    distributional_rows = []
    for d, avg in result["decile"]["average"].items():
        distributional_rows.append({
            "year": year,
            "decile": d,
            "average_change": round(avg, 2),
            "relative_change": round(result["decile"]["relative"][d], 6),
        })

    metrics_rows = []
    flat = [
        ("budgetary_impact", result["budget"]["budgetary_impact"]),
        ("federal_tax_revenue_impact", result["budget"]["federal_tax_revenue_impact"]),
        ("state_tax_revenue_impact", result["budget"]["state_tax_revenue_impact"]),
        ("tax_revenue_impact", result["budget"]["tax_revenue_impact"]),
        ("households", result["budget"]["households"]),
        ("total_cost", result["total_cost"]),
        ("beneficiaries", result["beneficiaries"]),
        ("avg_benefit", result["avg_benefit"]),
        ("winners", result["winners"]),
        ("losers", result["losers"]),
        ("winners_rate", result["winners_rate"]),
        ("losers_rate", result["losers_rate"]),
        ("residents", result["residents"]),
        ("winners_residents", result["winners_residents"]),
        ("losers_residents", result["losers_residents"]),
        ("winners_rate_residents", result["winners_rate_residents"]),
        ("losers_rate_residents", result["losers_rate_residents"]),
        ("poverty_baseline_rate", result["poverty_baseline_rate"]),
        ("poverty_reform_rate", result["poverty_reform_rate"]),
        ("poverty_rate_change", result["poverty_rate_change"]),
        ("poverty_percent_change", result["poverty_percent_change"]),
        ("child_poverty_baseline_rate", result["child_poverty_baseline_rate"]),
        ("child_poverty_reform_rate", result["child_poverty_reform_rate"]),
        ("child_poverty_rate_change", result["child_poverty_rate_change"]),
        ("child_poverty_percent_change", result["child_poverty_percent_change"]),
        ("deep_poverty_baseline_rate", result["deep_poverty_baseline_rate"]),
        ("deep_poverty_reform_rate", result["deep_poverty_reform_rate"]),
        ("deep_poverty_rate_change", result["deep_poverty_rate_change"]),
        ("deep_poverty_percent_change", result["deep_poverty_percent_change"]),
        ("deep_child_poverty_baseline_rate", result["deep_child_poverty_baseline_rate"]),
        ("deep_child_poverty_reform_rate", result["deep_child_poverty_reform_rate"]),
        ("deep_child_poverty_rate_change", result["deep_child_poverty_rate_change"]),
        ("deep_child_poverty_percent_change", result["deep_child_poverty_percent_change"]),
    ]
    for metric, value in flat:
        metrics_rows.append({"year": year, "metric": metric, "value": value})

    intra = result["intra_decile"]
    winners_losers_rows = [{
        "year": year,
        "decile": "All",
        "gain_more_5pct": intra["all"]["Gain more than 5%"],
        "gain_less_5pct": intra["all"]["Gain less than 5%"],
        "no_change": intra["all"]["No change"],
        "lose_less_5pct": intra["all"]["Lose less than 5%"],
        "lose_more_5pct": intra["all"]["Lose more than 5%"],
    }]
    for i in range(10):
        winners_losers_rows.append({
            "year": year,
            "decile": str(i + 1),
            "gain_more_5pct": intra["deciles"]["Gain more than 5%"][i],
            "gain_less_5pct": intra["deciles"]["Gain less than 5%"][i],
            "no_change": intra["deciles"]["No change"][i],
            "lose_less_5pct": intra["deciles"]["Lose less than 5%"][i],
            "lose_more_5pct": intra["deciles"]["Lose more than 5%"][i],
        })

    income_bracket_rows = []
    for b in result["by_income_bracket"]:
        income_bracket_rows.append({
            "year": year,
            "bracket": b["bracket"],
            "beneficiaries": b["beneficiaries"],
            "total_cost": b["total_cost"],
            "avg_benefit": b["avg_benefit"],
        })

    outputs = {
        "distributional_impact.csv": distributional_rows,
        "metrics.csv": metrics_rows,
        "winners_losers.csv": winners_losers_rows,
        "income_brackets.csv": income_bracket_rows,
    }
    for filename, rows in outputs.items():
        path = os.path.join(output_dir, filename)
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"Saved: {path}")


@app.local_entrypoint()
def main():
    """Run the TX state-level analysis on Modal."""
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running TX rebate pipeline on Modal (year {YEAR})...")
    print(f"Dataset: {TX_DATASET}")
    print(f"Output: {output_dir}")

    result = calculate_impacts.remote()
    _save_csvs(result, output_dir)

    print("\nDone.")
