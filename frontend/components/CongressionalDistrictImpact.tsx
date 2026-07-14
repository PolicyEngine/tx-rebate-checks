'use client';

import { useState, useEffect } from 'react';
import TXDistrictMap, { TXDistrictData } from './DynamicDistrictMap';
import ChartWatermark from './ChartWatermark';

interface Props {
  year?: number;
}

// Texas representatives (119th Congress; TX-23 vacant as of July 2026).
const TX_REPRESENTATIVES: Record<string, { name: string; party?: 'R' | 'D' }> = {
  '1': { name: 'Nathaniel Moran', party: 'R' },
  '2': { name: 'Dan Crenshaw', party: 'R' },
  '3': { name: 'Keith Self', party: 'R' },
  '4': { name: 'Pat Fallon', party: 'R' },
  '5': { name: 'Lance Gooden', party: 'R' },
  '6': { name: 'Jake Ellzey', party: 'R' },
  '7': { name: 'Lizzie Fletcher', party: 'D' },
  '8': { name: 'Morgan Luttrell', party: 'R' },
  '9': { name: 'Al Green', party: 'D' },
  '10': { name: 'Michael McCaul', party: 'R' },
  '11': { name: 'August Pfluger', party: 'R' },
  '12': { name: 'Craig Goldman', party: 'R' },
  '13': { name: 'Ronny Jackson', party: 'R' },
  '14': { name: 'Randy Weber', party: 'R' },
  '15': { name: 'Monica De La Cruz', party: 'R' },
  '16': { name: 'Veronica Escobar', party: 'D' },
  '17': { name: 'Pete Sessions', party: 'R' },
  '18': { name: 'Christian Menefee', party: 'D' },
  '19': { name: 'Jodey Arrington', party: 'R' },
  '20': { name: 'Joaquin Castro', party: 'D' },
  '21': { name: 'Chip Roy', party: 'R' },
  '22': { name: 'Troy Nehls', party: 'R' },
  '23': { name: 'Vacant' },
  '24': { name: 'Beth Van Duyne', party: 'R' },
  '25': { name: 'Roger Williams', party: 'R' },
  '26': { name: 'Brandon Gill', party: 'R' },
  '27': { name: 'Michael Cloud', party: 'R' },
  '28': { name: 'Henry Cuellar', party: 'D' },
  '29': { name: 'Sylvia Garcia', party: 'D' },
  '30': { name: 'Jasmine Crockett', party: 'D' },
  '31': { name: 'John Carter', party: 'R' },
  '32': { name: 'Julie Johnson', party: 'D' },
  '33': { name: 'Marc Veasey', party: 'D' },
  '34': { name: 'Vicente Gonzalez', party: 'D' },
  '35': { name: 'Greg Casar', party: 'D' },
  '36': { name: 'Brian Babin', party: 'R' },
  '37': { name: 'Lloyd Doggett', party: 'D' },
  '38': { name: 'Wesley Hunt', party: 'R' },
};

function partyColor(party: 'R' | 'D' | undefined) {
  if (party === 'R') return 'var(--party-r)';
  if (party === 'D') return 'var(--party-d)';
  return 'var(--party-none)';
}

export default function CongressionalDistrictImpact({ year = 2027 }: Props) {
  const [data, setData] = useState<TXDistrictData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);

  useEffect(() => {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH !== undefined
      ? process.env.NEXT_PUBLIC_BASE_PATH
      : '/us/tx-rebate-checks';

    // Initial state already covers loading/error; setting them
    // synchronously here trips react-hooks' cascading-render lint and
    // is only needed if `year` ever changes mid-session (it does not).
    let cancelled = false;

    fetch(`${basePath}/data/congressional_districts.csv`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load district data');
        return res.text();
      })
      .then((text) => {
        const lines = text.trim().split(/\r?\n/);
        const headers = lines[0].split(',').map((h) => h.trim());
        const rows = lines.slice(1).map((line) => {
          const values = line.split(',').map((v) => v.trim());
          const row: Record<string, string | number> = {};
          headers.forEach((h, i) => {
            const val = values[i];
            // Blank cells become undefined (not 0) so downstream
            // nullish fallbacks work.
            if (val === undefined || val === '') return;
            row[h] = isNaN(Number(val)) ? val : Number(val);
          });
          return row as unknown as TXDistrictData & { state: string; year: number };
        });
        const txRows = rows
          .filter((r) => r.state === 'TX' && r.year === year)
          .map((r) => {
            const districtNum = String(r.district).split('-')[1] || '';
            const districtId = districtNum.replace(/^0+/, '') || districtNum;
            const rep = TX_REPRESENTATIVES[districtId];
            return {
              ...r,
              district_number: districtId,
              representative: rep?.name || '',
              party: rep?.party,
              region: '',
            } as TXDistrictData;
          })
          .sort((a, b) =>
            Number(a.district_number) - Number(b.district_number)
          );
        if (cancelled) return;
        setData(txRows);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [year]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent"></div>
          <p className="mt-4 text-gray-600">Loading Texas district data...</p>
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h2 className="text-yellow-800 font-semibold mb-2">
          Texas district data not yet available
        </h2>
        <p className="text-yellow-700">
          {error || 'TX district-level impact data has not been generated yet.'}
        </p>
        <p className="text-yellow-700 mt-2">
          Run: <code className="bg-yellow-100 px-2 py-1 rounded">modal run scripts/modal_district_pipeline.py</code>
        </p>
      </div>
    );
  }

  const selectedData = selectedDistrict
    ? data.find((d) => d.district_number === selectedDistrict) || null
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          Texas congressional district impacts ({year})
        </h3>
        <p className="text-gray-600">
          Average household impact by congressional district under the{' '}
          <strong>proposed $1,500 rebate check</strong> vs. current law.
          Hover over a district for details and click to pin.
        </p>
      </div>

      {/* Map */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <TXDistrictMap
          data={data}
          selectedDistrict={selectedDistrict}
          onSelect={(districtNum) =>
            setSelectedDistrict((prev) =>
              prev === districtNum ? null : districtNum
            )
          }
        />
        <ChartWatermark />
      </div>

      {/* Detail card below map */}
      {selectedData ? (
        <DistrictDetailCard
          district={selectedData}
          onClose={() => setSelectedDistrict(null)}
        />
      ) : (
        <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg p-6 text-center">
          <p className="text-gray-500 text-sm">
            Click a district on the map to see detailed impact analysis.
          </p>
        </div>
      )}

      {/* All districts table */}
      <div>
        <h4 className="text-lg font-semibold text-gray-900 mb-3">
          All Texas districts
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">District</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Representative</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-900">Winners</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-900">Average change</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-900">Child poverty change</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr
                  key={d.district_number}
                  className={`border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${
                    selectedDistrict === d.district_number ? 'bg-primary-50' : ''
                  }`}
                  onClick={() =>
                    setSelectedDistrict((prev) =>
                      prev === d.district_number ? null : d.district_number
                    )
                  }
                >
                  <td className="py-3 px-4 text-gray-700 font-medium">
                    TX-{String(d.district_number).padStart(2, '0')}
                    <span className="block text-xs text-gray-500 font-normal">{d.region}</span>
                  </td>
                  <td className="py-3 px-4" style={{ color: partyColor(d.party) }}>
                    {d.representative}
                    {d.party ? <span className="ml-1 text-xs">({d.party})</span> : null}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-700">
                    {(d.winners_share_residents ?? d.winners_share) !== undefined
                      ? `${((d.winners_share_residents ?? d.winners_share)! * 100).toFixed(1)}%`
                      : '—'}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-700">
                    {d.average_household_income_change >= 0 ? '+' : ''}
                    ${d.average_household_income_change.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-700">
                    {d.child_poverty_pct_change !== undefined
                      ? `${d.child_poverty_pct_change > 0 ? '+' : ''}${d.child_poverty_pct_change.toFixed(2)}%`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology note */}
      <p className="text-xs text-gray-500">
        Winners are residents whose household&apos;s net income rises,
        matching the statewide tab. District estimates use
        PolicyEngine&apos;s district-calibrated datasets (~9,000 households
        per district), from the same enhanced CPS family as the statewide
        estimates. District figures may not exactly aggregate to statewide
        figures because each district file is calibrated independently.
      </p>
    </div>
  );
}

function DistrictDetailCard({
  district,
  onClose,
}: {
  district: TXDistrictData;
  onClose: () => void;
}) {
  const avgChange = district.average_household_income_change;
  const isPositive = avgChange > 0;
  const isNegative = avgChange < 0;
  // Use one population basis for the whole card — residents when both
  // resident shares are present, otherwise households — so the residual
  // "no change" share never mixes denominators.
  const hasResidentShares =
    district.winners_share_residents !== undefined &&
    district.losers_share_residents !== undefined;
  const winnersShare = hasResidentShares
    ? district.winners_share_residents!
    : district.winners_share ?? 0;
  const losersShare = hasResidentShares
    ? district.losers_share_residents!
    : district.losers_share ?? 0;
  const basisLabel = hasResidentShares ? 'residents' : 'households';
  // "No change" is the residual after winners + losers.
  const noChangeShare = Math.max(0, 1 - winnersShare - losersShare);
  const childPovChange = district.child_poverty_pct_change ?? 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-4 pb-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex items-center justify-center w-10 h-10 rounded-lg text-white font-bold text-lg"
            style={{
              backgroundColor: isPositive
                ? 'var(--chart-1)'
                : isNegative
                  ? 'var(--destructive)'
                  : 'var(--muted-foreground)',
            }}
          >
            {district.district_number}
          </span>
          <div>
            <h4 className="text-lg font-semibold text-gray-900">
              Texas District {district.district_number}
            </h4>
            <p className="text-sm text-gray-500">
              <span style={{ color: partyColor(district.party) }}>
                {district.representative}
                {district.party ? ` (${district.party})` : ''}
              </span>
              {district.region ? ` — ${district.region}` : ''}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 p-1"
          title="Close"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Average household impact
          </p>
          <p
            className={`text-xl font-bold ${
              isPositive ? 'text-primary-700' : isNegative ? 'text-red-700' : 'text-gray-700'
            }`}
          >
            {isPositive ? '+' : ''}
            ${avgChange.toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {(district.relative_household_income_change * 100).toFixed(2)}% of income
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Winners</p>
          <p className="text-xl font-bold text-primary-600">
            {(winnersShare * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">of {basisLabel} gain</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Child poverty change</p>
          <p
            className={`text-xl font-bold ${
              childPovChange < 0 ? 'text-primary-700' : childPovChange > 0 ? 'text-red-700' : 'text-gray-700'
            }`}
          >
            {childPovChange > 0 ? '+' : ''}
            {childPovChange.toFixed(2)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">vs. current law</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">No change</p>
          <p className="text-xl font-bold text-gray-600">
            {(noChangeShare * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">of {basisLabel}</p>
        </div>
      </div>
    </div>
  );
}
