/**
 * Constants for the Texas $1,500 rebate check proposal ("Money in Your
 * Pocket"). Mirrors tx_rebate_calc/rebate.py.
 */

// One check per household, no income limit (assumption — the proposal
// does not specify eligibility; this reading matches the stated
// Economic Stabilization Fund draw).
export const REBATE_PER_HOUSEHOLD = 1_500;

// First tax year the proposal could plausibly take effect.
export const DASHBOARD_YEAR = 2027;

// Economic Stabilization Fund framing from the press release.
export const ESF_BALANCE = 27_000_000_000;
export const ESF_RETAINED = 10_000_000_000;
