/**
 * Household impact for the Texas $1,500 rebate check.
 *
 * The proposal is a flat, universal transfer — one $1,500 check per
 * household with no income limit or phase-out (see the policy overview
 * for the eligibility assumption) — so the household impact needs no
 * simulation or backend at all: every household's net income rises by
 * exactly $1,500, regardless of earnings. This module generates the
 * response shape the chart components expect, entirely client-side.
 */

import { REBATE_PER_HOUSEHOLD } from "./rebate";
import {
  HouseholdRequest,
  HouseholdImpactResponse,
} from "./types";

const CHART_POINTS = 201;

export const api = {
  async calculateHouseholdImpact(
    request: HouseholdRequest,
  ): Promise<HouseholdImpactResponse> {
    const xMax = Math.max(request.max_earnings, request.income);
    const income_range = Array.from(
      { length: CHART_POINTS },
      (_, i) => (i * xMax) / (CHART_POINTS - 1),
    );
    const flat = income_range.map(() => REBATE_PER_HOUSEHOLD);
    const zeros = income_range.map(() => 0);

    return {
      income_range,
      net_income_change: flat,
      federalTaxChange: zeros,
      stateTaxChange: zeros,
      netIncomeChange: flat,
      benefit_at_income: {
        baseline: 0,
        reform: REBATE_PER_HOUSEHOLD,
        difference: REBATE_PER_HOUSEHOLD,
        federal_tax_change: 0,
        state_tax_change: 0,
        net_income_change: REBATE_PER_HOUSEHOLD,
      },
      x_axis_max: request.max_earnings,
    };
  },
};
