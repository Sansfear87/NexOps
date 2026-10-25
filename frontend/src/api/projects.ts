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

// Phase 7: Deployment Guardrails, Risk Gates, and Audit Logs
export interface PolicyRuleResult {
  rule: string;
  passed: boolean;
  score: number;
  detail: string;
}

export interface GateAuditLog {
  id: string;
  gate_id: string;
  action: 'EVALUATED' | 'APPROVAL_REQUESTED' | 'APPROVED' | 'REJECTED' | 'BYPASSED' | 'POLICY_OVERRIDDEN';
  actor_id?: string;
  actor_type: 'USER' | 'AGENT' | 'SYSTEM';
  previous_status?: string;
  new_status: string;
  reason?: string;
  audit_metadata?: Record<string, any>;
  created_at: string;
}

export interface DeploymentGate {
  id: string;
  project_id: string;
  pull_request_id?: string;
  review_id?: string;
  test_run_id?: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  gate_status: 'PASSED' | 'REQUIRES_APPROVAL' | 'APPROVED' | 'REJECTED' | 'BLOCKED' | 'BYPASSED';
  risk_score: number;
  summary: string;
  reasons: string[];
  critical_files: string[];
  policy_evaluations: PolicyRuleResult[];
  approved_by?: string;
  approved_at?: string;
  approval_notes?: string;
  bypass_reason?: string;
  created_at: string;
  updated_at: string;
  audit_logs?: GateAuditLog[];
}

export async function evaluatePRGate(
  projectId: string,
  pullRequestId: string,
  reviewId?: string,
  testRunId?: string
): Promise<DeploymentGate> {
  return apiFetch<DeploymentGate>(`/projects/${projectId}/gates/evaluate`, {
    method: 'POST',
    body: JSON.stringify({
      pull_request_id: pullRequestId,
      review_id: reviewId,
      test_run_id: testRunId
    })
  });
}

export async function listProjectGates(
  projectId: string,
  statusFilter?: string
): Promise<DeploymentGate[]> {
  const query = statusFilter ? `?status=${statusFilter}` : '';
  return apiFetch<DeploymentGate[]>(`/projects/${projectId}/gates${query}`, {
    method: 'GET'
  });
}

export async function getGate(gateId: string): Promise<DeploymentGate> {
  return apiFetch<DeploymentGate>(`/gates/${gateId}`, {
    method: 'GET'
  });
}

export async function approveGate(gateId: string, notes?: string): Promise<DeploymentGate> {
  return apiFetch<DeploymentGate>(`/gates/${gateId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes })
  });
}

export async function rejectGate(gateId: string, reason: string): Promise<DeploymentGate> {
  return apiFetch<DeploymentGate>(`/gates/${gateId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

export async function bypassGate(gateId: string, reason: string): Promise<DeploymentGate> {
  return apiFetch<DeploymentGate>(`/gates/${gateId}/bypass`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

export async function getGateAuditLogs(gateId: string): Promise<GateAuditLog[]> {
  return apiFetch<GateAuditLog[]>(`/gates/${gateId}/audit-logs`, {
    method: 'GET'
  });
}

// -------------------------------------------------------------
// Phase 8: Deployments & Provider Adapters
// -------------------------------------------------------------

export interface DeploymentLog {
  id: string;
  deployment_id: string;
  source: string;
  message: string;
  timestamp: string;
}

export interface Deployment {
  id: string;
  project_id: string;
  pull_request_id?: string | null;
  gate_id?: string | null;
  provider: 'vercel' | 'render' | 'nebius';
  environment: 'staging' | 'production';
  state: 'PENDING' | 'BUILDING' | 'TESTING' | 'APPROVED' | 'DEPLOYING' | 'HEALTH_CHECK' | 'SUCCESS' | 'FAILED' | 'ROLLING_BACK' | 'ROLLED_BACK';
  commit_sha: string;
  branch: string;
  url?: string | null;
  error_summary?: string | null;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  logs?: DeploymentLog[];
}

export interface CreateDeploymentPayload {
  provider: 'vercel' | 'render' | 'nebius';
  environment: 'staging' | 'production';
  commit_sha: string;
  branch?: string;
  pull_request_id?: string | null;
  gate_id?: string | null;
  configuration?: Record<string, any>;
  metadata?: Record<string, any>;
}

export async function createDeployment(
  projectId: string,
  payload: CreateDeploymentPayload
): Promise<Deployment> {
  return apiFetch<Deployment>(`/projects/${projectId}/deployments`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listDeployments(
  projectId: string,
  environment?: string
): Promise<Deployment[]> {
  const query = environment ? `?environment=${environment}` : '';
  return apiFetch<Deployment[]>(`/projects/${projectId}/deployments${query}`, {
    method: 'GET'
  });
}

export async function getDeployment(deploymentId: string): Promise<Deployment> {
  return apiFetch<Deployment>(`/deployments/${deploymentId}`, {
    method: 'GET'
  });
}

export async function getDeploymentLogs(deploymentId: string, tail: number = 100): Promise<DeploymentLog[]> {
  return apiFetch<DeploymentLog[]>(`/deployments/${deploymentId}/logs?tail=${tail}`, {
    method: 'GET'
  });
}

export async function rollbackDeployment(
  deploymentId: string,
  reason: string,
  targetDeploymentId?: string
): Promise<{ rollback_id: string; state: string; target_version: string; message: string }> {
  return apiFetch(`/deployments/${deploymentId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ reason, target_deployment_id: targetDeploymentId })
  });
}

// -------------------------------------------------------------
// Phase 9: Monitoring & Synthetic Probes
// -------------------------------------------------------------

export interface HealthCheck {
  id: string;
  deployment_id: string;
  project_id: string;
  endpoint: string;
  status_code?: number | null;
  latency_ms: number;
  is_healthy: boolean;
  error_message?: string | null;
  created_at: string;
}

export interface HealthMetric {
  id: string;
  deployment_id: string;
  project_id: string;
  metric_name: string;
  value: number;
  unit: string;
  created_at: string;
}

export async function triggerHealthProbe(
  deploymentId: string,
  endpoint: string = '/health'
): Promise<HealthCheck> {
  return apiFetch<HealthCheck>(`/deployments/${deploymentId}/probes`, {
    method: 'POST',
    body: JSON.stringify({ endpoint })
  });
}

export async function listProbes(deploymentId: string): Promise<HealthCheck[]> {
  return apiFetch<HealthCheck[]>(`/deployments/${deploymentId}/probes`, {
    method: 'GET'
  });
}

export async function getDeploymentHealth(deploymentId: string): Promise<Record<string, any>> {
  return apiFetch(`/deployments/${deploymentId}/health`, {
    method: 'GET'
  });
}

// -------------------------------------------------------------
// Phase 10: Incidents & Autonomous Diagnosis
// -------------------------------------------------------------

export interface DiagnosisRun {
  id: string;
  incident_id: string;
  diagnosis_summary: string;
  recommended_action: string;
  suspected_commits: any[];
  logs_analyzed: string[];
  created_at: string;
}

export interface Incident {
  id: string;
  project_id: string;
  deployment_id?: string | null;
  severity: 'SEV1' | 'SEV2' | 'SEV3';
  status: 'OPEN' | 'INVESTIGATING' | 'MITIGATING' | 'RESOLVED' | 'CLOSED';
  title: string;
  description?: string | null;
  root_cause_summary?: string | null;
  recommended_action?: string;
  target_stable_version?: string | null;
  created_at: string;
  resolved_at?: string | null;
  diagnoses?: DiagnosisRun[];
}

export interface CreateIncidentPayload {
  title: string;
  description?: string;
  severity?: 'SEV1' | 'SEV2' | 'SEV3';
  deployment_id?: string | null;
}

export async function createIncident(
  projectId: string,
  payload: CreateIncidentPayload
): Promise<Incident> {
  return apiFetch<Incident>(`/projects/${projectId}/incidents`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listIncidents(
  projectId: string,
  status?: string
): Promise<Incident[]> {
  const query = status ? `?status=${status}` : '';
  return apiFetch<Incident[]>(`/projects/${projectId}/incidents${query}`, {
    method: 'GET'
  });
}

export async function getIncident(incidentId: string): Promise<Incident> {
  return apiFetch<Incident>(`/incidents/${incidentId}`, {
    method: 'GET'
  });
}

export async function diagnoseIncident(incidentId: string): Promise<DiagnosisRun> {
  return apiFetch<DiagnosisRun>(`/incidents/${incidentId}/diagnose`, {
    method: 'POST'
  });
}

export async function resolveIncident(
  incidentId: string,
  rootCauseSummary: string,
  recommendedAction: string = 'ROLLBACK'
): Promise<Incident> {
  return apiFetch<Incident>(`/incidents/${incidentId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ root_cause_summary: rootCauseSummary, recommended_action: recommendedAction })
  });
}

// -------------------------------------------------------------
// Phase 11: Project Persistent Memory
// -------------------------------------------------------------

export interface ProjectMemoryItem {
  id: string;
  project_id: string;
  category: string;
  key: string;
  content: string;
  importance: number;
  metadata?: Record<string, any>;
  access_count: number;
  created_at: string;
  updated_at: string;
}

export async function storeProjectMemory(
  projectId: string,
  payload: { key: string; content: string; category?: string; importance?: number; metadata?: Record<string, any> }
): Promise<ProjectMemoryItem> {
  return apiFetch<ProjectMemoryItem>(`/projects/${projectId}/memory`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function searchProjectMemory(
  projectId: string,
  q?: string,
  category?: string
): Promise<{ items: ProjectMemoryItem[]; total: number }> {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (category) params.set('category', category);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return apiFetch<{ items: ProjectMemoryItem[]; total: number }>(`/projects/${projectId}/memory${qs}`, {
    method: 'GET'
  });
}
