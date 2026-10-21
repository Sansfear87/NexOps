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



export interface ReviewFinding {
  finding_id: string;
  file: string;
  line: number;
  end_line?: number;
  category: 'SECURITY' | 'BUG' | 'PERFORMANCE' | 'ARCHITECTURE' | 'STYLE' | 'TESTING' | 'DEVOPS';
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'BLOCKER';
  description: string;
  recommendation: string;
  suggested_diff?: string;
  confidence: number;
}

export interface ReviewResult {
  review_id: string;
  pull_number: number;
  head_sha: string;
  summary: string;
  overall_risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_rationale?: string;
  confidence: number;
  verdict: 'APPROVE' | 'REQUEST_CHANGES' | 'COMMENT';
  findings: ReviewFinding[];
  metadata?: {
    files_analyzed_count: number;
    lines_added_count: number;
    lines_deleted_count: number;
    duration_ms: number;
    model_used: string;
  };
}

export interface TestCaseResult {
  id: string;
  test_case_name: string;
  status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'ERROR';
  duration_ms?: number;
  error_message?: string;
}

export interface TestRun {
  id: string;
  project_id: string;
  pull_request_id?: string;
  commit_sha: string;
  suite_name: string;
  status: 'PENDING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT';
  passed: boolean;
  total_tests: number;
  failed_tests: number;
  duration_seconds: number;
  summary_output?: string;
  started_at: string;
  completed_at?: string;
  results: TestCaseResult[];
}

export async function triggerAIReview(
  projectId: string,
  pullNumber: number,
  postToGitHub: boolean = false
): Promise<ReviewResult> {
  return apiFetch<ReviewResult>(`/projects/${projectId}/github/pulls/${pullNumber}/review`, {
    method: 'POST',
    body: JSON.stringify({
      pull_number: pullNumber,
      post_to_github: postToGitHub
    })
  });
}

export async function listPRReviews(
  projectId: string,
  pullNumber: number
): Promise<ReviewResult[]> {
  return apiFetch<ReviewResult[]>(`/projects/${projectId}/github/pulls/${pullNumber}/reviews`, {
    method: 'GET'
  });
}

export async function listProjectReviews(
  projectId: string
): Promise<ReviewResult[]> {
  return apiFetch<ReviewResult[]>(`/projects/${projectId}/reviews`, {
    method: 'GET'
  });
}

export async function triggerTestRun(
  projectId: string,
  pullNumber?: number,
  suiteName: string = 'unit'
): Promise<TestRun> {
  return apiFetch<TestRun>(`/projects/${projectId}/tests/run`, {
    method: 'POST',
    body: JSON.stringify({
      pull_number: pullNumber,
      suite_name: suiteName
    })
  });
}

export async function listTestRuns(
  projectId: string,
  pullNumber?: number
): Promise<TestRun[]> {
  const query = pullNumber ? `?pull_number=${pullNumber}` : '';
  return apiFetch<TestRun[]>(`/projects/${projectId}/tests/runs${query}`, {
    method: 'GET'
  });
}
