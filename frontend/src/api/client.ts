/**
 * Base HTTP API client for AI DevOps Assistant Frontend.
 * Communicates with FastAPI backend; never communicates directly with database.
 */

const API_BASE = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem('nexops_session_token');
}

export function setStoredToken(token: string): void {
  localStorage.setItem('nexops_session_token', token);
}

export function clearStoredToken(): void {
  localStorage.removeItem('nexops_session_token');
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const token = getStoredToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      // Use statusText fallback
    }
    throw new ApiError(response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}
