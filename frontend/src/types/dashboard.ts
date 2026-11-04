import type { LucideIcon } from 'lucide-react';

export type StatTone = 'orange' | 'amber' | 'violet' | 'blue' | 'green';

export interface StatItem {
  id: string;
  label: string;
  value: number;
  /** Percentage change vs. the previous period. */
  change: number;
  tone: StatTone;
  icon: LucideIcon;
}

export interface ActivityPoint {
  label: string;
  applications: number;
}

export type AutomationUIState =
  | 'Ready'
  | 'Running'
  | 'Paused'
  | 'Completed'
  | 'Failed';

export interface AutomationInfo {
  name: string;
  defaultState: AutomationUIState;
  engineConnected: boolean;
}

export interface PreferenceSampleRole {
  id: string;
  title: string;
  company: string;
  location: string;
  matchScore: number;
  stage: 'Discovered' | 'Matching' | 'Shortlisted' | 'Applied' | 'Interview';
}

export interface PreferencePerformanceItem {
  id: string;
  code: string;
  name: string;
  title: string;
  targetRoles: string[];
  locations: string[];
  workMode: string;
  isActive: boolean;
  metrics: {
    jobsDiscovered: number;
    matchingJobs: number;
    shortlisted: number;
    applicationsSubmitted: number;
    interviews: number;
  };
  sampleResults: PreferenceSampleRole[];
}

export type ApplicationUpdateStatus =
  | 'Applied'
  | 'Under Review'
  | 'Interview'
  | 'Rejected';

export interface ApplicationUpdateItem {
  id: string;
  company: string;
  position: string;
  description: string;
  timestamp: string;
  status: ApplicationUpdateStatus;
}
