'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useHouseholdImpact } from '@/hooks/useHouseholdImpact';
import { REBATE_PER_HOUSEHOLD } from '@/lib/rebate';
import type { HouseholdRequest } from '@/lib/types';
import ChartWatermark from './ChartWatermark';

interface Props {
  request: HouseholdRequest | null;
  triggered: boolean;
  maxEarnings?: number;
}

const formatCurrency = (value: number) =>
  `$${Math.round(value).toLocaleString('en-US')}`;
const formatIncome = (value: number) => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${(value / 1000).toFixed(0)}k`;
};

// Tooltip showing the rebate's share of income at the hovered point.
const HoverTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: { income: number; share: number } }>;
  label?: number;
}) => {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  const incomeLabel = typeof label === 'number' ? label : p.income;
  return (
    <div
      style={{
        background: 'var(--chart-tooltip-bg)',
        border: '1px solid var(--chart-tooltip-border)',
        borderRadius: 4,
        padding: '8px 12px',
        fontFamily: 'var(--font-sans)',
        fontSize: 12,
      }}
    >
      <p style={{ margin: '0 0 4px', fontWeight: 600 }}>
        Income: {formatCurrency(incomeLabel)}
      </p>
      <p style={{ margin: 0 }}>
        Rebate: +{formatCurrency(REBATE_PER_HOUSEHOLD)} (
        {p.share.toFixed(1)}% of income)
      </p>
    </div>
  );
};

export default function ImpactAnalysis({
  request,
  triggered,
  maxEarnings,
}: Props) {
  const liveQuery = useHouseholdImpact(request, triggered);
  const data = liveQuery.data;

  if (!triggered || !data || !request) return null;

  const xMax = maxEarnings ?? data.x_axis_max;
  const share =
    request.income > 0
      ? (REBATE_PER_HOUSEHOLD / request.income) * 100
      : null;

  const chartData = data.income_range
    .filter((inc) => inc > 0 && inc <= xMax)
    .map((inc) => ({
      income: inc,
      share: (REBATE_PER_HOUSEHOLD / inc) * 100,
    }));

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-primary">Impact analysis</h2>

      {/* Personal impact */}
      <div>
        <h3 className="text-xl font-bold text-gray-800 mb-4">
          Your household&apos;s rebate ({request.year})
        </h3>
        <p className="text-gray-600 mb-4">
          Under the proposal, every Texas household receives the same
          $1,500 check, so the rebate matters most relative to what your
          household earns.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg p-6 border bg-green-50 border-success">
            <p className="text-sm text-gray-700 mb-2">Rebate check</p>
            <p className="text-3xl font-bold text-green-600">
              +{formatCurrency(REBATE_PER_HOUSEHOLD)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              One check per household, regardless of income
            </p>
          </div>
          <div className="rounded-lg p-6 border bg-gray-50 border-gray-300">
            <p className="text-sm text-gray-700 mb-2">
              Share of your employment income
            </p>
            <p className="text-3xl font-bold text-gray-700">
              {share === null ? '—' : `${share.toFixed(1)}%`}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {share === null
                ? 'Enter an income above to see the rebate as a share of it'
                : `$1,500 on ${formatCurrency(request.income)} of earnings`}
            </p>
          </div>
        </div>
      </div>

      <hr className="border-gray-200" />

      {/* Chart */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1 text-gray-800">
          The rebate as a share of income
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          A flat $1,500 check is worth proportionally more to
          lower-income households
        </p>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={chartData}
            margin={{ left: 20, right: 20, top: 5, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
            <XAxis
              dataKey="income"
              type="number"
              tickFormatter={formatIncome}
              stroke="var(--chart-reference)"
              domain={[0, xMax]}
              allowDataOverflow={false}
            />
            <YAxis
              tickFormatter={(v: number) => `${v.toFixed(0)}%`}
              stroke="var(--chart-reference)"
              width={60}
              domain={[0, 20]}
              allowDataOverflow
            />
            <Tooltip content={<HoverTooltip />} />
            <ReferenceLine y={0} stroke="var(--chart-reference)" strokeWidth={2} />
            {request.income > 0 && (
              <ReferenceLine
                x={request.income}
                stroke="var(--chart-axis)"
                strokeDasharray="4 4"
                label={{ value: 'Your income', fontSize: 12 }}
              />
            )}
            <Line
              type="monotone"
              dataKey="share"
              stroke="var(--chart-positive)"
              strokeWidth={3}
              name="Rebate as % of income"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
        <ChartWatermark />
      </div>
    </div>
  );
}
