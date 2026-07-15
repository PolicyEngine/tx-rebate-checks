"""Modal-based congressional-district pipeline for the Texas $1,500
rebate check dashboard.

Calculates per-district impacts for Texas's 38 congressional districts
(TX-01..TX-38; state FIPS 48) and writes ``congressional_districts.csv``
to ``frontend/public/data/``.

Model-native: each district runs a baseline (current law) and a reform
simulation with the ``gov/contrib/states/tx/rebate`` contributed reform
(policyengine-us PR #9037) applied; every figure is computed from the
difference.

Dataset note: the district runs use the per-district calibrated files
(``policyengine-us-data/districts/TX-XX.h5``, ~9k households each),
the same enhanced-CPS family as the statewide pipeline. Each district
file is calibrated independently, so district figures may not exactly
aggregate to the statewide figures.

Usage:
    modal run scripts/modal_district_pipeline.py
"""

import os

import modal


app = modal.App("tx-rebate-checks-district-pipeline")

# Matches scripts/modal_pipeline.py (1.771.0 first contains tx_rebate).
POLICYENGINE_US_PIN = "policyengine-us==1.771.2"
YEAR = 2027

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

TX_STATE = "TX"
TX_STATE_FIPS = 48
TX_DISTRICTS = list(range(1, 39))  # Texas has 38 congressional districts.


def get_tx_districts() -> list[str]:
    return [f"{TX_STATE}-{d:02d}" for d in TX_DISTRICTS]


@app.function(
    image=image,
    memory=16384,
    timeout=1800,
    retries=2,
)
def calculate_district(district_id: str) -> dict:
    """Run baseline vs tx_rebate reform for a single district."""
    import numpy as np
    from policyengine_us import Microsimulation
    from policyengine_us.reforms.states.tx.rebate.tx_rebate import tx_rebate

    print(f"Calculating {district_id}...")
    dataset_url = f"hf://policyengine/policyengine-us-data/districts/{district_id}.h5"

    try:
        sim_baseline = Microsimulation(dataset=dataset_url)
        sim_reform = Microsimulation(dataset=dataset_url, reform=tx_rebate)

        # Sanity: the reform must actually pay the rebate here.
        rebate_total = float(
            sim_reform.calculate("tx_rebate", period=YEAR).sum()
        )
        if rebate_total <= 0:
            raise RuntimeError(
                f"tx_rebate paid nothing in {district_id} — is the "
                "pinned policyengine-us release missing the reform?"
            )

        household_weight = np.array(
            sim_baseline.calculate("household_weight", period=YEAR)
        )
        baseline_net = np.array(
            sim_baseline.calculate("household_net_income", period=YEAR)
        )
        reform_net = np.array(
            sim_reform.calculate("household_net_income", period=YEAR)
        )
        income_change = reform_net - baseline_net
        total_weight = household_weight.sum()

        if total_weight > 0:
            avg_change = float(
                (income_change * household_weight).sum() / total_weight
            )
            avg_baseline = (baseline_net * household_weight).sum() / total_weight
            rel_change = avg_change / avg_baseline if avg_baseline > 0 else 0.0
            winners_share = float(
                (household_weight * (income_change > 1)).sum() / total_weight
            )
            losers_share = float(
                (household_weight * (income_change < -1)).sum() / total_weight
            )
        else:
            avg_change = rel_change = winners_share = losers_share = 0.0

        # Resident-based winners/losers, matching the statewide pipeline.
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
        total_person_weight = person_weight.sum()
        if total_person_weight > 0:
            winners_share_residents = float(
                (person_weight * (person_change > 1)).sum()
                / total_person_weight
            )
            losers_share_residents = float(
                (person_weight * (person_change < -1)).sum()
                / total_person_weight
            )
        else:
            winners_share_residents = losers_share_residents = 0.0

        # Poverty: model-native — the reform carries the rebate into
        # SPM resources.
        spm_unit_weight = np.array(
            sim_baseline.calculate("spm_unit_weight", period=YEAR)
        )
        total_spm_weight = spm_unit_weight.sum()
        if total_spm_weight > 0:
            pov_bl = np.array(
                sim_baseline.calculate(
                    "spm_unit_is_in_spm_poverty", period=YEAR
                )
            )
            pov_rf = np.array(
                sim_reform.calculate(
                    "spm_unit_is_in_spm_poverty", period=YEAR
                )
            )
            bl_rate = (pov_bl * spm_unit_weight).sum() / total_spm_weight
            rf_rate = (pov_rf * spm_unit_weight).sum() / total_spm_weight
            poverty_pct_change = (
                (rf_rate - bl_rate) / bl_rate * 100 if bl_rate > 0 else 0.0
            )
            children = np.array(
                sim_baseline.calculate(
                    "spm_unit_count_children", period=YEAR
                )
            )
            child_w = spm_unit_weight * children
            total_child_w = child_w.sum()
            if total_child_w > 0:
                bl_child = (pov_bl * child_w).sum() / total_child_w
                rf_child = (pov_rf * child_w).sum() / total_child_w
                child_poverty_pct_change = (
                    (rf_child - bl_child) / bl_child * 100
                    if bl_child > 0
                    else 0.0
                )
            else:
                child_poverty_pct_change = 0.0
        else:
            poverty_pct_change = child_poverty_pct_change = 0.0

        result = {
            "district": district_id,
            "average_household_income_change": round(avg_change, 2),
            "relative_household_income_change": round(rel_change, 6),
            "winners_share": round(winners_share, 4),
            "losers_share": round(losers_share, 4),
            "winners_share_residents": round(winners_share_residents, 4),
            "losers_share_residents": round(losers_share_residents, 4),
            "poverty_pct_change": round(float(poverty_pct_change), 2),
            "child_poverty_pct_change": round(float(child_poverty_pct_change), 2),
            "state": TX_STATE,
            "year": YEAR,
        }
        print(
            f"  {district_id}: avg=${avg_change:.2f}  rel={rel_change:.4%}  "
            f"poverty={poverty_pct_change:+.1f}%  "
            f"child poverty={child_poverty_pct_change:+.1f}%"
        )
        return result
    except Exception as e:
        print(f"  ERROR {district_id}: {e}")
        return None


@app.local_entrypoint()
def main():
    import pandas as pd

    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend",
        "public",
        "data",
    )
    os.makedirs(output_dir, exist_ok=True)

    districts = get_tx_districts()
    print(f"Running TX districts {districts[0]}..{districts[-1]} on Modal (year {YEAR})...")

    results = list(calculate_district.map(districts))
    rows = [r for r in results if r is not None]
    failed = len(results) - len(rows)
    if failed:
        raise SystemExit(f"ERROR: {failed} district(s) failed; not writing CSV")

    df = pd.DataFrame(rows)
    df = df.sort_values(["state", "district"]).reset_index(drop=True)
    path = os.path.join(output_dir, "congressional_districts.csv")
    df.to_csv(path, index=False)
    print(f"Saved: {path}")
