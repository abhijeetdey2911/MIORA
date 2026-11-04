import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Award,
  Briefcase,
  CalendarCheck,
  Layers,
  Send,
  Sparkles,
} from 'lucide-react';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { AutomationCard } from '../components/dashboard/AutomationCard';
import { PreferencePerformance } from '../components/dashboard/PreferencePerformance';
import { RecentUpdates } from '../components/dashboard/RecentUpdates';
import { StatCard } from '../components/dashboard/StatCard';
import { getDashboardOverview } from '../services/multiAgentService';
import type { ActivityPoint, StatItem } from '../types/dashboard';
import type { DashboardOverviewData } from '../types/multiAgent';

export function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverviewData | null>(null);

  const fetchOverview = useCallback(() => {
    getDashboardOverview()
      .then((data) => {
        setOverview(data);
      })
      .catch(() => {
        // Keep current dashboard state if offline
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    getDashboardOverview()
      .then((data) => {
        if (!cancelled) {
          setOverview(data);
        }
      })
      .catch(() => {
        // Keep current dashboard state if offline
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const stats: StatItem[] = useMemo(() => {
    return [
      {
        id: 'discovered',
        label: 'Jobs Discovered',
        value: overview?.jobs_discovered ?? 0,
        change: 0,
        tone: 'orange',
        icon: Briefcase,
      },
      {
        id: 'matching',
        label: 'Matching Jobs',
        value: overview?.matching_jobs ?? 0,
        change: 0,
        tone: 'amber',
        icon: Sparkles,
      },
      {
        id: 'shortlisted',
        label: 'Shortlisted Jobs',
        value: overview?.shortlisted_jobs ?? 0,
        change: 0,
        tone: 'violet',
        icon: Layers,
      },
      {
        id: 'applications',
        label: 'Applications Submitted',
        value: overview?.applications_submitted ?? 0,
        change: 0,
        tone: 'blue',
        icon: Send,
      },
      {
        id: 'interviews',
        label: 'Interviews',
        value: overview?.interviews ?? 0,
        change: 0,
        tone: 'green',
        icon: CalendarCheck,
      },
      {
        id: 'offers',
        label: 'Offers',
        value: overview?.offers ?? 0,
        change: 0,
        tone: 'green',
        icon: Award,
      },
    ];
  }, [overview]);

  const activity: ActivityPoint[] = useMemo(() => {
    if (overview?.activity_series && overview.activity_series.length > 0) {
      return overview.activity_series.map((pt) => ({
        date: pt.date,
        label: pt.day,
        applications: pt.applications,
      }));
    }
    return [
      { date: '1', label: 'Mon', applications: 0 },
      { date: '2', label: 'Tue', applications: 0 },
      { date: '3', label: 'Wed', applications: 0 },
      { date: '4', label: 'Thu', applications: 0 },
      { date: '5', label: 'Fri', applications: 0 },
      { date: '6', label: 'Sat', applications: 0 },
      { date: '7', label: 'Sun', applications: 0 },
    ];
  }, [overview]);

  return (
    <div className="space-y-4">
      {/* Overall Statistics (6 compact PostgreSQL-backed cards) */}
      <div className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        {stats.map((stat) => (
          <StatCard key={stat.id} stat={stat} />
        ))}
      </div>

      {/* Applications Over Time + Central Automation Control */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ActivityChart data={activity} />
        </div>
        <AutomationCard
          automationState={overview?.automation_state ?? 'ready'}
          isKillSwitchEngaged={overview?.is_kill_switch_engaged ?? false}
          approvalMode={overview?.approval_mode ?? 'manual'}
          activePreferenceCount={overview?.active_preferences_count ?? 0}
          pausedPreferenceCount={overview?.paused_preferences_count ?? 0}
          eligiblePreferenceCount={overview?.eligible_preferences_count ?? 0}
          lastRun={overview?.last_run ?? null}
          onWorkflowUpdated={fetchOverview}
        />
      </div>

      {/* Preference-Wise Performance Section */}
      <PreferencePerformance items={overview?.preference_performance ?? []} />

      {/* Recent Application Updates */}
      <RecentUpdates updates={overview?.recent_updates ?? []} />
    </div>
  );
}
