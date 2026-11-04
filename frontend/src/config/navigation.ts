import {
  Bell,
  Compass,
  FileText,
  FolderOpen,
  House,
  Play,
  Settings,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  /** Page heading shown in the header. */
  title: string;
  /** Page subtitle shown in the header. */
  description: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    label: 'Dashboard',
    path: '/',
    icon: House,
    title: 'Your Job Hunting Hub',
    description:
      'Discover opportunities, apply smarter, and track everything in one place.',
  },
  {
    label: 'Preferences',
    path: '/preferences',
    icon: SlidersHorizontal,
    title: 'Job Preferences',
    description: 'Manage the opportunities JobHunter should look for.',
  },
  {
    label: 'Resume',
    path: '/resume',
    icon: FileText,
    title: 'My Resumes',
    description:
      'Manage your resumes and organise them for different job preferences.',
  },
  {
    label: 'Job Discovery',
    path: '/jobs',
    icon: Compass,
    title: 'Job Discovery & Matching',
    description:
      'Explore deduplicated job listings, AI preference match scores, and verified application routes.',
  },
  {
    label: 'Applications',
    path: '/applications',
    icon: FolderOpen,
    title: 'Applications',
    description: 'Track every application from preparation and approval to offer.',
  },
  {
    label: 'Automation',
    path: '/automation',
    icon: Play,
    title: 'Automation Control Centre',
    description:
      'Start, pause, resume, schedule, and monitor your multi-agent job hunt.',
  },
  {
    label: 'Settings',
    path: '/settings',
    icon: Settings,
    title: 'Settings',
    description:
      'Configure AI providers, job sources, Telegram notifications, and safety permissions.',
  },
];

export const UPDATES_PAGE: NavItem = {
  label: 'Updates',
  path: '/updates',
  icon: Bell,
  title: 'Application Updates & Notifications',
  description:
    'Follow recruiter responses, interview invitations, offers, and automation notifications.',
};

const ALL_PAGES: readonly NavItem[] = [...NAV_ITEMS, UPDATES_PAGE];

export function findNavItem(pathname: string): NavItem | undefined {
  return ALL_PAGES.find((item) =>
    item.path === '/'
      ? pathname === '/'
      : pathname === item.path || pathname.startsWith(`${item.path}/`),
  );
}
