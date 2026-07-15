"""Modal-based state-level data generation pipeline for the Texas
$1,500 rebate check dashboard ("Money in Your Pocket" proposal).

Model-native: the rebate is encoded in policyengine-us as the
``gov/contrib/states/tx/rebate`` contributed reform (PR #9037,
released in 1.771.0), so the pipeline runs a baseline (current law)
and a reform simulation with the ``tx_rebate`` reform applied, and
every figure is computed from the difference. The reform pays one
$1,500 check per household with no income limit (assumption — the
proposal does not specify eligibility; this reading matches the
stated ~$17 billion Economic Stabilization Fund draw), integrated
into household net income and SPM resources by the model itself.

Runs against the ECPS state file (``states/TX.h5``), the same dataset
family as the district pipeline, and writes CSVs to
``frontend/public/data/``.

Usage:
    modal run scripts/modal_pipeline.py
    # or, resilient to local client limits:
    modal deploy scripts/modal_pipeline.py
    python scripts/run_state_pipeline_detached.py
"""

import os

import modal


app = modal.App("tx-rebate-checks-pipeline")

# 1.771.2 ≥ 1.771.0, the first release containing the tx_rebate
# contributed reform (PolicyEngine/policyengine-us#9037).
POLICYENGINE_US_PIN = "policyengine-us==1.771.2"

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

YEAR = 2027
ESF_AVAILABLE = 17_000_000_000  # $27B fund minus $10B retained

TX_DATASET = "hf://policyengine/policyengine-us-data/states/TX.h5"


@app.function(
    image=image,
    memory=32768,
    timeout=3600,
    retries=1,
)
def calculate_impacts() -> dict:
    """Run baseline vs tx_rebate reform on the TX state file and return
    distributional / fiscal / poverty / bracket breakdowns."""
    import numpy as np
    from policyengine_us import Microsimulation
    from policyengine_us.reforms.states.tx.rebate.tx_rebate import tx_rebate

    print(f"Starting TX rebate calculation for {YEAR}...")

    sim_baseline = Microsimulation(dataset=TX_DATASET)
    sim_reform = Microsimulation(dataset=TX_DATASET, reform=tx_rebate)

    # ===== FISCAL IMPACT =====
    weight_arr = np.array(
        sim_baseline.calculate("household_weight", period=YEAR)
    )
    total_households = float(weight_arr.sum())

    baseline_net_income = np.array(
        sim_baseline.calculate(
            "household_net_income", period=YEAR, map_to="household"
        )
    )
    reform_net_income = np.array(
        sim_reform.calculate(
            "household_net_income", period=YEAR, map_to="household"
        )
    )
    change_arr = reform_net_income - baseline_net_income

    total_cost = float((change_arr * weight_arr).sum())
    budgetary_impact = -total_cost

    # Sanity 1: the model's rebate outlay must equal the net-income
    # change it produces (the reform has no interactions by design).
    rebate_total = float(sim_reform.calculate("tx_rebate", period=YEAR).sum())
    if abs(rebate_total - total_cost) > 0.001 * max(rebate_total, 1):
        raise RuntimeError(
            f"tx_rebate outlay ${rebate_total/1e9:.2f}B != net-income "
            f"change ${total_cost/1e9:.2f}B — unexpected interaction."
        )
    # Sanity 2: the universal per-household reading should land near
    # the press release's implied $17B fund draw.
    if not (12e9 < total_cost < 22e9):
        raise RuntimeError(
            f"Total cost ${total_cost/1e9:.1f}B is far from the ~$17B "
            "ESF draw the proposal implies — check the dataset/weights."
        )
    print(
        f"  {total_households:,.0f} households, total ${total_cost/1e9:.2f}B "
        f"(ESF available: ${ESF_AVAILABLE/1e9:.0f}B)"
    )

    winners = float(weight_arr[change_arr > 1].sum())
    losers = float(weight_arr[change_arr < -1].sum())
    beneficiary_mask = change_arr > 0
    beneficiaries = float(weight_arr[beneficiary_mask].sum())
    avg_benefit = (
        float(np.average(change_arr[beneficiary_mask],
                         weights=weight_arr[beneficiary_mask]))
        if beneficiaries > 0
        else 0.0
    )
    winners_rate = winners / total_households * 100 if total_households else 0.0
    losers_rate = losers / total_households * 100 if total_households else 0.0

    # Resident-based winners/losers: a resident counts as a winner when
    # their household's net income rises.
    person_weight = np.array(
        sim_baseline.calculate("person_weight", period=YEAR)
    )
    person_change = np.array(
        sim_reform.calculate(
            "household_net_income", period=YEAR, map_to="person"
        )
    ) - np.array(
        sim_baseline.calculate(
            "household_net_income", period=YEAR, map_to="person"
        )
    )
    total_residents = float(person_weight.sum())
    winners_residents = float(person_weight[person_change > 1].sum())
    losers_residents = float(person_weight[person_change < -1].sum())
    winners_rate_residents = (
        winners_residents / total_residents * 100 if total_residents else 0.0
    )
    losers_rate_residents = (
        losers_residents / total_residents * 100 if total_residents else 0.0
    )

    # ===== INCOME DECILE =====
    decile = np.array(
        sim_baseline.calculate(
            "household_income_decile", period=YEAR, map_to="household"
        )
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
        sim_baseline.calculate(
            "household_count_people", period=YEAR, map_to="household"
        )
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
    # Model-native: the reform carries the rebate into SPM resources,
    # so poverty comes straight from the in_poverty variables.
    age_arr = np.array(sim_baseline.calculate("age", period=YEAR))
    is_child = age_arr < 18
    pw_arr = person_weight

    def _rates(var):
        bl = np.array(
            sim_baseline.calculate(var, period=YEAR, map_to="person")
        ).astype(bool)
        rf = np.array(
            sim_reform.calculate(var, period=YEAR, map_to="person")
        ).astype(bool)
        overall = (
            float((bl * pw_arr).sum() / pw_arr.sum() * 100),
            float((rf * pw_arr).sum() / pw_arr.sum() * 100),
        )
        cw = pw_arr[is_child]
        child = (
            float((bl[is_child] * cw).sum() / cw.sum() * 100),
            float((rf[is_child] * cw).sum() / cw.sum() * 100),
        )
        return overall, child

    (pov_bl, pov_rf), (cpov_bl, cpov_rf) = _rates("in_poverty")
    (dpov_bl, dpov_rf), (dcpov_bl, dcpov_rf) = _rates("in_deep_poverty")

    def _pct(bl, rf):
        return (rf - bl) / bl * 100 if bl > 0 else 0.0

    print(
        f"  poverty {pov_bl:.2f}% -> {pov_rf:.2f}%"
        f"  child {cpov_bl:.2f}% -> {cpov_rf:.2f}%"
    )

    # ===== INCOME BRACKETS =====
    # Households grouped by AGI (Texas has no state income tax, so there
    # is no state taxable-income measure to key on).
    agi = np.array(
        sim_baseline.calculate(
            "adjusted_gross_income", period=YEAR, map_to="household"
        )
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
        mask = (agi > min_inc) & (agi <= max_inc) & beneficiary_mask
        n = float(weight_arr[mask].sum())
        by_income_bracket.append({
            "bracket": label,
            "beneficiaries": n,
            "total_cost": float((change_arr[mask] * weight_arr[mask]).sum()),
            "avg_benefit": (
                float(np.average(change_arr[mask], weights=weight_arr[mask]))
                if n > 0
                else 0.0
            ),
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
        "beneficiaries": beneficiaries,
        "avg_benefit": avg_benefit,
        "winners": winners,
        "losers": losers,
        "winners_rate": winners_rate,
        "losers_rate": losers_rate,
        "residents": total_residents,
        "winners_residents": winners_residents,
        "losers_residents": losers_residents,
        "winners_rate_residents": winners_rate_residents,
        "losers_rate_residents": losers_rate_residents,
        "poverty_baseline_rate": pov_bl,
        "poverty_reform_rate": pov_rf,
        "poverty_rate_change": pov_rf - pov_bl,
        "poverty_percent_change": _pct(pov_bl, pov_rf),
        "child_poverty_baseline_rate": cpov_bl,
        "child_poverty_reform_rate": cpov_rf,
        "child_poverty_rate_change": cpov_rf - cpov_bl,
        "child_poverty_percent_change": _pct(cpov_bl, cpov_rf),
        "deep_poverty_baseline_rate": dpov_bl,
        "deep_poverty_reform_rate": dpov_rf,
        "deep_poverty_rate_change": dpov_rf - dpov_bl,
        "deep_poverty_percent_change": _pct(dpov_bl, dpov_rf),
        "deep_child_poverty_baseline_rate": dcpov_bl,
        "deep_child_poverty_reform_rate": dcpov_rf,
        "deep_child_poverty_rate_change": dcpov_rf - dcpov_bl,
        "deep_child_poverty_percent_change": _pct(dcpov_bl, dcpov_rf),
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
