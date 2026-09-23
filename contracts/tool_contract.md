# Tool Contract Specification

**Document Version:** 1.0.0  
**Status:** Canonical Interface Definition  
**Last Updated:** Phase 0 (Foundation)

---

## 1. Overview & Boundary Principles

Tools are the single, strictly controlled bridge connecting the Agent Runtime to Platform capabilities and external infrastructure.

### Boundary Guarantees:
1. **Zero Direct Access:** The agent never calls GitHub, Vercel, Render, Nebius, or the database directly. It requests tool executions by name and parameters.
2. **Schema Validation:** All tool arguments and return values are strictly validated against JSON Schemas before and after execution.
3. **Permission Enforcement:** The Platform intercepts every tool invocation and verifies that the active `AgentContext` possesses all required permissions.
4. **Auditability:** Every tool invocation creates an immutable audit record containing input hashes, execution duration, invoker metadata, and outputs.
5. **Fault Isolation:** Tool errors are normalized into a deterministic error schema with clear retry semantics (`retryable` boolean).

---

## 2. Standard Tool Definition Schema

Every tool registered in the Platform's Tool Registry must satisfy the following specification:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ToolDefinition",
  "type": "object",
  "required": [
    "name",
    "version",
    "description",
    "input_schema",
    "output_schema",
    "required_permissions",
    "timeout_seconds"
  ],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z_]+(\\.[a-z_]+)+$",
      "description": "Namespaced identifier, e.g., 'github.get_pull_request'"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "description": {
      "type": "string",
      "description": "Clear documentation for the agent describing when and how to use the tool."
    },
    "input_schema": {
      "type": "object",
      "description": "JSON Schema (Draft 2020-12) validating tool input parameters."
    },
    "output_schema": {
      "type": "object",
      "description": "JSON Schema (Draft 2020-12) validating tool output structure."
    },
    "required_permissions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of permission strings required to execute this tool."
    },
    "timeout_seconds": {
      "type": "integer",
      "default": 30,
      "description": "Maximum allowed wall-clock execution time before cancellation."
    },
    "is_side_effect_free": {
      "type": "boolean",
      "default": false,
      "description": "True if idempotent and read-only; false if it mutates state."
    }
  }
}
```

---

## 3. Tool Execution Response & Error Structure

All tool executions produce a normalized `ToolExecutionEnvelope`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ToolExecutionEnvelope",
  "type": "object",
  "required": ["execution_id", "tool_name", "status", "audit"],
  "properties": {
    "execution_id": { "type": "string", "format": "uuid" },
    "tool_name": { "type": "string" },
    "status": {
      "type": "string",
      "enum": ["SUCCESS", "FAILED", "TIMED_OUT", "PERMISSION_DENIED"]
    },
    "data": {
      "type": ["object", "null"],
      "description": "Output payload matching tool's output_schema if status is SUCCESS."
    },
    "error": {
      "type": ["object", "null"],
      "description": "Error details if status is not SUCCESS.",
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "INVALID_INPUT",
            "PERMISSION_DENIED",
            "RESOURCE_NOT_FOUND",
            "RATE_LIMITED",
            "PROVIDER_UNAVAILABLE",
            "EXECUTION_TIMEOUT",
            "INTERNAL_ERROR"
          ]
        },
        "message": { "type": "string" },
        "retryable": {
          "type": "boolean",
          "description": "Indicates whether the agent can safely retry this action."
        },
        "details": { "type": "object" }
      },
      "required": ["code", "message", "retryable"]
    },
    "audit": {
      "type": "object",
      "required": ["trace_id", "run_id", "invoker_id", "timestamp_utc", "duration_ms"],
      "properties": {
        "trace_id": { "type": "string", "format": "uuid" },
        "run_id": { "type": "string", "format": "uuid" },
        "invoker_id": { "type": "string" },
        "timestamp_utc": { "type": "string", "format": "date-time" },
        "duration_ms": { "type": "integer" },
        "parameters_hash": { "type": "string" }
      }
    }
  }
}
```

---

## 4. Standard Core Tools Catalog

### 4.1 `github.get_repository`
- **Description:** Retrieve repository metadata and configuration.
- **Required Permissions:** `["repo:read"]`
- **Timeout:** 15 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["owner", "repo"],
    "properties": {
      "owner": { "type": "string" },
      "repo": { "type": "string" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["id", "full_name", "default_branch", "is_private"],
    "properties": {
      "id": { "type": "integer" },
      "full_name": { "type": "string" },
      "default_branch": { "type": "string" },
      "is_private": { "type": "boolean" },
      "description": { "type": ["string", "null"] }
    }
  }
  ```

---

### 4.2 `github.get_pull_request`
- **Description:** Retrieve metadata, author, branches, and state for a pull request.
- **Required Permissions:** `["repo:read"]`
- **Timeout:** 15 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["owner", "repo", "pull_number"],
    "properties": {
      "owner": { "type": "string" },
      "repo": { "type": "string" },
      "pull_number": { "type": "integer" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["id", "number", "title", "state", "base_branch", "head_branch", "head_sha"],
    "properties": {
      "id": { "type": "integer" },
      "number": { "type": "integer" },
      "title": { "type": "string" },
      "body": { "type": ["string", "null"] },
      "state": { "type": "string", "enum": ["open", "closed", "merged"] },
      "base_branch": { "type": "string" },
      "head_branch": { "type": "string" },
      "head_sha": { "type": "string" }
    }
  }
  ```

---

### 4.3 `github.get_diff`
- **Description:** Retrieve the unified diff or per-file changes of a pull request.
- **Required Permissions:** `["repo:read"]`
- **Timeout:** 30 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["owner", "repo", "pull_number"],
    "properties": {
      "owner": { "type": "string" },
      "repo": { "type": "string" },
      "pull_number": { "type": "integer" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["files"],
    "properties": {
      "files": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["filename", "status", "additions", "deletions", "patch"],
          "properties": {
            "filename": { "type": "string" },
            "status": { "type": "string", "enum": ["added", "modified", "removed", "renamed"] },
            "additions": { "type": "integer" },
            "deletions": { "type": "integer" },
            "patch": { "type": "string" }
          }
        }
      }
    }
  }
  ```

---

### 4.4 `tests.run`
- **Description:** Trigger an automated test suite execution in a sandboxed runner.
- **Required Permissions:** `["test:execute"]`
- **Timeout:** 180 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["project_id", "commit_sha"],
    "properties": {
      "project_id": { "type": "string" },
      "commit_sha": { "type": "string" },
      "test_suite": { "type": "string", "default": "unit" },
      "environment_vars": { "type": "object", "additionalProperties": { "type": "string" } }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["run_id", "exit_code", "passed", "total_tests", "failed_tests", "duration_seconds"],
    "properties": {
      "run_id": { "type": "string", "format": "uuid" },
      "exit_code": { "type": "integer" },
      "passed": { "type": "boolean" },
      "total_tests": { "type": "integer" },
      "failed_tests": { "type": "integer" },
      "duration_seconds": { "type": "number" },
      "summary_output": { "type": "string" }
    }
  }
  ```

---

### 4.5 `deployment.deploy`
- **Description:** Initiate a deployment via the unified provider abstraction.
- **Required Permissions:** `["deploy:staging"]` or `["deploy:production"]`
- **Timeout:** 60 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["project_id", "target_environment", "commit_sha", "provider"],
    "properties": {
      "project_id": { "type": "string" },
      "target_environment": { "type": "string", "enum": ["staging", "production"] },
      "commit_sha": { "type": "string" },
      "provider": { "type": "string", "enum": ["vercel", "render", "nebius"] },
      "configuration": { "type": "object" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "status", "provider_reference_id"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "status": { "type": "string", "enum": ["PENDING", "BUILDING", "DEPLOYING"] },
      "provider_reference_id": { "type": "string" },
      "url": { "type": ["string", "null"] }
    }
  }
  ```

---

### 4.6 `deployment.status`
- **Description:** Query current deployment status and health checks.
- **Required Permissions:** `["repo:read"]`
- **Timeout:** 15 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "state", "updated_at"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "state": {
        "type": "string",
        "enum": [
          "PENDING", "BUILDING", "TESTING", "APPROVED", "DEPLOYING",
          "HEALTH_CHECK", "SUCCESS", "FAILED", "ROLLING_BACK", "ROLLED_BACK"
        ]
      },
      "url": { "type": ["string", "null"] },
      "updated_at": { "type": "string", "format": "date-time" }
    }
  }
  ```

---

### 4.7 `deployment.logs`
- **Description:** Fetch build, runtime, or health check logs for a deployment.
- **Required Permissions:** `["repo:read"]`
- **Timeout:** 30 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "tail": { "type": "integer", "default": 100 }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "logs"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "logs": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["timestamp", "stream", "message"],
          "properties": {
            "timestamp": { "type": "string", "format": "date-time" },
            "stream": { "type": "string", "enum": ["stdout", "stderr", "system"] },
            "message": { "type": "string" }
          }
        }
      }
    }
  }
  ```

---

### 4.8 `deployment.rollback`
- **Description:** Safely revert an environment to a previous healthy release.
- **Required Permissions:** `["deploy:staging"]` or `["deploy:production"]`
- **Timeout:** 60 seconds
- **Input Schema:**
  ```json
  {
    "type": "object",
    "required": ["deployment_id", "reason"],
    "properties": {
      "deployment_id": { "type": "string", "format": "uuid" },
      "target_version": { "type": ["string", "null"] },
      "reason": { "type": "string" }
    }
  }
  ```
- **Output Schema:**
  ```json
  {
    "type": "object",
    "required": ["rollback_id", "state", "target_version"],
    "properties": {
      "rollback_id": { "type": "string", "format": "uuid" },
      "state": { "type": "string", "enum": ["ROLLING_BACK", "ROLLED_BACK", "FAILED"] },
      "target_version": { "type": "string" }
    }
  }
  ```
