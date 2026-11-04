import { Briefcase, CalendarCheck, Layers, Send, Sparkles } from 'lucide-react';
import type {
  ActivityPoint,
  ApplicationUpdateItem,
  AutomationInfo,
  PreferencePerformanceItem,
  StatItem,
} from '../types/dashboard';
import { formatShortDate, getLastDays } from '../utils/date';

/**
 * Sample data for the Dashboard UI.
 * Real execution metrics will replace these once the multi-agent automation engine is connected.
 */

export const SAMPLE_USER = { name: 'Abhijeet' };

export const SAMPLE_STATS: readonly StatItem[] = [
  {
    id: 'discovered',
    label: 'Jobs Discovered',
    value: 328,
    change: 12,
    tone: 'orange',
    icon: Briefcase,
  },
  {
    id: 'matching',
    label: 'Matching Jobs',
    value: 146,
    change: 15,
    tone: 'amber',
    icon: Sparkles,
  },
  {
    id: 'shortlisted',
    label: 'Shortlisted',
    value: 64,
    change: 18,
    tone: 'violet',
    icon: Layers,
  },
  {
    id: 'applications',
    label: 'Applications',
    value: 42,
    change: 31,
    tone: 'blue',
    icon: Send,
  },
  {
    id: 'interviews',
    label: 'Interviews',
    value: 6,
    change: 50,
    tone: 'green',
    icon: CalendarCheck,
  },
];

export const SAMPLE_PREFERENCE_PERFORMANCE: readonly PreferencePerformanceItem[] = [
  {
    id: 'pref-sample-p1',
    code: 'P1',
    name: 'Data Analytics',
    title: 'P1 — Data Analytics',
    targetRoles: ['Data Analyst', 'Business Intelligence Engineer', 'Product Analyst'],
    locations: ['Bengaluru', 'Pune', 'Remote'],
    workMode: 'Hybrid',
    isActive: true,
    metrics: {
      jobsDiscovered: 142,
      matchingJobs: 62,
      shortlisted: 26,
      applicationsSubmitted: 18,
      interviews: 2,
    },
    sampleResults: [
      {
        id: 'p1-job-1',
        title: 'Senior Product Data Analyst',
        company: 'Razorpay',
        location: 'Bengaluru · Hybrid',
        matchScore: 92,
        stage: 'Interview',
      },
      {
        id: 'p1-job-2',
        title: 'Analytics Engineer',
        company: 'Swiggy',
        location: 'Remote',
        matchScore: 88,
        stage: 'Applied',
      },
      {
        id: 'p1-job-3',
        title: 'Business Intelligence Analyst',
        company: 'Atlassian',
        location: 'Bengaluru · Remote',
        matchScore: 84,
        stage: 'Shortlisted',
      },
    ],
  },
  {
    id: 'pref-sample-p2',
    code: 'P2',
    name: 'Software Development',
    title: 'P2 — Software Development',
    targetRoles: ['Full-Stack Engineer', 'Backend Developer', 'Software Engineer'],
    locations: ['Bengaluru', 'Hyderabad', 'Remote'],
    workMode: 'Remote',
    isActive: true,
    metrics: {
      jobsDiscovered: 186,
      matchingJobs: 84,
      shortlisted: 38,
      applicationsSubmitted: 24,
      interviews: 4,
    },
    sampleResults: [
      {
        id: 'p2-job-1',
        title: 'Senior Frontend Engineer',
        company: 'Linear',
        location: 'Remote',
        matchScore: 95,
        stage: 'Interview',
      },
      {
        id: 'p2-job-2',
        title: 'Full-Stack Engineer, Billing',
        company: 'Stripe',
        location: 'Bengaluru · Hybrid',
        matchScore: 91,
        stage: 'Applied',
      },
      {
        id: 'p2-job-3',
        title: 'Product Engineer',
        company: 'Raycast',
        location: 'Remote',
        matchScore: 89,
        stage: 'Shortlisted',
      },
    ],
  },
];

export const USER_CENTRIC_WORKFLOW_STEPS: readonly string[] = [
  'Create one or more job preferences',
  'Upload and approve your resume',
  'Press the central Start JobHunter button',
  'Active preferences are processed independently by agents',
  'Results are stored and tracked per preference',
];

/** Applications per day for the last seven days, ending today. */
const SAMPLE_ACTIVITY_VALUES = [4, 14, 12, 21, 18, 28, 40] as const;

export function getSampleActivity(today: Date = new Date()): ActivityPoint[] {
  return getLastDays(SAMPLE_ACTIVITY_VALUES.length, today).map((date, index) => ({
    label: formatShortDate(date),
    applications: SAMPLE_ACTIVITY_VALUES[index],
  }));
}

export const SAMPLE_AUTOMATION: AutomationInfo = {
  name: 'JobHunter Central Orchestrator',
  defaultState: 'Ready',
  engineConnected: false,
};

export const SAMPLE_RECENT_UPDATES: readonly ApplicationUpdateItem[] = [
  {
    id: 'upd-1',
    company: 'Linear',
    position: 'Senior Frontend Engineer',
    description: 'Technical interview scheduled with the Core Product team.',
    timestamp: 'Today, 10:20 AM',
    status: 'Interview',
  },
  {
    id: 'upd-2',
    company: 'Vercel',
    position: 'Staff UI Engineer',
    description: 'Application moved to hiring manager review after portfolio screening.',
    timestamp: 'Today, 8:45 AM',
    status: 'Under Review',
  },
  {
    id: 'upd-3',
    company: 'Stripe',
    position: 'Full-Stack Engineer, Billing',
    description: 'Tailored resume and cover letter submitted via Greenhouse.',
    timestamp: 'Yesterday, 6:15 PM',
    status: 'Applied',
  },
  {
    id: 'upd-4',
    company: 'Raycast',
    position: 'Product Engineer',
    description: 'Recruiter reviewed profile and forwarded to engineering lead.',
    timestamp: 'Nov 1, 3:40 PM',
    status: 'Under Review',
  },
  {
    id: 'upd-5',
    company: 'Figma',
    position: 'Software Engineer, Design Systems',
    description: 'Role closed after initial screening; position filled internally.',
    timestamp: 'Oct 31, 11:10 AM',
    status: 'Rejected',
  },
];
