from enum import Enum
from dataclasses import dataclass, field
from typing import Any
import re
from datetime import datetime, timezone
import uuid

class MemoryTier(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    CONVERSATION = "CONVERSATION"
    PROJECT = "PROJECT"

class MemoryCategory(str, Enum):
    ARCHITECTURE_RULE = "ARCHITECTURE_RULE"
    FLAKY_TEST = "FLAKY_TEST"
    INCIDENT_POSTMORTEM = "INCIDENT_POSTMORTEM"
    DEPLOYMENT_NOTE = "DEPLOYMENT_NOTE"
    USER_PREFERENCE = "USER_PREFERENCE"
    AGENT_SCRATCHPAD = "AGENT_SCRATCHPAD"

def _redact_secrets(content: str) -> str:
    patterns = [
        (r'(?i)(api[_-]?key[\s=:]*)(["\'][a-zA-Z0-9_\-]+["\']|[a-zA-Z0-9_\-]+)', r'\1<REDACTED_API_KEY>'),
        (r'(?i)(token[\s=:]*)(["\'][a-zA-Z0-9_\-]+["\']|[a-zA-Z0-9_\-]+)', r'\1<REDACTED_TOKEN>'),
        (r'(?i)(password[\s=:]*)(["\'][^"\']+["\']|[^\s]+)', r'\1<REDACTED_PASSWORD>'),
        (r'(?i)(secret[\s=:]*)(["\'][a-zA-Z0-9_\-]+["\']|[a-zA-Z0-9_\-]+)', r'\1<REDACTED_SECRET>')
    ]
    redacted = content
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted

@dataclass
class MemoryEntry:
    entry_id: str
    tier: MemoryTier
    category: MemoryCategory
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    ttl_seconds: int | None = None
    relevance_score: float = 1.0

class ShortTermMemory:
    """Ephemeral per-run scratchpad. Lives only during one agent.run() call."""
    def __init__(self):
        self._store: dict[str, Any] = {}
        
    def store(self, key: str, value: Any) -> None:
        self._store[key] = value
        
    def retrieve(self, key: str) -> Any | None:
        return self._store.get(key)
        
    def list_all(self) -> dict[str, Any]:
        return dict(self._store)
        
    def clear(self) -> None:
        self._store.clear()

class ConversationMemory:
    """Session-scoped memory across multiple agent runs in one conversation."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._entries: list[MemoryEntry] = []
        
    def add(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        
    def search(self, query: str, category: MemoryCategory | None = None, limit: int = 10) -> list[MemoryEntry]:
        results = self._entries
        if category:
            results = [e for e in results if e.category == category]
            
        # Simple keyword matching
        query_words = set(query.lower().split())
        
        scored = []
        for entry in results:
            content_lower = entry.content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored.append((score, entry))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored][:limit]
        
    def get_recent(self, limit: int = 5) -> list[MemoryEntry]:
        return self._entries[-limit:]

class ProjectMemory:
    """Persistent cross-session memory. Delegates to platform storage callback."""
    def __init__(self, project_id: str, storage_callback=None):
        self.project_id = project_id
        self.storage_callback = storage_callback
        self._local_fallback: list[MemoryEntry] = []
        
    def record(self, entry: MemoryEntry) -> None:
        if self.storage_callback:
            self.storage_callback(entry)
        else:
            self._local_fallback.append(entry)
            
    def retrieve(self, query: str, category: MemoryCategory | None = None, limit: int = 10) -> list[MemoryEntry]:
        # Local fallback search
        results = self._local_fallback
        if category:
            results = [e for e in results if e.category == category]
            
        query_words = set(query.lower().split())
        scored = []
        for entry in results:
            content_lower = entry.content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored.append((score, entry))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored][:limit]

class MemoryManager:
    """Unified interface across all 3 tiers."""
    def __init__(self, session_id: str, project_id: str, storage_callback=None):
        self.session_id = session_id
        self.project_id = project_id
        self._short_term = ShortTermMemory()
        self._conversation = ConversationMemory(session_id)
        self._project = ProjectMemory(project_id, storage_callback)
        
    @property
    def short_term(self) -> ShortTermMemory:
        return self._short_term
        
    @property
    def conversation(self) -> ConversationMemory:
        return self._conversation
        
    @property  
    def project(self) -> ProjectMemory:
        return self._project
        
    def remember(self, content: str, category: MemoryCategory, tier: MemoryTier = MemoryTier.CONVERSATION, tags: list[str] = None) -> MemoryEntry:
        redacted_content = _redact_secrets(content)
        entry = MemoryEntry(
            entry_id=str(uuid.uuid4()),
            tier=tier,
            category=category,
            content=redacted_content,
            tags=tags or [],
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        if tier == MemoryTier.CONVERSATION:
            self.conversation.add(entry)
        elif tier == MemoryTier.PROJECT:
            self.project.record(entry)
            
        return entry
        
    def recall(self, query: str, tier: MemoryTier | None = None, limit: int = 10) -> list[MemoryEntry]:
        results = []
        
        if tier is None or tier == MemoryTier.CONVERSATION:
            results.extend(self.conversation.search(query, limit=limit))
            
        if tier is None or tier == MemoryTier.PROJECT:
            results.extend(self.project.retrieve(query, limit=limit))
            
        # Deduplicate and sort by relevance
        seen = set()
        unique_results = []
        for r in results:
            if r.entry_id not in seen:
                seen.add(r.entry_id)
                unique_results.append(r)
                
        return unique_results[:limit]
