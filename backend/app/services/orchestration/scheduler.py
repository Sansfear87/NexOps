"""Task Scheduler executing workflow DAG with concurrency bounds and retry policies.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional
from app.services.orchestration.task_graph import TaskGraph, TaskNode, TaskStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Schedules and executes ready tasks in a TaskGraph concurrently up to a concurrency limit."""

    def __init__(self, max_concurrency: int = 3):
        self.max_concurrency = max_concurrency

    async def execute_graph(
        self,
        graph: TaskGraph,
        worker_dispatcher: Callable[[TaskNode], Coroutine[Any, Any, Dict[str, Any]]],
    ) -> TaskGraph:
        """Execute the DAG tasks to completion or terminal failure."""
        graph.validate_dag()
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _run_single_task(task: TaskNode) -> None:
            async with semaphore:
                graph.mark_running(task.task_id)
                try:
                    result = await asyncio.wait_for(
                        worker_dispatcher(task),
                        timeout=task.deadline_seconds,
                    )
                    graph.mark_succeeded(task.task_id, result)
                except asyncio.TimeoutError:
                    logger.error("Task '%s' timed out after %s seconds.", task.task_id, task.deadline_seconds)
                    graph.mark_failed(task.task_id, f"Task timed out after {task.deadline_seconds}s")
                except Exception as exc:
                    logger.error("Task '%s' failed: %s", task.task_id, exc)
                    if task.attempt_count <= task.max_retries:
                        logger.info("Retrying task '%s' (attempt %d/%d)...", task.task_id, task.attempt_count, task.max_retries)
                        task.status = TaskStatus.PENDING
                    else:
                        graph.mark_failed(task.task_id, str(exc))

        while not graph.is_complete():
            ready_tasks = graph.get_ready_tasks()
            if not ready_tasks:
                # If no tasks are ready and the graph is not complete, we might be stuck due to prior failures
                if any(t.status == TaskStatus.RUNNING for t in graph.tasks.values()):
                    await asyncio.sleep(0.05)
                    continue
                else:
                    # Unexecutable pending tasks due to failed dependencies
                    for t in graph.tasks.values():
                        if t.status in (TaskStatus.PENDING, TaskStatus.READY):
                            graph.mark_failed(t.task_id, "Dependencies failed or not met.")
                    break

            # Execute batch of ready tasks concurrently
            await asyncio.gather(*[_run_single_task(t) for t in ready_tasks])

        return graph
