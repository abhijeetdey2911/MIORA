import { ArrowRight, Bell, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { NotificationItem } from '../../types/multiAgent';

interface RecentUpdatesProps {
  updates: readonly NotificationItem[];
}

function getBadgeStyle(statusBadge: string | null): {
  badge: string;
  dot: string;
} {
  const s = (statusBadge || 'Update').toLowerCase();
  if (s.includes('interview') || s.includes('offer') || s.includes('completed')) {
    return {
      badge:
        'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300',
      dot: 'bg-emerald-500',
    };
  }
  if (s.includes('submitted') || s.includes('running')) {
    return {
      badge: 'bg-sky-500/10 text-sky-600 dark:bg-sky-400/15 dark:text-sky-300',
      dot: 'bg-sky-500',
    };
  }
  if (s.includes('unconfirmed') || s.includes('paused')) {
    return {
      badge:
        'bg-amber-500/10 text-amber-600 dark:bg-amber-400/15 dark:text-amber-300',
      dot: 'bg-amber-500',
    };
  }
  if (s.includes('rejected') || s.includes('failed') || s.includes('error')) {
    return {
      badge:
        'bg-rose-500/10 text-rose-600 dark:bg-rose-400/15 dark:text-rose-300',
      dot: 'bg-rose-500',
    };
  }
  return {
    badge: 'bg-accent-soft text-accent-ink',
    dot: 'bg-accent',
  };
}

export function RecentUpdates({ updates }: RecentUpdatesProps) {
  return (
    <section
      aria-labelledby="recent-updates-heading"
      className="rounded-2xl border border-line bg-surface p-5 shadow-card"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2
            id="recent-updates-heading"
            className="text-sm font-semibold text-ink"
          >
            Recent Updates
          </h2>
          <p className="mt-0.5 text-xs text-subtle">
            Live status changes and multi-agent notifications from PostgreSQL
          </p>
        </div>

        <Link
          to="/updates"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-subtle/40 hover:text-accent-ink"
        >
          View All
          <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
        </Link>
      </div>

      {updates.length === 0 ? (
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-dashed border-line bg-surface-2 px-4 py-5 text-xs text-muted">
          <Bell className="h-4 w-4 shrink-0 text-subtle" />
          <span>
            No application updates or workflow notifications recorded yet.
            Updates will appear here automatically as JobHunter runs.
          </span>
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-line">
          {updates.slice(0, 5).map((item) => {
            const style = getBadgeStyle(item.status_badge);
            const initial = (item.company || item.title || 'J')
              .charAt(0)
              .toUpperCase();
            return (
              <li
                key={item.id}
                className="flex flex-col gap-3 py-3.5 first:pt-1 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <div
                    aria-hidden="true"
                    className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-line bg-surface-2 text-xs font-semibold text-ink"
                  >
                    {initial}
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                      <p className="text-sm font-semibold text-ink">
                        {item.job_title || item.title}
                      </p>
                      {item.company && (
                        <span className="text-xs font-medium text-muted">
                          · {item.company}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-muted">{item.message}</p>
                  </div>
                </div>

                <div className="flex shrink-0 items-center justify-between gap-3 pl-12 sm:flex-col sm:items-end sm:justify-center sm:gap-1.5 sm:pl-0">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${style.badge}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                    {item.status_badge || 'Update'}
                  </span>

                  <span className="inline-flex items-center gap-1 text-[11px] text-subtle">
                    <Clock className="h-3 w-3 shrink-0" strokeWidth={1.9} />
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
