"""Constants for the Texas $1,500 rebate check proposal.

Source: Hinojosa campaign press release, "RECAP: Gina Hinojosa Launches
'Money in Your Pocket' Economic Agenda" (July 13, 2026): $1,500 refund
checks funded from the ~$27 billion Economic Stabilization Fund,
leaving $10 billion in the fund.

Eligibility assumption (the proposal does not specify): one check per
household, no income limit. At Texas's ~11-12 million households this
costs ~$17-18 billion, matching the stated fund draw
(ESF_BALANCE - ESF_RETAINED = $17 billion).
"""

# One check per household, no income limit (assumption — see module
# docstring).
REBATE_PER_HOUSEHOLD = 1_500

# First tax year the proposal could plausibly take effect (the winner
# of the 2026 gubernatorial race takes office in January 2027).
DASHBOARD_YEAR = 2027

# Economic Stabilization Fund framing from the press release.
ESF_BALANCE = 27_000_000_000
ESF_RETAINED = 10_000_000_000
