export type ResumeFormat = 'PDF' | 'DOCX';

export type ResumeProcessingStatus =
  | 'Uploaded'
  | 'Processing'
  | 'Processed'
  | 'Failed';

export type ResumeAIStatus =
  | 'Not Analysed'
  | 'Analysing'
  | 'Analysis Complete'
  | 'Draft Generated'
  | 'Awaiting Approval'
  | 'Approved';

export type SuggestionPriority = 'High' | 'Medium' | 'Low';
export type SuggestionStatus = 'Pending' | 'Accepted' | 'Rejected';

export interface AssociatedPreferenceSummary {
  id: string;
  preference_name: string;
  is_active: boolean;
  approved_resume_version_id?: string | null;
}

export interface ResumeItem {
  id: string;
  name?: string;
  resume_name: string;
  original_filename: string;
  file_type?: ResumeFormat;
  file_format: ResumeFormat;
  mime_type: string;
  file_size: number;
  extracted_text: string | null;
  processing_status: ResumeProcessingStatus;
  processing_message: string | null;
  requires_ocr: boolean;
  ai_status: ResumeAIStatus;
  approved_version_id: string | null;
  overall_quality_score: number | null;
  associated_preferences: AssociatedPreferenceSummary[];
  upload_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ResumeUpdatePayload {
  resume_name?: string;
  preference_ids?: string[];
}

export interface AIProviderStatus {
  configured: boolean;
  provider: string;
  model: string;
  fallback_model?: string | null;
  setup_message: string | null;
}

export interface CandidateProfileSummary {
  full_name: string | null;
  headline: string | null;
  location: string | null;
  years_of_experience: string | null;
  contact_channels_present: string[];
  summary_evaluation: string;
}

export interface EducationItem {
  degree: string;
  institution: string | null;
  graduation_year: string | null;
  details: string | null;
}

export interface ExperienceItem {
  role: string;
  company: string | null;
  duration: string | null;
  key_contributions: string[];
}

export interface ProjectItem {
  title: string;
  technologies: string[];
  summary: string;
  impact: string | null;
}

export interface PreferenceAnalysisItem {
  preference_id: string;
  preference_name: string;
  target_roles: string[];
  preference_relevance_score: number;
  score_explanation: string;
  relevant_skills: string[];
  relevant_projects: string[];
  experience_alignment: string;
  missing_relevant_keywords: string[];
  missing_keywords_note: string;
  strengths: string[];
  weaknesses: string[];
  improvement_opportunities: string[];
}

export interface ResumeSuggestionItem {
  id: string;
  resume_id: string;
  analysis_id: string | null;
  section_name: string;
  current_content: string | null;
  suggested_improvement: string;
  user_edited_content: string | null;
  effective_content: string;
  reason: string;
  priority: SuggestionPriority;
  clarifying_question: string | null;
  status: SuggestionStatus;
  created_at: string;
  updated_at: string;
}

export interface ResumeAnalysisData {
  id: string;
  resume_id: string;
  provider: string;
  model_name: string;
  candidate_profile: CandidateProfileSummary;
  education: EducationItem[];
  technical_skills: string[];
  soft_skills: string[];
  work_experience: ExperienceItem[];
  internships: ExperienceItem[];
  projects: ProjectItem[];
  certifications: string[];
  achievements: string[];
  tools_and_technologies: string[];
  preference_analyses: PreferenceAnalysisItem[];
  overall_quality_score: number;
  preference_relevance_score: number;
  skills_alignment_score: number;
  experience_alignment_score: number;
  project_relevance_score: number;
  ats_readability_score: number;
  score_explanations: Record<string, string>;
  score_disclaimer: string;
  missing_keywords_disclaimer: string;
  overall_strengths: string[];
  overall_weaknesses: string[];
  missing_information_questions: string[];
  suggestions: ResumeSuggestionItem[];
  created_at: string;
  updated_at: string;
}

export interface SectionComparisonItem {
  section_name: string;
  original_content: string;
  suggested_content: string;
  final_content?: string | null;
  reason?: string | null;
  status?: SuggestionStatus;
}

export interface ResumeVersionItem {
  id: string;
  parent_resume_id: string;
  version_number: number;
  version_type: string;
  title: string;
  content: string;
  section_changes: SectionComparisonItem[];
  target_preference_ids: string[];
  approval_status: string;
  approved_at: string | null;
  creation_date: string;
  created_at: string;
  updated_at: string;
}

export interface ApproveResumeVersionResponse {
  resume_id: string;
  ai_status: ResumeAIStatus;
  approved_version: ResumeVersionItem;
  linked_preference_ids: string[];
  message: string;
}

export const MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
}

export function formatUploadDate(isoDate: string): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(isoDate));
  } catch {
    return isoDate;
  }
}
