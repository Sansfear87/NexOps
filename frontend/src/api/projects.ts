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

// Phase 2: GitHub Connections & Webhooks
export interface GitHubConnection {
  id: string;
  project_id: string;
  owner: string;
  repo_name: string;
  default_branch: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectGitHubPayload {
  owner: string;
  repo_name?: string;
  repo?: string;
  token?: string;
  webhook_secret?: string;
  default_branch?: string;
}

export interface PullRequest {
  id: string;
  connection_id: string;
  number: number;
  title: string;
  state: string;
  author: string;
  base_branch: string;
  head_branch: string;
  head_sha: string;
  additions: number;
  deletions: number;
  changed_files: number;
  created_at: string;
  updated_at: string;
}

export interface PlatformEvent {
  id: string;
  project_id: string;
  event_type: string;
  version: string;
  trace_id: string;
  actor_id: string;
  actor_type: string;
  payload: any;
  created_at: string;
}

export interface AgentExecutionResponse {
  run_id: string;
  trace_id: string;
  project_id: string;
  goal: string;
  status: string;
  confidence: number;
  actions_taken: any[];
  output_data?: any;
  created_at: string;
}

export async function listGitHubConnections(projectId: string): Promise<GitHubConnection[]> {
  return apiFetch<GitHubConnection[]>(`/projects/${projectId}/github/connections`, {
    method: 'GET'
  });
}

export async function connectGitHub(
  projectId: string,
  payload: ConnectGitHubPayload
): Promise<GitHubConnection> {
  return apiFetch<GitHubConnection>(`/projects/${projectId}/github/connect`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listPullRequests(projectId: string): Promise<PullRequest[]> {
  return apiFetch<PullRequest[]>(`/projects/${projectId}/github/pulls`, {
    method: 'GET'
  });
}

export async function listPlatformEvents(projectId: string): Promise<PlatformEvent[]> {
  return apiFetch<PlatformEvent[]>(`/projects/${projectId}/events`, {
    method: 'GET'
  });
}

export async function executeAgentReview(
  projectId: string,
  pullNumber: number,
  goal?: string
): Promise<AgentExecutionResponse> {
  return apiFetch<AgentExecutionResponse>(`/projects/${projectId}/agent/execute`, {
    method: 'POST',
    body: JSON.stringify({
      pull_number: pullNumber,
      goal: goal || `Perform automated security and code review for PR #${pullNumber}`
    })
  });
}

