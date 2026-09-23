# Event Contract Specification

**Document Version:** 1.0.0  
**Status:** Canonical Interface Definition  
**Last Updated:** Phase 0 (Foundation)

---

## 1. Overview & Architecture

Events in the AI DevOps Assistant represent state transitions across the platform lifecycle: code changes, automated reviews, test runs, deployments, health monitor alerts, incidents, diagnoses, and automated rollbacks.

### Event System Guarantees:
1. **Modular Monolith Delivery:** Events are published to an internal event dispatcher and persisted in PostgreSQL as an append-only event log.
2. **Schema Uniformity:** Every event conforms to the canonical `EventEnvelope`.
3. **Traceability:** Every event carries a `trace_id` allowing end-to-end tracing across pull requests, tests, deployments, and incidents.
4. **Idempotency:** Subscribers deduplicate events using `event_id`.

---

## 2. Canonical Event Envelope

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EventEnvelope",
  "type": "object",
  "required": [
    "event_id",
    "event_type",
    "version",
    "timestamp_utc",
    "trace_id",
    "project_id",
    "actor",
    "payload"
  ],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for this specific event."
    },
    "event_type": {
      "type": "string",
      "description": "Discriminator enum matching one of the canonical event types."
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "default": "1.0"
    },
    "timestamp_utc": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp when the event was emitted."
    },
    "trace_id": {
      "type": "string",
      "format": "uuid",
      "description": "Correlates all actions triggered across this operational lifecycle."
    },
    "project_id": {
      "type": "string",
      "description": "DevOps Assistant project identifier."
    },
    "actor": {
      "type": "object",
      "required": ["id", "type"],
      "properties": {
        "id": { "type": "string" },
        "type": {
          "type": "string",
          "enum": ["USER", "AGENT", "SYSTEM", "WEBHOOK", "HEALTH_MONITOR"]
        }
      }
    },
    "payload": {
      "type": "object",
      "description": "Typed data specific to the event_type."
    }
  }
}
```

---

## 3. Canonical Event Types & Payloads

### 3.1 Code & Review Lifecycle

#### `PR_OPENED`
- **Description:** A new pull request has been opened on GitHub.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["pull_number", "title", "author", "base_ref", "head_ref", "head_sha"],
    "properties": {
      "pull_number": { "type": "integer" },
      "title": { "type": "string" },
      "author": { "type": "string" },
      "base_ref": { "type": "string" },
      "head_ref": { "type": "string" },
      "head_sha": { "type": "string" }
    }
  }
  ```

#### `PR_UPDATED`
- **Description:** New commits pushed or branch force-updated on an open PR.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["pull_number", "previous_head_sha", "new_head_sha"],
    "properties": {
      "pull_number": { "type": "integer" },
      "previous_head_sha": { "type": "string" },
      "new_head_sha": { "type": "string" }
    }
  }
  ```

#### `REVIEW_STARTED`
- **Description:** AI Agent review process triggered for a pull request.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["pull_number", "head_sha", "review_run_id"],
    "properties": {
      "pull_number": { "type": "integer" },
      "head_sha": { "type": "string" },
      "review_run_id": { "type": "string", "format": "uuid" }
    }
  }
  ```

#### `REVIEW_COMPLETED`
- **Description:** AI Agent review completed with findings and risk evaluation.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["pull_number", "head_sha", "review_run_id", "overall_risk", "findings_count", "verdict"],
    "properties": {
      "pull_number": { "type": "integer" },
      "head_sha": { "type": "string" },
      "review_run_id": { "type": "string", "format": "uuid" },
      "overall_risk": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
      "findings_count": { "type": "integer" },
      "verdict": { "type": "string", "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"] }
    }
  }
  ```

---

### 3.2 Testing Lifecycle

#### `TEST_STARTED`
- **Description:** Test runner dispatched.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["test_run_id", "commit_sha", "suite_name"],
    "properties": {
      "test_run_id": { "type": "string", "format": "uuid" },
      "commit_sha": { "type": "string" },
      "suite_name": { "type": "string" }
    }
  }
  ```

#### `TEST_COMPLETED`
- **Description:** Test runner completed execution.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["test_run_id", "commit_sha", "passed", "total_tests", "failed_tests", "duration_seconds"],
    "properties": {
      "test_run_id": { "type": "string", "format": "uuid" },
      "commit_sha": { "type": "string" },
      "passed": { "type": "boolean" },
      "total_tests": { "type": "integer" },
      "failed_tests": { "type": "integer" },
      "duration_seconds": { "type": "number" }
    }
  }
  ```

---

### 3.3 Deployment Lifecycle

#### `DEPLOYMENT_STARTED`
- **Description:** A deployment request has been dispatched to the designated provider adapter.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "target_environment", "provider", "commit_sha"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "target_environment": { "type": "string", "enum": ["staging", "production"] },
      "provider": { "type": "string", "enum": ["vercel", "render", "nebius"] },
      "commit_sha": { "type": "string" }
    }
  }
  ```

#### `DEPLOYMENT_COMPLETED`
- **Description:** Provider finished build and deployment; endpoint is live.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "target_environment", "provider", "url", "duration_seconds"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "target_environment": { "type": "string" },
      "provider": { "type": "string" },
      "url": { "type": "string" },
      "duration_seconds": { "type": "number" }
    }
  }
  ```

#### `DEPLOYMENT_FAILED`
- **Description:** Deployment or build step failed at the provider layer.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "target_environment", "failure_stage", "error_message"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "target_environment": { "type": "string" },
      "failure_stage": { "type": "string", "enum": ["BUILD", "DEPLOY", "CONFIG", "HEALTH_CHECK"] },
      "error_message": { "type": "string" }
    }
  }
  ```

---

### 3.4 Health, Incidents & Recovery Lifecycle

#### `HEALTH_CHECK_FAILED`
- **Description:** Post-deployment synthetic or live health monitor probe failed.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "endpoint", "status_code", "latency_ms", "failure_reason"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "endpoint": { "type": "string" },
      "status_code": { "type": ["integer", "null"] },
      "latency_ms": { "type": "number" },
      "failure_reason": { "type": "string" }
    }
  }
  ```

#### `INCIDENT_CREATED`
- **Description:** Automated incident declared due to failed health check or deployment crash.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "deployment_id", "severity", "title"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "deployment_id": { "type": "string", "format": "uuid" },
      "severity": { "type": "string", "enum": ["SEV1", "SEV2", "SEV3"] },
      "title": { "type": "string" }
    }
  }
  ```

#### `DIAGNOSIS_STARTED`
- **Description:** Agent invoked to analyze logs, diff, and root cause of the incident.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "diagnosis_run_id"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "diagnosis_run_id": { "type": "string", "format": "uuid" }
    }
  }
  ```

#### `DIAGNOSIS_COMPLETED`
- **Description:** Agent finished root cause analysis and formulated remediation plan.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "diagnosis_run_id", "root_cause_summary", "recommended_action"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "diagnosis_run_id": { "type": "string", "format": "uuid" },
      "root_cause_summary": { "type": "string" },
      "recommended_action": { "type": "string", "enum": ["ROLLBACK", "PATCH", "CONFIG_FIX", "HUMAN_ESCALATION"] }
    }
  }
  ```

#### `ROLLBACK_STARTED`
- **Description:** Platform or agent initiated rollback to previous stable deployment.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "deployment_id", "target_stable_version"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "deployment_id": { "type": "string", "format": "uuid" },
      "target_stable_version": { "type": "string" }
    }
  }
  ```

#### `ROLLBACK_COMPLETED`
- **Description:** Target environment successfully restored to stable version.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "rollback_id", "restored_version", "duration_seconds"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "rollback_id": { "type": "string", "format": "uuid" },
      "restored_version": { "type": "string" },
      "duration_seconds": { "type": "number" }
    }
  }
  ```

#### `RECOVERY_COMPLETED`
- **Description:** Incident closed, health monitors green, post-mortem stored in project memory.
- **Payload Schema:**
  ```json
  {
    "type": "object",
    "required": ["incident_id", "time_to_recover_seconds", "resolution_strategy"],
    "properties": {
      "incident_id": { "type": "string", "format": "uuid" },
      "time_to_recover_seconds": { "type": "number" },
      "resolution_strategy": { "type": "string" }
    }
  }
  ```
