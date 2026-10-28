"""Task Graph DAG Representation for Multi-Agent Workflows.

Provides explicit task states, dependency scheduling, cycle detection, and serialization.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class TaskNode(BaseModel):
    """Represents a single node in the workflow Directed Acyclic Graph (DAG)."""
    task_id: str
    name: str
    task_type: str = Field(..., description="e.g. code_review, security_review, run_tests, risk_assessment")
    depends_on: List[str] = Field(default_factory=list, description="IDs of tasks that must succeed before this task runs")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    assigned_model: Optional[str] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempt_count: int = 0
    max_retries: int = 2
    deadline_seconds: float = 60.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskGraph:
    """Directed Acyclic Graph (DAG) managing workflow tasks, dependencies, and state transitions."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.tasks: Dict[str, TaskNode] = {}

    def add_task(self, task: TaskNode) -> None:
        """Add a task node to the graph and validate uniqueness."""
        if task.task_id in self.tasks:
            raise ValueError(f"Task with ID '{task.task_id}' already exists in graph.")
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """Fetch task by ID."""
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> List[TaskNode]:
        """Return all tasks that are PENDING and whose dependencies have all SUCCEEDED."""
        ready: List[TaskNode] = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue

            # Check if all dependencies are satisfied
            deps_satisfied = True
            for dep_id in task.depends_on:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.SUCCEEDED:
                    deps_satisfied = False
                    break

            if deps_satisfied:
                task.status = TaskStatus.READY
                ready.append(task)

        return ready

    def mark_running(self, task_id: str, assigned_model: Optional[str] = None) -> None:
        """Transition task from READY to RUNNING."""
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.attempt_count += 1
        task.started_at = datetime.now(timezone.utc).isoformat()
        if assigned_model:
            task.assigned_model = assigned_model

    def mark_succeeded(self, task_id: str, result: Dict[str, Any]) -> None:
        """Transition task to SUCCEEDED and store result."""
        task = self.tasks[task_id]
        task.status = TaskStatus.SUCCEEDED
        task.result = result
        task.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, task_id: str, error: str) -> None:
        """Transition task to FAILED and record error message."""
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.now(timezone.utc).isoformat()

    def is_complete(self) -> bool:
        """Return True if all tasks have reached a terminal state."""
        terminal_states = {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.TIMED_OUT,
            TaskStatus.CANCELLED,
        }
        return all(task.status in terminal_states for task in self.tasks.values())

    def has_failures(self) -> bool:
        """Return True if any task failed, timed out, or was cancelled."""
        failure_states = {TaskStatus.FAILED, TaskStatus.TIMED_OUT, TaskStatus.CANCELLED}
        return any(task.status in failure_states for task in self.tasks.values())

    def validate_dag(self) -> None:
        """Ensure the task graph has no cyclic dependencies using Kahn's algorithm."""
        in_degree: Dict[str, int] = {t_id: 0 for t_id in self.tasks}
        adj_list: Dict[str, List[str]] = {t_id: [] for t_id in self.tasks}

        for task_id, task in self.tasks.items():
            for dep_id in task.depends_on:
                if dep_id not in self.tasks:
                    raise ValueError(f"Task '{task_id}' depends on non-existent task '{dep_id}'.")
                adj_list[dep_id].append(task_id)
                in_degree[task_id] += 1

        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            node = queue.pop(0)
            visited_count += 1
            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.tasks):
            raise ValueError("Cyclic dependency detected in task graph.")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task graph for JSON persistence and real-time frontend streaming."""
        return {
            "run_id": self.run_id,
            "is_complete": self.is_complete(),
            "has_failures": self.has_failures(),
            "tasks": [task.model_dump() for task in self.tasks.values()],
        }
