export type WorkMode = 'Remote' | 'Hybrid' | 'On-site';

export type EmploymentType = 'Full-time' | 'Internship' | 'Contract' | 'Part-time';

export type ExperienceLevel = 'Fresher' | 'Entry-level' | 'Experienced';

export type JobCategory =
  | 'Data Analytics'
  | 'Software Development'
  | 'AI & Machine Learning'
  | 'DevOps & Cloud'
  | 'Product & Design'
  | 'Cybersecurity & QA';

export const JOB_CATEGORIES: readonly JobCategory[] = [
  'Data Analytics',
  'Software Development',
  'AI & Machine Learning',
  'DevOps & Cloud',
  'Product & Design',
  'Cybersecurity & QA',
];

export const JOB_ROLES_BY_CATEGORY: Record<JobCategory, readonly string[]> = {
  'Data Analytics': [
    'Data Analyst',
    'Business Analyst',
    'BI Analyst',
    'Reporting Analyst',
    'Product Analyst',
    'SQL Developer',
    'Junior Data Analyst',
    'Data Engineer',
    'Analytics Engineer',
  ],
  'Software Development': [
    'Software Engineer',
    'Full-Stack Developer',
    'Full-Stack Engineer',
    'Frontend Engineer',
    'Backend Developer',
    'Backend Engineer',
    'Python Developer',
    'React Developer',
    'Java Developer',
  ],
  'AI & Machine Learning': [
    'AI Engineer',
    'AI Applications Engineer',
    'Machine Learning Engineer',
    'Data Scientist',
    'GenAI / LLM Engineer',
    'NLP Engineer',
    'Computer Vision Engineer',
  ],
  'DevOps & Cloud': [
    'DevOps Engineer',
    'Cloud Engineer',
    'Site Reliability Engineer (SRE)',
    'Platform Engineer',
    'Cloud Architect',
  ],
  'Product & Design': [
    'Product Manager',
    'Associate Product Manager',
    'Product Designer',
    'UI/UX Designer',
    'Technical Program Manager',
  ],
  'Cybersecurity & QA': [
    'QA Automation Engineer',
    'SDET',
    'Security Engineer',
    'Application Security Analyst',
    'Performance Test Engineer',
  ],
};

export function inferJobCategory(roles: readonly string[]): JobCategory {
  if (!roles || roles.length === 0) {
    return 'Data Analytics';
  }
  const normalized = new Set(roles.map((r) => r.trim().toLowerCase()));
  let bestCategory: JobCategory = 'Data Analytics';
  let bestMatches = 0;

  for (const category of JOB_CATEGORIES) {
    const categoryRoles = JOB_ROLES_BY_CATEGORY[category];
    const matches = categoryRoles.filter((r) =>
      normalized.has(r.toLowerCase()),
    ).length;
    if (matches > bestMatches) {
      bestMatches = matches;
      bestCategory = category;
    }
  }
  return bestCategory;
}

export const PREDEFINED_LOCATIONS: readonly string[] = [
  'Bangalore',
  'Hyderabad',
  'Pune',
  'Mumbai',
  'Delhi NCR',
  'Chennai',
  'Kolkata',
  'Jamshedpur',
  'Remote (India)',
  'Anywhere in India',
];

export type LocationMode = 'INDIA_ONLY' | 'SELECTED_LOCATIONS_ONLY' | 'WORLDWIDE_REMOTE';

export interface LocationModeOption {
  value: LocationMode;
  label: string;
  badge: string;
  description: string;
}

export const LOCATION_MODES: readonly LocationModeOption[] = [
  {
    value: 'INDIA_ONLY',
    label: 'India Only (Default)',
    badge: 'India Only',
    description: 'Restricts results to Indian locations (all cities) & India-eligible remote roles.',
  },
  {
    value: 'SELECTED_LOCATIONS_ONLY',
    label: 'Selected Locations Only',
    badge: 'Selected Cities',
    description: 'Strictly restricted to your chosen cities above. Excludes other cities.',
  },
  {
    value: 'WORLDWIDE_REMOTE',
    label: 'Worldwide Remote',
    badge: 'Worldwide Remote',
    description: 'Includes global remote roles open to Indian candidates + Indian locations.',
  },
];

export const WORK_MODES: readonly WorkMode[] = ['Remote', 'Hybrid', 'On-site'];

export const EMPLOYMENT_TYPES: readonly EmploymentType[] = [
  'Full-time',
  'Internship',
  'Contract',
  'Part-time',
];

export const EXPERIENCE_LEVELS: readonly ExperienceLevel[] = [
  'Fresher',
  'Entry-level',
  'Experienced',
];

export const CURRENCIES: readonly string[] = ['INR', 'USD', 'EUR', 'GBP', 'SGD', 'AED'];

export interface JobPreferencePayload {
  preference_name: string;
  job_roles: string[];
  locations: string[];
  location_mode?: LocationMode;
  work_mode: WorkMode;
  employment_type: EmploymentType;
  experience_level: ExperienceLevel;
  min_salary: number | null;
  max_salary: number | null;
  currency: string;
  skills: string[];
  minimum_match_score: number;
  is_active: boolean;
}

export interface JobPreference extends JobPreferencePayload {
  id: string;
  created_at: string;
  updated_at: string;
}
