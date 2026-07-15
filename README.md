# Texas $1,500 rebate check dashboard

Models the $1,500 refund checks proposed in Texas gubernatorial
nominee Gina Hinojosa's "Money in Your Pocket" economic agenda
(July 2026): direct checks to Texas families funded by drawing the
~$27 billion Economic Stabilization Fund down to a $10 billion
reserve. Reports household, statewide, and congressional district
impacts for tax year 2027. PolicyEngine is a nonpartisan nonprofit
and does not endorse candidates or proposals.

## Eligibility assumption

The proposal does not specify who receives a check. This dashboard
assumes **one $1,500 check per household with no income limit** — the
reading most consistent with the campaign's own arithmetic: the ~$17
billion fund draw covers Texas's ~11-12 million households at $1,500
each.

The rebate is encoded in policyengine-us as the
`gov/contrib/states/tx/rebate` contributed reform
([PR #9037](https://github.com/PolicyEngine/policyengine-us/pull/9037),
released in 1.771.0): the pipelines run baseline vs reform simulations
and compute every figure from the difference, with the model carrying
the rebate into household net income and SPM resources. The household
tab computes entirely client-side — no backend (the reform is a flat
transfer, so the household impact is a constant +$1,500).

- **Frontend**: `frontend/` (Next.js / Tailwind)
- **Modal pipelines**:
  - `scripts/modal_pipeline.py` — statewide impacts on the ECPS state
    file (`policyengine-us-data/states/TX.h5`)
  - `scripts/modal_district_pipeline.py` — per-district impacts on the
    district-calibrated files
    (`policyengine-us-data/districts/TX-01..TX-38.h5`)
- **Pre-computed CSVs**: `frontend/public/data/*.csv`

## Dataset note

Both levels run on the enhanced-CPS dataset family. ECPS overstates
baseline poverty *levels*, so the dashboard emphasizes poverty
*changes*. District files are calibrated independently, so district
figures may not exactly aggregate to statewide figures.

## Refreshing data

policyengine-us is pinned in the Modal images (`POLICYENGINE_US_PIN`)
and `pyproject.toml`. To refresh:

1. `modal run scripts/modal_pipeline.py`
2. `modal run scripts/modal_district_pipeline.py`

Live: <https://tx-rebate-checks.vercel.app/us/tx-rebate-checks>
