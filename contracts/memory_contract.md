# Memory Contract Specification

**Document Version:** 1.0.0  
**Status:** Canonical Interface Definition  
**Last Updated:** Phase 0 (Foundation)

---

## 1. Overview & Memory Architecture

The AI DevOps Assistant maintains three distinct tiers of memory to provide coherent reasoning across ephemeral actions, ongoing multi-turn conversations/incidents, and long-term project lifecycles.

> [!IMPORTANT]
> **Phase 0 Boundary:** No vector database or semantic embedding search is implemented in Phase 0. The memory subsystem defines structured schemas, access scopes, and retrieval contracts. PostgreSQL-backed relational storage is used initially, with vector embeddings (`pgvector`) deferred to Phase 11.

```
+-------------------------------------------------------------------------+
|                              MEMORY TIERS                               |
+-------------------------------------------------------------------------+
| Tier 1: Short-Term Agent Context                                        |
| - Scope: Single execution run (AgentRequest -> AgentResult)             |
| - Lifetime: Ephemeral in-memory scratchpad during reasoning             |
+-------------------------------------------------------------------------+
| Tier 2: Conversation Memory                                             |
| - Scope: Thread / Session (PR review thread, Incident debugging chat)   |
| - Lifetime: Active session duration (persisted in DB)                   |
+-------------------------------------------------------------------------+
| Tier 3: Project Memory                                                  |
| - Scope: Cross-session persistent organizational knowledge             |
| - Lifetime: Permanent per project (architecture rules, past incidents)  |
+-------------------------------------------------------------------------+
```

---

## 2. Memory Tier Definitions

### 2.1 Tier 1: Short-Term Agent Context
Ephemeral working memory held in the agent runtime during a single invocation. Contains:
- Current step index and maximum steps remaining.
- Scratchpad / Chain-of-thought observations from prior tool executions in the same run.
- Local goal refinement.
- Cleared immediately upon returning `AgentResult`.

### 2.2 Tier 2: Conversation Memory
Maintains message history and interaction state between human operators and the assistant within a specific domain context (e.g., resolving a PR feedback loop or responding to a SEV1 incident alert).
- Retains human inputs, agent responses, clarification questions, and approvals.
- Enables multi-turn dialogue without repeating initial instructions.

### 2.3 Tier 3: Project Memory
Persistent repository knowledge accumulated across multiple runs:
- **Architecture Invariants:** Coding conventions, framework guidelines, forbidden dependencies.
- **Incident Post-Mortems:** Causes of prior outages, mitigation history, flaky test lists.
- **Deployment Constraints:** Peak traffic windows, maintenance blackout schedules.

---

## 3. Data Shapes & Schemas

### 3.1 `MemoryEntry`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MemoryEntry",
  "type": "object",
  "required": [
    "entry_id",
    "tier",
    "project_id",
    "category",
    "content",
    "created_at",
    "metadata"
  ],
  "properties": {
    "entry_id": { "type": "string", "format": "uuid" },
    "tier": {
      "type": "string",
      "enum": ["SHORT_TERM", "CONVERSATION", "PROJECT"]
    },
    "session_id": {
      "type": ["string", "null"],
      "description": "Required for CONVERSATION tier."
    },
    "project_id": { "type": "string" },
    "category": {
      "type": "string",
      "enum": [
        "ARCHITECTURE_RULE",
        "FLAKY_TEST",
        "INCIDENT_POSTMORTEM",
        "DEPLOYMENT_NOTE",
        "USER_PREFERENCE",
        "AGENT_SCRATCHPAD"
      ]
    },
    "content": {
      "type": "string",
      "description": "Textual knowledge or structured Markdown summary."
    },
    "metadata": {
      "type": "object",
      "properties": {
        "source_trace_id": { "type": "string" },
        "author_id": { "type": "string" },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      }
    },
    "created_at": { "type": "string", "format": "date-time" },
    "expires_at": {
      "type": ["string", "null"],
      "description": "Optional TTL timestamp for transient memory entries."
    }
  }
}
```

---

## 4. Memory Interface Contract

The Platform exposes the memory service to agents through the following controlled operations:

### 4.1 Retrieval Contract

```python
class MemoryService(Protocol):
    """Protocol for memory operations accessed via platform tools."""

    async def retrieve(
        self,
        project_id: str,
        tier: MemoryTier,
        query: str,
        filters: Optional[MemoryFilter] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Query memory entries matching project and filter criteria.
        Phase 0-10: Exact match, tag filter, and relational queries.
        Phase 11: Augmented with pgvector semantic similarity search.
        """
        ...
```

#### `MemoryQueryRequest` Schema:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MemoryQueryRequest",
  "type": "object",
  "required": ["project_id", "tier", "query"],
  "properties": {
    "project_id": { "type": "string" },
    "tier": { "type": "string", "enum": ["CONVERSATION", "PROJECT"] },
    "query": { "type": "string" },
    "session_id": { "type": ["string", "null"] },
    "category": { "type": ["string", "null"] },
    "tags": { "type": "array", "items": { "type": "string" } },
    "limit": { "type": "integer", "default": 5, "maximum": 50 }
  }
}
```

---

### 4.2 Write & Update Contract

```python
    async def record(
        self,
        entry: MemoryWriteRequest
    ) -> MemoryEntry:
        """Persist a new memory entry."""
        ...

    async def update(
        self,
        entry_id: str,
        content: str,
        metadata_patch: Optional[dict] = None
    ) -> MemoryEntry:
        """Update an existing memory entry."""
        ...
```

#### `MemoryWriteRequest` Schema:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MemoryWriteRequest",
  "type": "object",
  "required": ["project_id", "tier", "category", "content"],
  "properties": {
    "project_id": { "type": "string" },
    "tier": { "type": "string", "enum": ["CONVERSATION", "PROJECT"] },
    "session_id": { "type": ["string", "null"] },
    "category": { "type": "string" },
    "content": { "type": "string" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "ttl_seconds": { "type": ["integer", "null"] }
  }
}
```

---

## 5. Security & Permission Boundaries

1. **Permission Check:**
   - Reading memory requires `memory:read`.
   - Writing memory requires `memory:write`.
2. **Project Isolation:**
   - Agents are strictly sandboxed to their assigned `project_id`. Cross-project memory leakage is rejected at the service layer.
3. **Redaction & Sanitization:**
   - All entries written to `CONVERSATION` or `PROJECT` memory must pass a secret-redaction scanner (detecting API keys, passwords, bearer tokens) before persistence.
