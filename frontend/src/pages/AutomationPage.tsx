import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  History,
  Loader2,
  OctagonX,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import {
  getAutomationSchedule,
  getAutomationSettings,
  listWorkflowRuns,
  pauseJobHunterWorkflow,
  recoverInterruptedWorkflows,
  resumeJobHunterWorkflow,
  startJobHunterWorkflow,
  stopJobHunterWorkflow,
  updateAutomationSchedule,
  updateAutomationSettings,
} from '../services/multiAgentService';
import type {
  AutomationSettingsData,
  ScheduledJobData,
  WorkflowRunSummary,
} from '../types/multiAgent';

export function AutomationPage() {
  const [settings, setSettings] = useState<AutomationSettingsData | null>(null);
  const [schedule, setSchedule] = useState<ScheduledJobData | null>(null);
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [sData, schedData, runsData] = await Promise.all([
        getAutomationSettings(),
        getAutomationSchedule(),
        listWorkflowRuns(15),
      ]);
      setSettings(sData);
      setSchedule(schedData);
      setRuns(runsData);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Failed to load automation controls.',
      );
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getAutomationSettings(),
      getAutomationSchedule(),
      listWorkflowRuns(15),
    ])
      .then(([sData, schedData, runsData]) => {
        if (!cancelled) {
          setSettings(sData);
          setSchedule(schedData);
          setRuns(runsData);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setErrorMessage(
            err instanceof Error
              ? err.message
              : 'Failed to load automation controls.',
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleAction = async (
    actionKey: string,
    fn: () => Promise<unknown>,
    successMsg: string,
  ) => {
    setBusyAction(actionKey);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      await fn();
      setStatusMessage(successMsg);
      await loadAll();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Action failed.');
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Control Bar: Start, Pause, Resume, Stop (Kill Switch), Recover */}
      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-ink">
                Automation Control Centre
              </h2>
              {settings && (
                <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-xs font-semibold capitalize text-accent-ink">
                  {settings.is_kill_switch_engaged
                    ? 'Kill Switch Engaged'
                    : settings.automation_state}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-muted">
              Coordinate LangGraph Agents 1–5 across all active job preferences
              with strict safety limits and PostgreSQL checkpointing.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                handleAction(
                  'start',
                  () => startJobHunterWorkflow({ trigger_source: 'manual' }),
                  'JobHunter workflow executed across active preferences.',
                )
              }
              className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card hover:brightness-105 disabled:opacity-60"
            >
              {busyAction === 'start' ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5 fill-current" />
              )}
              Start JobHunter
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                handleAction(
                  'pause',
                  () => pauseJobHunterWorkflow(),
                  'Active workflows paused at safe agent boundaries.',
                )
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-xs font-medium text-ink hover:border-subtle/50 disabled:opacity-60"
            >
              <Pause className="h-3.5 w-3.5" />
              Pause
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                handleAction(
                  'resume',
                  () => resumeJobHunterWorkflow(),
                  'Paused workflows resumed from PostgreSQL checkpoint.',
                )
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-xs font-medium text-ink hover:border-subtle/50 disabled:opacity-60"
            >
              <Play className="h-3.5 w-3.5" />
              Resume
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                handleAction(
                  'recover',
                  () => recoverInterruptedWorkflows(),
                  'Checked and recovered any interrupted runs from PostgreSQL checkpoints.',
                )
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-xs font-medium text-ink hover:border-subtle/50 disabled:opacity-60"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Recover Runs
            </button>

            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() =>
                handleAction(
                  'stop',
                  () =>
                    stopJobHunterWorkflow(
                      'Genuine kill switch engaged from Automation Control Centre.',
                    ),
                  'Kill switch engaged. All running and queued workflows stopped immediately.',
                )
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-500/20 dark:text-rose-300 disabled:opacity-60"
            >
              <OctagonX className="h-3.5 w-3.5" />
              Stop (Kill Switch)
            </button>
          </div>
        </div>

        {errorMessage && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
        {statusMessage && !errorMessage && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{statusMessage}</span>
          </div>
        )}
      </section>

      {/* Limits & Permissions + Schedule Configuration */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {settings && (
          <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-semibold text-ink">
                Limits, Safety Thresholds & Approval Mode
              </h3>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Approval Mode
                </label>
                <select
                  value={settings.approval_mode}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      approval_mode: e.target.value as
                        | 'manual'
                        | 'auto_authorised',
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                >
                  <option value="manual">
                    Manual Approval Mode (Recommended)
                  </option>
                  <option value="auto_authorised">
                    Auto-Authorised Within Limits
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Minimum Match Score (%)
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={settings.minimum_match_score}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      minimum_match_score: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Max Jobs Per Run
                </label>
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={settings.max_jobs_per_run}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_jobs_per_run: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Max Applications Per Run
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={settings.max_applications_per_run}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_applications_per_run: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Max Applications Per Day
                </label>
                <input
                  type="number"
                  min={0}
                  max={200}
                  value={settings.max_applications_per_day}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_applications_per_day: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Max Runtime (Seconds)
                </label>
                <input
                  type="number"
                  min={60}
                  max={14400}
                  value={settings.max_runtime_seconds}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_runtime_seconds: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Max API Spend (USD) · Current: $
                  {settings.current_api_spend_usd.toFixed(4)}
                </label>
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  max={500}
                  value={settings.max_api_spend_usd}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      max_api_spend_usd: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Retry Limit
                </label>
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={settings.retry_limit}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      retry_limit: Number(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() =>
                  handleAction(
                    'save-settings',
                    () => updateAutomationSettings(settings),
                    'Automation limits and safety settings saved.',
                  )
                }
                className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white"
              >
                Save Limits & Permissions
              </button>
            </div>
          </section>
        )}

        {schedule && (
          <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CalendarClock className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold text-ink">
                  Scheduled Execution
                </h3>
              </div>

              <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-ink">
                <input
                  type="checkbox"
                  checked={schedule.is_enabled}
                  onChange={(e) =>
                    setSchedule({ ...schedule, is_enabled: e.target.checked })
                  }
                />
                Schedule Enabled
              </label>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-muted">
                  Schedule Name
                </label>
                <input
                  type="text"
                  value={schedule.name}
                  onChange={(e) =>
                    setSchedule({ ...schedule, name: e.target.value })
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-muted">
                    Daily Run Time (24h HH:MM)
                  </label>
                  <input
                    type="time"
                    value={schedule.daily_time}
                    onChange={(e) =>
                      setSchedule({ ...schedule, daily_time: e.target.value })
                    }
                    className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-muted">
                    Timezone
                  </label>
                  <input
                    type="text"
                    value={schedule.timezone}
                    onChange={(e) =>
                      setSchedule({ ...schedule, timezone: e.target.value })
                    }
                    className="mt-1 w-full rounded-xl border border-line bg-surface-2 px-3 py-2 text-xs text-ink"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-line bg-surface-2 p-3 text-[11px] text-muted">
                <p>
                  Cron Expression:{' '}
                  <code className="font-semibold text-ink">
                    {schedule.cron_expression}
                  </code>
                </p>
                <p className="mt-1">
                  Next Scheduled Run:{' '}
                  <span className="font-medium text-ink">
                    {schedule.next_run_at
                      ? new Date(schedule.next_run_at).toLocaleString()
                      : 'Disabled'}
                  </span>
                </p>
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() =>
                  handleAction(
                    'save-schedule',
                    () =>
                      updateAutomationSchedule({
                        name: schedule.name,
                        is_enabled: schedule.is_enabled,
                        daily_time: schedule.daily_time,
                        timezone: schedule.timezone,
                        max_jobs_per_run: schedule.max_jobs_per_run,
                        max_applications_per_run:
                          schedule.max_applications_per_run,
                      }),
                    'Schedule configuration saved.',
                  )
                }
                className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white"
              >
                Save Schedule
              </button>
            </div>
          </section>
        )}
      </div>

      {/* Workflow Execution History */}
      <section className="rounded-2xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold text-ink">
            Workflow Execution History ({runs.length})
          </h3>
        </div>

        {runs.length === 0 ? (
          <p className="mt-4 text-xs text-muted">
            No workflow runs executed yet.
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            {runs.map((run) => (
              <div
                key={run.id}
                className="rounded-xl border border-line bg-surface-2 p-3.5 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-accent-soft px-2.5 py-0.5 text-[11px] font-semibold capitalize text-accent-ink">
                      {run.status}
                    </span>
                    <span className="font-semibold text-ink">
                      Trigger: {run.trigger_source} · {run.active_preferences}{' '}
                      active preference(s)
                    </span>
                  </div>
                  <span className="text-[11px] text-muted">
                    {run.started_at
                      ? new Date(run.started_at).toLocaleString()
                      : ''}
                  </span>
                </div>

                {run.preference_executions.length > 0 && (
                  <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {run.preference_executions.map((pe) => (
                      <div
                        key={pe.id}
                        className="rounded-lg border border-line bg-surface p-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-ink">
                            {pe.preference_name}
                          </span>
                          <span className="text-[10px] capitalize text-muted">
                            {pe.status} ({pe.current_agent})
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-muted">
                          Discovered: {pe.jobs_discovered} · Matched:{' '}
                          {pe.matching_jobs} · Shortlisted:{' '}
                          {pe.shortlisted_jobs} · Applied:{' '}
                          {pe.applications_submitted}
                        </p>
                        {pe.error_message && (
                          <p className="mt-1 text-[10px] text-rose-500">
                            {pe.error_message}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
