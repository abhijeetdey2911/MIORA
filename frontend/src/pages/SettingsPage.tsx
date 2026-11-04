import { useEffect, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  Globe,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  getAutomationSettings,
  listJobSources,
  toggleJobSource,
  updateAutomationSettings,
} from '../services/multiAgentService';
import { getAIProviderStatus } from '../services/resumeService';
import type {
  AutomationSettingsData,
  JobSourceItem,
} from '../types/multiAgent';
import type { AIProviderStatus } from '../types/resume';

export function SettingsPage() {
  const [aiStatus, setAiStatus] = useState<AIProviderStatus | null>(null);
  const [settings, setSettings] = useState<AutomationSettingsData | null>(null);
  const [sources, setSources] = useState<JobSourceItem[]>([]);
  const [savedBanner, setSavedBanner] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getAIProviderStatus(),
      getAutomationSettings(),
      listJobSources(),
    ])
      .then(([ai, autoSet, srcList]) => {
        if (!cancelled) {
          setAiStatus(ai);
          setSettings(autoSet);
          setSources(srcList);
        }
      })
      .catch(() => {
        // Keep UI responsive
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSaveSettings = async () => {
    if (!settings) return;
    setSavedBanner(null);
    try {
      const updated = await updateAutomationSettings(settings);
      setSettings(updated);
      setSavedBanner('Settings saved to PostgreSQL.');
    } catch {
      // Ignore
    }
  };

  const handleToggleSource = async (source: JobSourceItem) => {
    try {
      const updated = await toggleJobSource(source.id, !source.is_enabled);
      setSources((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch {
      // Ignore
    }
  };

  return (
    <div className="space-y-4">
      {savedBanner && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{savedBanner}</span>
        </div>
      )}

      {/* AI Provider Status & Job Discovery Adapters */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <h2 className="text-sm font-semibold text-ink">
                AI Provider Status
              </h2>
            </div>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                aiStatus?.configured
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300'
                  : 'bg-amber-500/10 text-amber-600 dark:text-amber-300'
              }`}
            >
              {aiStatus?.configured ? 'Configured' : 'Using Deterministic Rule Engine'}
            </span>
          </div>

          <div className="mt-3 rounded-xl border border-line bg-surface-2 p-3.5 text-xs text-muted">
            <p>
              Provider:{' '}
              <span className="font-semibold uppercase text-ink">
                {aiStatus?.provider || 'openai'}
              </span>{' '}
              · Model:{' '}
              <span className="font-semibold text-ink">
                {aiStatus?.model || 'gpt-4o-mini'}
              </span>
            </p>
            <p className="mt-1.5">
              {aiStatus?.configured
                ? 'Backend LLM API key is active for Phase 3B Resume Intelligence and Agent 2 Job Matching.'
                : aiStatus?.setup_message ||
                  'Set AI_API_KEY in backend/.env to enable live LLM evaluation. Agent 2 automatically uses transparent deterministic rule scoring when no API key is configured.'}
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-semibold text-ink">
              Permitted Job Discovery Source Adapters (Agent 1)
            </h2>
          </div>

          <ul className="mt-3 divide-y divide-line">
            {sources.map((src) => (
              <li
                key={src.id}
                className="flex items-center justify-between gap-3 py-2.5 text-xs"
              >
                <div>
                  <p className="font-semibold text-ink">{src.name}</p>
                  <p className="text-[11px] text-muted">
                    Rate limit: {src.rate_limit_per_minute}/min ·{' '}
                    {src.last_synced_at
                      ? `Last synced ${new Date(src.last_synced_at).toLocaleTimeString()}`
                      : 'Ready'}
                  </p>
                </div>

                <label className="inline-flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={src.is_enabled}
                    onChange={() => handleToggleSource(src)}
                  />
                  <span className="text-xs font-medium text-ink">
                    {src.is_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Telegram Notification Settings & Safety Permissions */}
      {settings && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Send className="h-4 w-4 text-sky-500" />
                <h2 className="text-sm font-semibold text-ink">
                  Telegram Bot Notifications (Part 12)
                </h2>
              </div>

              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                  settings.telegram_configured
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300'
                    : 'bg-surface-2 text-muted'
                }`}
              >
                {settings.telegram_configured
                  ? 'Bot Token Configured'
                  : 'Bot Token Not Set in .env'}
              </span>
            </div>

            <div className="mt-3 space-y-2.5 text-xs">
              <label className="flex items-center justify-between rounded-xl border border-line bg-surface-2 p-3 font-semibold text-ink">
                <span>Enable Telegram Notifications</span>
                <input
                  type="checkbox"
                  checked={settings.telegram_notifications_enabled}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      telegram_notifications_enabled: e.target.checked,
                    })
                  }
                />
              </label>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 pt-1">
                {[
                  {
                    key: 'notify_on_workflow_start',
                    label: 'Workflow Started',
                  },
                  {
                    key: 'notify_on_workflow_complete',
                    label: 'Workflow Completed',
                  },
                  { key: 'notify_on_errors', label: 'Workflow Errors' },
                  {
                    key: 'notify_on_application_submitted',
                    label: 'Application Submitted',
                  },
                  {
                    key: 'notify_on_submission_unconfirmed',
                    label: 'Submission Unconfirmed',
                  },
                  {
                    key: 'notify_on_interview',
                    label: 'Interview Invitations',
                  },
                  {
                    key: 'notify_on_recruiter_response',
                    label: 'Recruiter Responses',
                  },
                  { key: 'notify_on_offer', label: 'Job Offers' },
                ].map(({ key, label }) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 py-2 text-ink"
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(
                        settings[key as keyof AutomationSettingsData],
                      )}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          [key]: e.target.checked,
                        })
                      }
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <h2 className="text-sm font-semibold text-ink">
                Agent 4 Route Auto-Submission Permissions & Safety
              </h2>
            </div>
            <p className="mt-1 text-xs text-muted">
              Even in Auto-Authorised Mode, Agent 4 will only auto-submit on
              verified routes whose route type is explicitly permitted below.
            </p>

            <div className="mt-3 space-y-2.5 text-xs">
              {[
                {
                  key: 'allow_portal_auto_submit',
                  label: 'Subagent 4.1 — Official Company Portals',
                },
                {
                  key: 'allow_form_auto_submit',
                  label: 'Subagent 4.2 — Official Application Forms',
                },
                {
                  key: 'allow_hr_email_auto_submit',
                  label: 'Subagent 4.3 — Published HR Application Emails',
                },
                {
                  key: 'allow_recruiter_outreach',
                  label: 'Subagent 4.4 — Verified Recruiter Outreach',
                },
              ].map(({ key, label }) => (
                <label
                  key={key}
                  className="flex items-center justify-between rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 font-medium text-ink"
                >
                  <span className="inline-flex items-center gap-2">
                    <Bot className="h-3.5 w-3.5 text-accent" />
                    {label}
                  </span>
                  <input
                    type="checkbox"
                    checked={Boolean(
                      settings[key as keyof AutomationSettingsData],
                    )}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        [key]: e.target.checked,
                      })
                    }
                  />
                </label>
              ))}
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={handleSaveSettings}
                className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card"
              >
                Save Notification & Safety Settings
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
