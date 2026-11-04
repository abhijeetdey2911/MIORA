import { useCallback, useEffect, useState } from 'react';
import { Bell, CheckCheck, Clock, Send } from 'lucide-react';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../services/multiAgentService';
import type { NotificationItem } from '../types/multiAgent';

export function UpdatesPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const loadNotifications = useCallback(async () => {
    try {
      const rows = await listNotifications({ unread_only: unreadOnly });
      setNotifications(rows);
    } catch {
      // Keep UI responsive
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    let cancelled = false;
    listNotifications({ unread_only: unreadOnly })
      .then((rows) => {
        if (!cancelled) {
          setNotifications(rows);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [unreadOnly]);

  const filtered = notifications.filter((n) => {
    if (categoryFilter === 'all') return true;
    if (categoryFilter === 'interviews_offers') {
      return (
        n.event_type.includes('interview') ||
        n.event_type.includes('offer') ||
        n.event_type.includes('recruiter')
      );
    }
    if (categoryFilter === 'applications') {
      return (
        n.event_type.includes('application') ||
        n.event_type.includes('submission')
      );
    }
    if (categoryFilter === 'workflow') {
      return n.event_type.includes('workflow');
    }
    return true;
  });

  const handleMarkRead = async (id: string) => {
    try {
      const updated = await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      await loadNotifications();
    } catch {
      // Ignore
    }
  };

  return (
    <div className="space-y-4">
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card">
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: 'all', label: 'All Updates' },
            { id: 'interviews_offers', label: 'Recruiter, Interviews & Offers' },
            { id: 'applications', label: 'Application Submissions' },
            { id: 'workflow', label: 'Automation & Workflows' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setCategoryFilter(tab.id)}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                categoryFilter === tab.id
                  ? 'bg-accent text-white shadow-card'
                  : 'border border-line bg-surface-2 text-muted hover:text-ink'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-ink">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
            />
            Unread only
          </label>

          <button
            type="button"
            onClick={handleMarkAllRead}
            className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink hover:border-subtle/50"
          >
            <CheckCheck className="h-3.5 w-3.5 text-accent" />
            Mark All Read
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        {loading ? (
          <p className="py-8 text-center text-xs text-muted">
            Loading updates and notifications...
          </p>
        ) : filtered.length === 0 ? (
          <div className="py-10 text-center">
            <Bell className="mx-auto h-7 w-7 text-subtle" />
            <p className="mt-2 text-sm font-semibold text-ink">
              No updates in this view
            </p>
            <p className="mt-1 text-xs text-muted">
              Application milestones, recruiter responses, interview
              invitations, and workflow events will appear here automatically.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {filtered.map((item) => (
              <li
                key={item.id}
                className={`flex flex-col justify-between gap-3 py-3.5 sm:flex-row sm:items-center ${
                  !item.is_read ? 'bg-accent-soft/20 px-3 rounded-xl' : ''
                }`}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-ink">
                      {item.title}
                    </p>
                    {item.status_badge && (
                      <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-[11px] font-medium text-ink">
                        {item.status_badge}
                      </span>
                    )}
                    {item.telegram_sent && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-2 py-0.5 text-[10px] font-medium text-sky-600 dark:text-sky-300">
                        <Send className="h-2.5 w-2.5" />
                        Telegram Sent
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted">{item.message}</p>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span className="inline-flex items-center gap-1 text-[11px] text-subtle">
                    <Clock className="h-3 w-3" />
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                  {!item.is_read && (
                    <button
                      type="button"
                      onClick={() => handleMarkRead(item.id)}
                      className="rounded-lg border border-line bg-surface-2 px-2.5 py-1 text-[11px] font-medium text-ink hover:border-subtle/50"
                    >
                      Mark Read
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
