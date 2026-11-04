import type {
  AIProviderStatus,
  ApproveResumeVersionResponse,
  ResumeAnalysisData,
  ResumeItem,
  ResumeSuggestionItem,
  ResumeUpdatePayload,
  ResumeVersionItem,
  SectionComparisonItem,
  SuggestionStatus,
} from '../types/resume';

const RAW_URL = import.meta.env.VITE_API_URL;
const BACKEND_BASE_URL = typeof RAW_URL === 'string' ? RAW_URL.replace(/\/+$/, '') : '';
const RESUMES_API_URL = `${BACKEND_BASE_URL}/api/v1/resumes`;

interface BackendErrorDetail {
  loc?: (string | number)[];
  msg?: string;
}

interface BackendErrorBody {
  message?: string;
  detail?: string | BackendErrorDetail[];
  details?: BackendErrorDetail[];
}

function extractErrorMessageFromBody(body: BackendErrorBody, status: number): string {
  const validationList =
    body.details ?? (Array.isArray(body.detail) ? body.detail : undefined);
  if (validationList && validationList.length > 0) {
    const first = validationList[0];
    return (first.msg ?? 'Invalid input').replace(/^Value error,\s*/i, '');
  }
  if (typeof body.message === 'string' && body.message) {
    return body.message;
  }
  if (typeof body.detail === 'string' && body.detail) {
    return body.detail;
  }
  return `Request failed with status ${status}`;
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    return extractErrorMessageFromBody(body, response.status);
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new Error(
      'Unable to reach the JobHunter backend server. Please verify the service is running.',
    );
  }

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function getResumes(): Promise<ResumeItem[]> {
  return requestJson<ResumeItem[]>(RESUMES_API_URL);
}

export async function getResumeById(id: string): Promise<ResumeItem> {
  return requestJson<ResumeItem>(`${RESUMES_API_URL}/${encodeURIComponent(id)}`);
}

export interface UploadResumeOptions {
  file: File;
  resumeName?: string;
  preferenceIds?: string[];
  onProgress?: (percent: number) => void;
}

export function uploadResume({
  file,
  resumeName,
  preferenceIds,
  onProgress,
}: UploadResumeOptions): Promise<ResumeItem> {
  return new Promise<ResumeItem>((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (resumeName && resumeName.trim()) {
      formData.append('resume_name', resumeName.trim());
    }
    if (preferenceIds && preferenceIds.length > 0) {
      formData.append('preference_ids', JSON.stringify(preferenceIds));
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', RESUMES_API_URL, true);
    xhr.setRequestHeader('Accept', 'application/json');

    xhr.upload.onprogress = (event: ProgressEvent) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const parsed = JSON.parse(xhr.responseText) as ResumeItem;
          onProgress?.(100);
          resolve(parsed);
        } catch {
          reject(new Error('Invalid response received from backend server.'));
        }
      } else {
        try {
          const errBody = JSON.parse(xhr.responseText) as BackendErrorBody;
          reject(new Error(extractErrorMessageFromBody(errBody, xhr.status)));
        } catch {
          reject(new Error(`Resume upload failed with status ${xhr.status}.`));
        }
      }
    };

    xhr.onerror = () => {
      reject(
        new Error(
          'Network error while uploading resume. Please verify the backend service is running.',
        ),
      );
    };

    xhr.send(formData);
  });
}

export async function updateResume(
  id: string,
  payload: ResumeUpdatePayload,
): Promise<ResumeItem> {
  return requestJson<ResumeItem>(`${RESUMES_API_URL}/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteResume(
  id: string,
): Promise<{ message: string; id: string }> {
  return requestJson<{ message: string; id: string }>(
    `${RESUMES_API_URL}/${encodeURIComponent(id)}`,
    {
      method: 'DELETE',
    },
  );
}

export function getResumeDownloadUrl(id: string): string {
  return `${RESUMES_API_URL}/${encodeURIComponent(id)}/download`;
}

// ==============================================================================
// Phase 3B — AI Resume Intelligence API Client Functions
// ==============================================================================

export async function getAIProviderStatus(): Promise<AIProviderStatus> {
  return requestJson<AIProviderStatus>(`${RESUMES_API_URL}/ai-status`);
}

export async function analyseResume(resumeId: string): Promise<ResumeAnalysisData> {
  return requestJson<ResumeAnalysisData>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/analyse`,
    { method: 'POST' },
  );
}

export async function getResumeAnalysis(resumeId: string): Promise<ResumeAnalysisData> {
  return requestJson<ResumeAnalysisData>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/analysis`,
  );
}

export async function getResumeSuggestions(
  resumeId: string,
): Promise<ResumeSuggestionItem[]> {
  return requestJson<ResumeSuggestionItem[]>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/suggestions`,
  );
}

export async function updateResumeSuggestion(
  resumeId: string,
  suggestionId: string,
  payload: { status?: SuggestionStatus; user_edited_content?: string },
): Promise<ResumeSuggestionItem> {
  return requestJson<ResumeSuggestionItem>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/suggestions/${encodeURIComponent(suggestionId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  );
}

export async function regenerateResumeSuggestion(
  resumeId: string,
  suggestionId: string,
  userInstruction?: string,
): Promise<ResumeSuggestionItem> {
  return requestJson<ResumeSuggestionItem>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/suggestions/${encodeURIComponent(suggestionId)}/regenerate`,
    {
      method: 'POST',
      body: JSON.stringify({ user_instruction: userInstruction || null }),
    },
  );
}

export async function enhanceResumeDraft(
  resumeId: string,
  options?: {
    sections?: string[];
    target_preference_ids?: string[];
    apply_accepted_suggestions?: boolean;
  },
): Promise<ResumeVersionItem> {
  return requestJson<ResumeVersionItem>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/enhance`,
    {
      method: 'POST',
      body: JSON.stringify(options ?? { apply_accepted_suggestions: true }),
    },
  );
}

export async function getResumeVersions(
  resumeId: string,
): Promise<ResumeVersionItem[]> {
  return requestJson<ResumeVersionItem[]>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/versions`,
  );
}

export async function createUserResumeVersion(
  resumeId: string,
  payload: {
    title?: string;
    content: string;
    section_changes?: SectionComparisonItem[];
    target_preference_ids?: string[];
  },
): Promise<ResumeVersionItem> {
  return requestJson<ResumeVersionItem>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/versions`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
}

export async function updateResumeVersion(
  resumeId: string,
  versionId: string,
  payload: {
    title?: string;
    content?: string;
    section_changes?: SectionComparisonItem[];
  },
): Promise<ResumeVersionItem> {
  return requestJson<ResumeVersionItem>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/versions/${encodeURIComponent(versionId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  );
}

export async function approveResumeVersion(
  resumeId: string,
  versionId: string,
  preferenceIds?: string[],
): Promise<ApproveResumeVersionResponse> {
  return requestJson<ApproveResumeVersionResponse>(
    `${RESUMES_API_URL}/${encodeURIComponent(resumeId)}/versions/${encodeURIComponent(versionId)}/approve`,
    {
      method: 'POST',
      body: JSON.stringify({ preference_ids: preferenceIds ?? null }),
    },
  );
}
