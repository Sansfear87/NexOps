/**
 * Core type definitions for AI DevOps Assistant Frontend
 * In sync with Canonical Contract Specifications (contracts/)
 */

export type AgentStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'WAITING_FOR_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'TIMED_OUT';

export type DeploymentState =
  | 'PENDING'
  | 'BUILDING'
  | 'TESTING'
  | 'APPROVED'
  | 'DEPLOYING'
  | 'HEALTH_CHECK'
  | 'SUCCESS'
  | 'FAILED'
  | 'ROLLING_BACK'
  | 'ROLLED_BACK';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type ReviewSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'BLOCKER';

export interface ReviewFinding {
  finding_id: string;
  file: string;
  line: number;
  end_line?: number | null;
  category: string;
  severity: ReviewSeverity;
  description: string;
  recommendation: string;
  suggested_diff?: string | null;
  confidence: number;
}

export interface ReviewResult {
  review_id: string;
  pull_number: number;
  head_sha: string;
  summary: string;
  overall_risk: RiskLevel;
  risk_rationale?: string;
  confidence: number;
  verdict: 'APPROVE' | 'REQUEST_CHANGES' | 'COMMENT';
  findings: ReviewFinding[];
}

export interface EventEnvelope<T = Record<string, unknown>> {
  event_id: string;
  event_type: string;
  version: string;
  timestamp_utc: string;
  trace_id: string;
  project_id: string;
  actor: {
    id: string;
    type: 'USER' | 'AGENT' | 'SYSTEM' | 'WEBHOOK' | 'HEALTH_MONITOR';
  };
  payload: T;
}
