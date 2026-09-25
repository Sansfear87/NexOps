from dataclasses import dataclass, field
import uuid

@dataclass
class SubTask:
    task_id: str
    description: str
    required_tools: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)  # task_ids this depends on
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    result: dict | None = None
    priority: int = 0  # lower = higher priority

@dataclass
class AgentPlan:
    plan_id: str
    goal: str
    sub_tasks: list[SubTask] = field(default_factory=list)
    current_task_index: int = 0
    status: str = "PLANNING"  # PLANNING, EXECUTING, COMPLETED, FAILED
    
    def get_next_task(self) -> SubTask | None:
        if self.current_task_index < len(self.sub_tasks):
            return self.sub_tasks[self.current_task_index]
        return None
        
    def mark_current_completed(self, result: dict) -> None:
        task = self.get_next_task()
        if task:
            task.status = "COMPLETED"
            task.result = result
            self.current_task_index += 1
            if self.is_complete():
                self.status = "COMPLETED"
            else:
                self.status = "EXECUTING"
                
    def mark_current_failed(self, error: str) -> None:
        task = self.get_next_task()
        if task:
            task.status = "FAILED"
            task.result = {"error": error}
            self.status = "FAILED"
            
    def is_complete(self) -> bool:
        return self.current_task_index >= len(self.sub_tasks) and all(t.status in ("COMPLETED", "SKIPPED") for t in self.sub_tasks)
        
    def get_progress(self) -> dict:
        total = len(self.sub_tasks)
        completed = sum(1 for t in self.sub_tasks if t.status == "COMPLETED")
        failed = sum(1 for t in self.sub_tasks if t.status == "FAILED")
        remaining = total - completed - failed
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "remaining": remaining
        }
        
    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "current_task_index": self.current_task_index,
            "status": self.status,
            "sub_tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "required_tools": t.required_tools,
                    "required_permissions": t.required_permissions,
                    "depends_on": t.depends_on,
                    "status": t.status,
                    "result": t.result,
                    "priority": t.priority
                } for t in self.sub_tasks
            ]
        }

class TaskDecomposer:
    """Uses LLM to break complex goals into executable sub-tasks."""
    
    DECOMPOSITION_PROMPT = '''Analyze the following goal and break it down into smaller sub-tasks.
Goal: {goal}
Available Tools: {tools}
'''
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
    async def decompose(self, goal: str, available_tools: list[str], permissions: list[str]) -> AgentPlan:
        """Break a goal into sub-tasks using the LLM."""
        if self.llm_client is None:
            return self._rule_based_decompose(goal, available_tools)
            
        # Fallback to rule-based for now since llm client interaction is mock
        return self._rule_based_decompose(goal, available_tools)
    
    def _rule_based_decompose(self, goal: str, available_tools: list[str]) -> AgentPlan:
        """Fallback decomposition without LLM."""
        plan = AgentPlan(plan_id=str(uuid.uuid4()), goal=goal, status="EXECUTING")
        goal_lower = goal.lower()
        
        if "review pr" in goal_lower or "review" in goal_lower:
            plan.sub_tasks = [
                SubTask(task_id="1", description="Fetch PR details", required_tools=["github_api"]),
                SubTask(task_id="2", description="Analyze diff", required_tools=["code_analyzer"], depends_on=["1"]),
                SubTask(task_id="3", description="Submit review comments", required_tools=["github_api"], depends_on=["2"])
            ]
        elif "deploy" in goal_lower:
            plan.sub_tasks = [
                SubTask(task_id="1", description="Run tests", required_tools=["test_runner"]),
                SubTask(task_id="2", description="Assess risk", depends_on=["1"]),
                SubTask(task_id="3", description="Execute deployment", required_tools=["deploy_tool"], depends_on=["2"]),
                SubTask(task_id="4", description="Verify health", required_tools=["health_checker"], depends_on=["3"])
            ]
        elif "diagnose" in goal_lower or "incident" in goal_lower:
            plan.sub_tasks = [
                SubTask(task_id="1", description="Fetch recent logs", required_tools=["log_viewer"]),
                SubTask(task_id="2", description="Analyze metrics", required_tools=["metrics_viewer"]),
                SubTask(task_id="3", description="Identify root cause", depends_on=["1", "2"])
            ]
        else:
            plan.sub_tasks = [
                SubTask(task_id="1", description=f"Execute {goal}", required_tools=available_tools)
            ]
            
        return plan
