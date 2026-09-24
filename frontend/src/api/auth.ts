import { apiFetch, setStoredToken, clearStoredToken } from './client';

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  user: User;
  session_token: string;
  token_type: string;
  expires_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
  if (data.session_token) {
    setStoredToken(data.session_token);
  }
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
  if (data.session_token) {
    setStoredToken(data.session_token);
  }
  return data;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } finally {
    clearStoredToken();
  }
}

export async function getMe(): Promise<User> {
  return apiFetch<User>('/auth/me', { method: 'GET' });
}
