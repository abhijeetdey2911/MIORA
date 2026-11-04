import type { ReactElement } from 'react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ActivityPoint } from '../../types/dashboard';

interface ActivityChartProps {
  data: ActivityPoint[];
}

const Y_TICKS = [0, 10, 20, 30, 40];

const AXIS_TICK = { fill: 'var(--subtle)', fontSize: 12 };

/** Highlights only the most recent data point. */
function renderDot(lastIndex: number) {
  return function Dot({
    cx,
    cy,
    index,
  }: {
    cx?: number;
    cy?: number;
    index?: number;
  }): ReactElement {
    if (index !== lastIndex || cx === undefined || cy === undefined) {
      return <g key={`dot-${index}`} />;
    }
    return (
      <circle
        key={`dot-${index}`}
        cx={cx}
        cy={cy}
        r={4.5}
        fill="var(--accent)"
        stroke="var(--surface)"
        strokeWidth={2}
      />
    );
  };
}

export function ActivityChart({ data }: ActivityChartProps) {
  return (
    <section
      aria-labelledby="activity-heading"
      className="h-full rounded-2xl border border-line bg-surface p-5 shadow-card"
    >
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="activity-heading" className="text-sm font-semibold text-ink">
          Applications Over Time
        </h2>
        <span className="text-xs text-subtle">Last 7 days</span>
      </div>

      <div className="mt-4 h-56 sm:h-60">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={AXIS_TICK}
              tickMargin={10}
              padding={{ left: 8, right: 8 }}
            />
            <YAxis
              ticks={Y_TICKS}
              domain={[0, 45]}
              tickLine={false}
              axisLine={false}
              tick={AXIS_TICK}
              width={32}
            />
            <Tooltip
              cursor={{ stroke: 'var(--line)', strokeWidth: 1 }}
              contentStyle={{
                background: 'var(--surface)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                boxShadow: 'var(--card-shadow)',
                fontSize: 12,
              }}
              labelStyle={{ color: 'var(--muted)', marginBottom: 2 }}
              itemStyle={{ color: 'var(--ink)', padding: 0 }}
              formatter={(value) => [String(value), 'Applications']}
            />
            <Area
              type="monotone"
              dataKey="applications"
              stroke="var(--accent)"
              strokeWidth={2.5}
              fill="url(#activity-fill)"
              dot={renderDot(data.length - 1)}
              activeDot={{ r: 5, fill: 'var(--accent)', stroke: 'var(--surface)', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
