'use client';

import { useEffect, useCallback, useState } from 'react';
import ImpactAnalysis from '@/components/ImpactAnalysis';
import AggregateImpact from '@/components/AggregateImpact';
import PolicyOverview from '@/components/PolicyOverview';
import CongressionalDistrictImpact from '@/components/CongressionalDistrictImpact';
import { DASHBOARD_YEAR } from '@/lib/rebate';
import type { HouseholdRequest } from '@/lib/types';
import { parseHashParams } from '@/lib/embedding';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'policy' | 'impact' | 'aggregate' | 'districts'>('policy');

  const TAB_CONFIG = [
    { id: 'policy' as const, label: 'Policy overview' },
    { id: 'impact' as const, label: 'Household impact' },
    { id: 'aggregate' as const, label: 'Statewide impact' },
    { id: 'districts' as const, label: 'Congressional districts' },
  ];

  const handleTabChange = useCallback((tab: 'policy' | 'impact' | 'aggregate' | 'districts') => {
    setActiveTab(tab);
  }, []);

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-primary-500 text-white py-8 px-4 shadow-md">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-4xl font-bold mb-2">
            Texas $1,500 rebate check calculator
          </h1>
          <p className="text-lg opacity-90">
            See the impact of the proposed $1,500 rebate checks for Texas
            households — part of gubernatorial nominee Gina Hinojosa&apos;s
            &ldquo;Money in Your Pocket&rdquo; agenda — statewide and by
            congressional district
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex space-x-1 mb-4" role="tablist">
          {TAB_CONFIG.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              onClick={() => handleTabChange(tab.id)}
              className={`px-6 py-3 rounded-t-lg font-semibold transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-primary-600 border-t-4 border-primary-500'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          className="bg-white rounded-lg shadow-md p-6"
        >
          {activeTab === 'policy' ? (
            <PolicyOverview />
          ) : activeTab === 'impact' ? (
            <HouseholdImpactTab />
          ) : activeTab === 'aggregate' ? (
            <StatewideImpactTab />
          ) : (
            <CongressionalDistrictImpact />
          )}
        </div>
      </div>
    </main>
  );
}

/** Household impact tab.
 *
 * The rebate is a flat $1,500 per household, so the only input that
 * changes anything is income — it determines what the check is worth
 * relative to what the household earns. */
function HouseholdImpactTab() {
  const getInitialIncome = () => {
    if (typeof window === 'undefined') return 50000;
    const params = parseHashParams(window.location.hash);
    return params.income ?? 50000;
  };

  const [income, setIncome] = useState(getInitialIncome);
  const [maxEarnings, setMaxEarnings] = useState(100000);
  const [triggered, setTriggered] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState<HouseholdRequest | null>(null);

  useEffect(() => {
    const handleHashChange = () => {
      const params = parseHashParams(window.location.hash);
      if (params.income !== undefined) setIncome(params.income);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const formatNumber = (num: number) => num.toLocaleString('en-US');
  const parseNumber = (str: string) => {
    const num = Number(str.replace(/,/g, ''));
    return isNaN(num) ? 0 : num;
  };

  const handleCalculate = () => {
    setSubmittedRequest({
      age_head: 35,
      age_spouse: null,
      dependent_ages: [],
      income,
      year: DASHBOARD_YEAR,
      max_earnings: maxEarnings,
      state_code: 'TX',
    });
    setTriggered(true);
  };

  return (
    <div className="space-y-6">
      {/* Inline household config */}
      <section className="bg-gray-50 rounded-xl p-6 md:p-8 border border-gray-200 shadow-sm">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Your household</h2>
        <p className="text-sm text-gray-600 mb-6">
          Every Texas household would receive the same $1,500 check under
          the proposal, whatever its size, composition, or income. Enter
          your household&apos;s employment income to see what the check is
          worth relative to your earnings.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1.5">
              Employment income
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
              <input
                type="text"
                value={formatNumber(income)}
                onChange={(e) => setIncome(parseNumber(e.target.value))}
                className="w-full pl-6 pr-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              />
            </div>
          </div>
        </div>

        {/* Calculate button */}
        <div className="mt-8">
          <button
            onClick={handleCalculate}
            className="py-3 px-10 rounded-lg font-semibold text-white bg-primary-500 hover:bg-primary-600 active:bg-primary-700 transition-all shadow-sm hover:shadow-md sm:w-auto w-full"
          >
            Calculate impact
          </button>
        </div>
      </section>

      {/* Chart x-axis options */}
      {triggered && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
          <span>Chart x-axis max:</span>
          {[100000, 200000, 500000, 1000000].map((v) => (
            <button
              key={v}
              onClick={() => {
                setMaxEarnings(v);
                setSubmittedRequest(prev => prev ? { ...prev, max_earnings: v } : null);
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                maxEarnings === v
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              ${v >= 1000000 ? `${v / 1000000}M` : `${v / 1000}k`}
            </button>
          ))}
        </div>
      )}

      {/* Impact results */}
      {submittedRequest && (
        <ImpactAnalysis
          request={submittedRequest}
          triggered={triggered}
          maxEarnings={maxEarnings}
        />
      )}
    </div>
  );
}

/** Statewide impact tab */
function StatewideImpactTab() {
  return (
    <div className="space-y-6">
      <AggregateImpact triggered={true} />
    </div>
  );
}
