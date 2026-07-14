"""Texas $1,500 rebate check calculation module.

Models Gina Hinojosa's "Money in Your Pocket" proposal: $1,500 refund
checks to Texas families, funded by drawing down the state's Economic
Stabilization Fund (leaving $10 billion of the ~$27 billion balance).

The press release does not specify eligibility, so this dashboard
assumes one $1,500 check per household with no income limit — the
reading most consistent with the stated fund math (~$17 billion
available covers Texas's ~11-12 million households at $1,500 each).

Because the rebate is a flat, universal transfer, impacts are computed
arithmetically on top of a single current-law simulation: every
household's net income rises by exactly $1,500, and poverty impacts
come from adding each household's rebate to its members' SPM unit
resources.
"""

from .rebate import (
    DASHBOARD_YEAR,
    ESF_BALANCE,
    ESF_RETAINED,
    REBATE_PER_HOUSEHOLD,
)

__all__ = [
    "DASHBOARD_YEAR",
    "ESF_BALANCE",
    "ESF_RETAINED",
    "REBATE_PER_HOUSEHOLD",
]

__version__ = "1.0.0"
