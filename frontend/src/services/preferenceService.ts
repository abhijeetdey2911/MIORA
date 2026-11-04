import type { JobPreference, JobPreferencePayload } from '../types/preference';

const RAW_URL = import.meta.env.VITE_API_URL;
const BACKEND_BASE_URL = typeof RAW_URL === 'string' ? RAW_URL.replace(/\/+$/, '') : '';
const PREFERENCES_API_URL = `${BACKEND_BASE_URL}/api/v1/preferences`;

interface BackendErrorDetail {
  loc?: (string | number)[];
  msg?: string;
}

interface BackendErrorBody {
  message?: string;
  detail?: string | BackendErrorDetail[];
  details?: BackendErrorDetail[];
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as BackendErrorBody;
    const validationList =
      body.details ?? (Array.isArray(body.detail) ? body.detail : undefined);
    if (validationList && validationList.length > 0) {
      const first = validationList[0];
      const cleanedMsg = (first.msg ?? 'Invalid input').replace(/^Value error,\s*/i, '');
      return cleanedMsg;
    }
    if (typeof body.message === 'string' && body.message) {
      return body.message;
    }
    if (typeof body.detail === 'string' && body.detail) {
      return body.detail;
    }
  } catch {
    // Ignore JSON parse errors and fallback to status text
  }
  return `Request failed with status ${response.status}`;
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

export async function getPreferences(): Promise<JobPreference[]> {
  return requestJson<JobPreference[]>(PREFERENCES_API_URL);
}

export async function getPreferenceById(id: string): Promise<JobPreference> {
  return requestJson<JobPreference>(`${PREFERENCES_API_URL}/${encodeURIComponent(id)}`);
}

export async function createPreference(
  payload: JobPreferencePayload,
): Promise<JobPreference> {
  return requestJson<JobPreference>(PREFERENCES_API_URL, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updatePreference(
  id: string,
  payload: JobPreferencePayload,
): Promise<JobPreference> {
  return requestJson<JobPreference>(`${PREFERENCES_API_URL}/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function updatePreferenceStatus(
  id: string,
  isActive: boolean,
): Promise<JobPreference> {
  return requestJson<JobPreference>(
    `${PREFERENCES_API_URL}/${encodeURIComponent(id)}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    },
  );
}

export async function deletePreference(
  id: string,
): Promise<{ message: string; id: string }> {
  return requestJson<{ message: string; id: string }>(
    `${PREFERENCES_API_URL}/${encodeURIComponent(id)}`,
    {
      method: 'DELETE',
    },
  );
}

