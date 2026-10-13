import { apiFetch } from './client';
import { User } from './auth';

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: string;
  created_at: string;
  user?: User;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  owner_id: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  owner?: User;
  members: ProjectMember[];
}

export interface CreateProjectPayload {
  name: string;
  slug: string;
  description?: string;
}

export interface ProjectMemberCreatePayload {
  email: string;
  role: string;
}

export interface ProjectMemberUpdatePayload {
  role: string;
}

export interface APIKeyResponse {
  id: string;
  project_id: string;
  user_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface APIKeyCreated extends APIKeyResponse {
  raw_key: string;
}

export interface APIKeyCreatePayload {
  name: string;
  expires_in_days?: number | null;
  scopes?: string[];
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listProjects(): Promise<Project[]> {
  return apiFetch<Project[]>('/projects', {
    method: 'GET'
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return apiFetch<Project>(`/projects/${projectId}`, {
    method: 'GET'
  });
}

export async function deleteProject(projectId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/projects/${projectId}`, {
    method: 'DELETE'
  });
}

// Phase 1: Team Member RBAC Management
export async function listMembers(projectId: string): Promise<ProjectMember[]> {
  return apiFetch<ProjectMember[]>(`/projects/${projectId}/members`, {
    method: 'GET'
  });
}

export async function addMember(projectId: string, payload: ProjectMemberCreatePayload): Promise<ProjectMember> {
  return apiFetch<ProjectMember>(`/projects/${projectId}/members`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateMemberRole(
  projectId: string,
  userId: string,
  payload: ProjectMemberUpdatePayload
): Promise<ProjectMember> {
  return apiFetch<ProjectMember>(`/projects/${projectId}/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function removeMember(projectId: string, userId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/projects/${projectId}/members/${userId}`, {
    method: 'DELETE'
  });
}

// Phase 1: API Key Lifecycle Management
export async function listApiKeys(projectId: string): Promise<APIKeyResponse[]> {
  return apiFetch<APIKeyResponse[]>(`/projects/${projectId}/api-keys`, {
    method: 'GET'
  });
}

export async function createApiKey(projectId: string, payload: APIKeyCreatePayload): Promise<APIKeyCreated> {
  return apiFetch<APIKeyCreated>(`/projects/${projectId}/api-keys`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function revokeApiKey(projectId: string, keyId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/projects/${projectId}/api-keys/${keyId}`, {
    method: 'DELETE'
  });
}
