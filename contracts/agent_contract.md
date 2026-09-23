# Agent Contract Specification

**Document Version:** 1.0.0  
**Status:** Canonical Interface Definition  
**Last Updated:** Phase 0 (Foundation)

---

## 1. Overview & Architectural Boundaries

The Agent subsystem is an isolated execution engine responsible for reasoning, plan formulation, and tool selection. It operates strictly as an untrusted or constrained component within the platform.

### Strict Boundary Rules
- **No Direct Database Access:** The agent must never connect to PostgreSQL or any persistent datastore directly.
- **No Direct Cloud or Provider SDK Access:** The agent must never invoke the GitHub API, Vercel API, Render API, Nebius AI Cloud API, or run shell commands directly.
- **No Secret Access:** The agent must never receive raw credentials, API keys, tokens, or encryption secrets. All operations requiring privileges are performed by Platform Services on behalf of the agent through validated tool executions.
- **Contract Enforcement:** All communication between the Platform and the Agent must strictly adhere to the data structures defined in this contract.

```
+-------------------------------------------------------+
|                      AGENT RUNTIME                    |
|                                                       |
|  [Planner / LLM Reasoning] (DeepSeek / Nemotron)      |
|                         |                             |
|                         v                             |
|                   AgentContract                       |
+-------------------------|-----------------------------+
                          |
             Controlled Tool Invocations
                          |
+-------------------------v-----------------------------+
|                     PLATFORM                          |
|                                                       |
|  [Tool Registry] -> [Permission Guard] -> [Audit Log] |
|                         |                             |
|                         v                             |
|                 [Platform Services]                   |
|     (PostgreSQL, GitHub API, Deployment Adapters)     |
+-------------------------------------------------------+
```

---

## 2. Core Execution Interface

The conceptual interface exposed by the Agent Runtime to the Platform is:

```python
agent.run(
    goal: str,
    context: AgentContext,
    tools: List[ToolDefinition],
    permissions: List[Permission]
) -> AgentResult
```

The runtime executes an iterative loop:
1. Observe context and current state.
2. Select an action (`AgentAction`) using available and permitted tools.
3. Yield action to the Platform for validation and execution.
4. Receive tool result from Platform.
5. Terminate when the goal is achieved, an irrecoverable failure occurs, or human approval is needed.

---

## 3. Data Shapes & Schemas

### 3.1 `AgentStatus` (Enum)

Represents the state of an agent execution run:

```json
{
  "type": "string",
  "enum": [
    "PENDING",
    "RUNNING",
    "WAITING_FOR_APPROVAL",
    "COMPLETED",
    "FAILED",
    "TIMED_OUT"
  ]
}
```

- `PENDING`: Request received, queued for agent dispatch.
- `RUNNING`: Agent actively reasoning or waiting for tool execution results.
- `WAITING_FOR_APPROVAL`: Agent proposed a high-risk action requiring human confirmation.
- `COMPLETED`: Goal successfully accomplished.
- `FAILED`: Execution terminated due to unresolvable errors or budget exhaustion.
- `TIMED_OUT`: Run exceeded maximum allowed execution duration.

---

### 3.2 `AgentContext` (Data Shape)

Contextual metadata passed by the Platform into `agent.run`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentContext",
  "type": "object",
  "required": [
    "trace_id",
    "run_id",
    "project_id",
    "repository",
    "environment",
    "initiated_at",
    "permissions"
  ],
  "properties": {
    "trace_id": {
      "type": "string",
      "format": "uuid",
      "description": "Global distributed tracing ID spanning the entire lifecycle."
    },
    "run_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for this specific agent execution attempt."
    },
    "project_id": {
      "type": "string",
      "description": "Identifier of the target project within the DevOps platform."
    },
    "repository": {
      "type": "object",
      "required": ["owner", "name", "default_branch"],
      "properties": {
        "owner": { "type": "string" },
        "name": { "type": "string" },
        "default_branch": { "type": "string" },
        "current_ref": { "type": "string" }
      }
    },
    "actor": {
      "type": "object",
      "required": ["id", "type"],
      "properties": {
        "id": { "type": "string" },
        "type": { "type": "string", "enum": ["USER", "SYSTEM", "WEBHOOK", "SCHEDULE"] }
      }
    },
    "environment": {
      "type": "string",
      "enum": ["development", "staging", "production"],
      "description": "Target deployment environment."
    },
    "initiated_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp of execution start."
    },
    "permissions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of explicit permission tokens granted for this run."
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true,
      "description": "Arbitrary non-sensitive context (e.g. pull_request_id, incident_id)."
    }
  }
}
```

---

### 3.3 `AgentRequest` (Data Shape)

The complete invocation envelope delivered to the agent:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentRequest",
  "type": "object",
  "required": ["goal", "context", "available_tools", "permissions"],
  "properties": {
    "goal": {
      "type": "string",
      "description": "Natural language or structured objective (e.g., 'Review PR #42 and evaluate deployment safety')."
    },
    "context": {
      "$ref": "#/definitions/AgentContext"
    },
    "available_tools": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of tool names registered and accessible to this agent run."
    },
    "permissions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Permission grants active for this request."
    },
    "constraints": {
      "type": "object",
      "properties": {
        "max_steps": { "type": "integer", "default": 20 },
        "timeout_seconds": { "type": "integer", "default": 300 },
        "require_human_approval_for": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of tool names or action types requiring manual confirmation."
        }
      }
    }
  }
}
```

---

### 3.4 `AgentAction` (Data Shape)

A discrete step proposed by the agent to be executed by the platform:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentAction",
  "type": "object",
  "required": ["action_id", "tool_name", "parameters", "rationale", "timestamp"],
  "properties": {
    "action_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for this action step."
    },
    "tool_name": {
      "type": "string",
      "description": "Namespaced tool name (e.g., 'github.get_diff', 'deployment.deploy')."
    },
    "parameters": {
      "type": "object",
      "description": "Arguments matching the input schema of the tool."
    },
    "rationale": {
      "type": "string",
      "description": "Agent's internal reasoning explaining why this tool is invoked."
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "type": "string",
      "enum": ["PROPOSED", "APPROVED", "EXECUTING", "COMPLETED", "REJECTED", "FAILED"],
      "default": "PROPOSED"
    },
    "result": {
      "type": ["object", "null"],
      "description": "Tool execution result provided back to the agent by the platform."
    }
  }
}
```

---

### 3.5 `AgentResult` (Data Shape)

The final response returned by the agent upon run termination:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentResult",
  "type": "object",
  "required": [
    "run_id",
    "trace_id",
    "status",
    "confidence",
    "actions_taken",
    "output"
  ],
  "properties": {
    "run_id": { "type": "string", "format": "uuid" },
    "trace_id": { "type": "string", "format": "uuid" },
    "status": {
      "type": "string",
      "enum": ["COMPLETED", "FAILED", "WAITING_FOR_APPROVAL", "TIMED_OUT"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Self-assessed confidence score of the outcome (0.0 to 1.0)."
    },
    "actions_taken": {
      "type": "array",
      "items": { "$ref": "#/definitions/AgentAction" },
      "description": "Chronological audit log of all actions proposed and executed."
    },
    "output": {
      "type": "object",
      "description": "Domain-specific payload (e.g., ReviewResult, DeploymentDecision)."
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "type": { "type": "string" },
          "uri": { "type": "string" }
        }
      }
    },
    "error": {
      "type": ["object", "null"],
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "details": { "type": "object" }
      }
    },
    "metrics": {
      "type": "object",
      "properties": {
        "duration_ms": { "type": "integer" },
        "steps_count": { "type": "integer" },
        "tokens_consumed": { "type": "integer" }
      }
    }
  }
}
```

---

## 4. Permissions Model

Permissions dictate what tools and environments the agent may access:

| Permission Name | Description |
|-----------------|-------------|
| `repo:read` | Read repository contents, branches, commits, PR metadata, and diffs |
| `repo:write` | Post PR comments, update review status |
| `test:execute` | Trigger isolated test runs |
| `deploy:staging` | Trigger or rollback deployments to staging environment |
| `deploy:production` | Trigger or rollback deployments to production environment |
| `incident:manage` | Open incident records, update incident status, trigger automated remediation |
| `memory:read` | Query short-term, conversation, and project memory stores |
| `memory:write` | Write structured lessons or post-mortem summaries into project memory |

If an agent attempts to invoke a tool for which `permissions` lacks the required grant, the Platform rejects the action with a `PERMISSION_DENIED` error and the action is recorded in the audit log.
