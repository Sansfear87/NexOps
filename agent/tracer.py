from dataclasses import dataclass, field
from typing import Any
import time
from datetime import datetime, timezone

@dataclass
class TraceStep:
    step_index: int
    step_type: str  # "thought", "action", "observation", "error", "final_answer"
    content: str
    tool_name: str | None = None
    tool_parameters: dict | None = None
    tool_result: dict | None = None
    duration_ms: int = 0
    token_count_estimate: int = 0  # rough estimate: len(content) / 4
    timestamp: str = ""  # ISO-8601

@dataclass 
class AgentTrace:
    run_id: str
    trace_id: str
    goal: str
    steps: list[TraceStep] = field(default_factory=list)
    total_duration_ms: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    total_tokens_estimate: int = 0
    status: str = "RUNNING"
    
    def add_step(self, **kwargs) -> TraceStep:
        kwargs['step_index'] = len(self.steps)
        if 'timestamp' not in kwargs or not kwargs['timestamp']:
            kwargs['timestamp'] = datetime.now(timezone.utc).isoformat()
        if 'content' in kwargs and 'token_count_estimate' not in kwargs:
            kwargs['token_count_estimate'] = len(kwargs.get('content', '')) // 4
            
        step = TraceStep(**kwargs)
        self.steps.append(step)
        
        if step.step_type in ("thought", "action", "final_answer"):
            self.total_llm_calls += 1
            self.total_tokens_estimate += step.token_count_estimate
            
        if step.step_type == "action":
            self.total_tool_calls += 1
            
        self.total_duration_ms += step.duration_ms
        return step
        
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "goal": self.goal,
            "total_duration_ms": self.total_duration_ms,
            "total_llm_calls": self.total_llm_calls,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens_estimate": self.total_tokens_estimate,
            "status": self.status,
            "steps": [
                {
                    "step_index": s.step_index,
                    "step_type": s.step_type,
                    "content": s.content,
                    "tool_name": s.tool_name,
                    "tool_parameters": s.tool_parameters,
                    "tool_result": s.tool_result,
                    "duration_ms": s.duration_ms,
                    "token_count_estimate": s.token_count_estimate,
                    "timestamp": s.timestamp,
                } for s in self.steps
            ]
        }
        
    def summary(self) -> str:
        return f"Trace {self.trace_id} for run {self.run_id} ({self.status}): {len(self.steps)} steps, {self.total_duration_ms}ms, {self.total_llm_calls} LLM calls"


class AgentTracer:
    """Collects traces during agent execution."""
    def __init__(self):
        self.traces: dict[str, AgentTrace] = {}
        
    def start_trace(self, run_id: str, trace_id: str, goal: str) -> AgentTrace:
        trace = AgentTrace(run_id=run_id, trace_id=trace_id, goal=goal)
        self.traces[run_id] = trace
        return trace
        
    def record_thought(self, trace: AgentTrace, thought_text: str) -> TraceStep:
        return trace.add_step(step_type="thought", content=thought_text)
        
    def record_action(self, trace: AgentTrace, tool_name: str, parameters: dict) -> TraceStep:
        return trace.add_step(
            step_type="action", 
            content=f"Call {tool_name}", 
            tool_name=tool_name, 
            tool_parameters=parameters
        )
        
    def record_observation(self, trace: AgentTrace, tool_name: str, result: dict, duration_ms: int) -> TraceStep:
        return trace.add_step(
            step_type="observation", 
            content=f"Result from {tool_name}", 
            tool_name=tool_name, 
            tool_result=result,
            duration_ms=duration_ms
        )
        
    def record_error(self, trace: AgentTrace, error_text: str) -> TraceStep:
        return trace.add_step(step_type="error", content=error_text)
        
    def record_final_answer(self, trace: AgentTrace, answer: str) -> TraceStep:
        return trace.add_step(step_type="final_answer", content=answer)
        
    def finalize_trace(self, trace: AgentTrace, status: str) -> AgentTrace:
        trace.status = status
        return trace
        
    def get_trace(self, run_id: str) -> AgentTrace | None:
        return self.traces.get(run_id)
        
    def export_traces(self) -> list[dict]:
        return [trace.to_dict() for trace in self.traces.values()]
