import { ArrowUpRight } from 'lucide-react';
import type { StatItem, StatTone } from '../../types/dashboard';

const TONE_STYLES: Record<StatTone, string> = {
  orange: 'bg-accent-soft text-accent-ink',
  amber: 'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300',
  violet: 'bg-violet-500/10 text-violet-600 dark:bg-violet-400/15 dark:text-violet-300',
  blue: 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300',
  green: 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300',
};

interface StatCardProps {
  stat: StatItem;
}

export function StatCard({ stat }: StatCardProps) {
  const { icon: Icon, label, value, change, tone } = stat;
  const toneClass = TONE_STYLES[tone];

  return (
    <div className="flex h-full min-h-[78px] min-w-0 items-center gap-2.5 rounded-2xl border border-line bg-surface px-3.5 py-3 shadow-card transition-colors hover:border-subtle/40">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${toneClass}`}
      >
        <Icon className="h-4 w-4" strokeWidth={1.9} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-center">
        <div className="flex items-center justify-between gap-1.5">
          <p className="text-lg font-semibold leading-none tracking-tight text-ink sm:text-[20px]">
            {value.toLocaleString()}
          </p>

          <span
            className={`inline-flex shrink-0 items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[10px] font-semibold leading-none ${toneClass}`}
            title="Change vs. previous period (sample data)"
          >
            <ArrowUpRight className="h-2.5 w-2.5" strokeWidth={2.5} />
            {change > 0 ? '+' : ''}
            {change}%
          </span>
        </div>

        <p className="mt-1.5 text-[11px] font-medium leading-tight text-muted">
          {label}
        </p>
      </div>
    </div>
  );
}
