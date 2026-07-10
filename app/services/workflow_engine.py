"""Workflow engine service for executing multi-agent workflows.

Supports task scheduling, retries, and conditional routing.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.models.workflow import WorkflowTask
from app.repositories.notification_repository import notification_repo
from app.repositories.workflow_repository import workflow_repo
from app.schemas.notification import NotificationCreate
from app.schemas.workflow import WorkflowTaskUpdate
from app.services.coordinator_agent import direct_agent
from app.services.document_agent import (
    AgentDeps as DocDeps,
    document_agent,
)
from app.services.research_agent import (
    AgentDeps as ResearchDeps,
    research_agent,
)

logger = logging.getLogger(__name__)


class WorkflowEngineService:
    """Service class coordinating workflow lifecycle execution."""

    async def execute_task_logic(
        self, db: AsyncSession, task: WorkflowTask, user: User
    ) -> dict[str, Any]:
        """Execute the actual logic of a single WorkflowTask based on its task_type.

        Supports multi-agent and system/utility tasks.
        """
        logger.info("Executing task %s of type %s", task.id, task.task_type)
        query = (task.input_data or {}).get("query", "")

        if task.task_type == "research":
            # Invoke the specialist Research Agent
            deps_research = ResearchDeps(db=db, current_user=user)
            res_research = await research_agent.run(query, deps=deps_research)
            return {
                "summary": res_research.output.summary,
                "detailed_findings": res_research.output.detailed_findings,
                "sources_cited": res_research.output.sources_cited,
                "confidence_score": res_research.output.confidence_score,
            }

        if task.task_type == "document":
            # Invoke the specialist Document Agent
            deps_doc = DocDeps(db=db, current_user=user)
            res_doc = await document_agent.run(query, deps=deps_doc)
            return {
                "response_summary": res_doc.output.response_summary,
                "document_details": res_doc.output.document_details,
                "documents_referenced": res_doc.output.documents_referenced,
                "operation_status": res_doc.output.operation_status,
            }

        if task.task_type == "direct":
            # Direct chit-chat/greetings agent
            res_direct = await direct_agent.run(query)
            return {
                "response": res_direct.output,
            }

        if task.task_type in {"system", "custom"}:
            # Utility system tasks, e.g. echo, simple math, or metadata processing
            message = (task.input_data or {}).get(
                "message", "System action executed successfully."
            )
            return {"status": "success", "message": message}

        raise ValueError(f"Unsupported task type: {task.task_type}")

    async def execute_task_with_retry(
        self, db: AsyncSession, task: WorkflowTask, user: User
    ) -> bool:
        """Run a task's logic, managing retries with delays in case of failures."""
        task_id = task.id

        while task.retry_count <= task.max_retries:
            try:
                # Update task status to running
                await workflow_repo.update_task(
                    db, task, WorkflowTaskUpdate(status="running")
                )

                # Run the task logic
                output = await self.execute_task_logic(db, task, user)

                # Mark task as completed
                await workflow_repo.update_task(
                    db,
                    task,
                    WorkflowTaskUpdate(status="completed", output_data=output),
                )
                logger.info("Task %s completed successfully", task_id)
                return True

            except Exception as err:
                logger.error(
                    "Error executing task %s (Attempt %d/%d): %s",
                    task_id,
                    task.retry_count + 1,
                    task.max_retries + 1,
                    str(err),
                )

                # Increment retry count
                new_retry_count = task.retry_count + 1
                await workflow_repo.update_task(
                    db, task, WorkflowTaskUpdate(retry_count=new_retry_count)
                )

                if new_retry_count <= task.max_retries:
                    # Update status to retrying
                    await workflow_repo.update_task(
                        db, task, WorkflowTaskUpdate(status="retrying")
                    )
                    logger.info(
                        "Sleeping for %d seconds before retry...", task.retry_delay
                    )
                    await asyncio.sleep(task.retry_delay)
                else:
                    # Exceeded max retries, mark as failed
                    await workflow_repo.update_task(
                        db,
                        task,
                        WorkflowTaskUpdate(
                            status="failed",
                            output_data={
                                "error": (
                                    f"Failed after max retries. Last error: {str(err)}"
                                )
                            },
                        ),
                    )
                    logger.info("Task %s failed after exceeding max retries", task_id)
                    return False

        return False

    async def run_workflow_context(  # noqa: PLR0912, PLR0915
        self,
        session_factory: async_sessionmaker[AsyncSession],
        workflow_id: UUID,
        user_id: UUID,
    ) -> None:
        """Core engine loop executing tasks within a background database session.

        Implements dependency checks, scheduling, conditional routing, and retries.
        """
        logger.info("Workflow %s background execution started", workflow_id)

        async with session_factory() as db:
            # 1. Fetch workflow with tasks
            workflow = await workflow_repo.get_by_id(db, workflow_id, user_id)
            if not workflow:
                logger.error("Workflow %s not found for user %s", workflow_id, user_id)
                return

            if workflow.status in ["running", "completed", "failed"]:
                logger.warning(
                    "Workflow %s has status '%s', skipping run.",
                    workflow_id,
                    workflow.status,
                )
                return

            # Update workflow status to running
            await workflow_repo.update_workflow_status(db, workflow, "running", user_id)

            user = workflow.user

            try:
                # Sort tasks by step number for sequential scheduling baseline
                tasks_to_run = sorted(workflow.tasks, key=lambda t: t.step_number)
                task_map = {task.id: task for task in tasks_to_run}

                execution_pointer = 0
                while execution_pointer < len(tasks_to_run):
                    task = tasks_to_run[execution_pointer]

                    # Skip already completed or skipped tasks
                    if task.status in ["completed", "skipped"]:
                        execution_pointer += 1
                        continue

                    # Check dependencies
                    if task.depends_on_task_id:
                        dep_task = task_map.get(task.depends_on_task_id)
                        if dep_task and dep_task.status != "completed":
                            if dep_task.status == "failed":
                                # Dependency failed, skip this task
                                await workflow_repo.update_task(
                                    db,
                                    task,
                                    WorkflowTaskUpdate(
                                        status="skipped",
                                        output_data={"reason": "Dependency failed"},
                                    ),
                                )
                                execution_pointer += 1
                                continue
                            # Dependency is still running or pending.
                            # In a fully concurrent DAG engine, we would yield.
                            # Here we wait for it.
                            logger.info(
                                "Task %s is waiting for dependency %s to complete",
                                task.id,
                                dep_task.id,
                            )
                            await asyncio.sleep(1)
                            continue

                    # Check scheduling
                    if task.scheduled_at:
                        now = (
                            datetime.now(UTC)
                            if task.scheduled_at.tzinfo
                            else datetime.now()
                        )
                        if now < task.scheduled_at:
                            wait_seconds = (task.scheduled_at - now).total_seconds()
                            if wait_seconds > 0:
                                logger.info(
                                    "Task %s scheduled in future. "
                                    "Sleeping for %f seconds.",
                                    task.id,
                                    wait_seconds,
                                )
                                # Cap sleep at a reasonable test limit
                                await asyncio.sleep(min(wait_seconds, 60.0))

                    # Run task
                    success = await self.execute_task_with_retry(db, task, user)

                    # Refresh task record from DB in case relationship maps changed
                    await db.refresh(task)

                    # Conditional routing checks
                    next_task_id = None
                    if task.conditional_routes:
                        outcome = "success" if success else "failure"
                        route_target = task.conditional_routes.get(outcome)
                        if route_target:
                            try:
                                next_task_id = UUID(route_target)
                            except ValueError:
                                logger.warning(
                                    "Invalid conditional route target: %s", route_target
                                )

                    if next_task_id:
                        logger.info(
                            "Conditional route matched! Next task: %s", next_task_id
                        )
                        # Mark intermediate tasks (between pointer and next)
                        # as skipped
                        target_index = -1
                        for idx, t in enumerate(tasks_to_run):
                            if t.id == next_task_id:
                                target_index = idx
                                break

                        if target_index != -1:
                            # Skip tasks in between
                            for t in tasks_to_run[execution_pointer + 1 : target_index]:
                                if t.status == "pending":
                                    await workflow_repo.update_task(
                                        db, t, WorkflowTaskUpdate(status="skipped")
                                    )
                            execution_pointer = target_index
                            continue

                    # If task failed and no conditional fallback route
                    # was registered, fail workflow
                    if not success:
                        await workflow_repo.update_workflow_status(
                            db, workflow, "failed", user_id
                        )
                        logger.info(
                            "Workflow %s failed due to task %s failure",
                            workflow_id,
                            task.id,
                        )
                        return

                    execution_pointer += 1

                # Check if all tasks completed or skipped
                workflow = await workflow_repo.get_by_id(db, workflow_id, user_id)
                if not workflow:
                    logger.error("Workflow %s re-fetch returned None", workflow_id)
                    return
                all_done = all(
                    t.status in ["completed", "skipped"] for t in workflow.tasks
                )

                if all_done:
                    final_status = "completed"
                    # If any task failed and is not matched by conditional route,
                    # it would have returned early.
                    # If tasks ended in failed/skipped status, check if there was
                    # a failure that was unhandled
                    has_failed = any(t.status == "failed" for t in workflow.tasks)
                    if has_failed:
                        final_status = "failed"

                    await workflow_repo.update_workflow_status(
                        db, workflow, final_status, user_id
                    )

                    # Trigger workflow status notification
                    try:
                        await notification_repo.create(
                            db,
                            NotificationCreate(
                                title=f"Workflow {final_status.capitalize()}",
                                message=(
                                    f"Workflow '{workflow.name}' has finished "
                                    f"with status: {final_status}."
                                ),
                                notification_type="workflow",
                            ),
                            user_id=workflow.user_id,
                        )
                    except Exception as notify_err:
                        logger.error(
                            "Failed to notify workflow owner: %s", str(notify_err)
                        )

                    logger.info(
                        "Workflow %s finished with status: %s",
                        workflow_id,
                        final_status,
                    )

            except Exception as e:
                logger.error(
                    "Error executing workflow %s loop: %s",
                    workflow_id,
                    str(e),
                    exc_info=True,
                )
                if workflow is not None:
                    await workflow_repo.update_workflow_status(
                        db, workflow, "failed", user_id
                    )
                    try:
                        await notification_repo.create(
                            db,
                            NotificationCreate(
                                title="Workflow Failed",
                                message=(
                                    f"Workflow '{workflow.name}' failed due to "
                                    f"a system error: {str(e)}"
                                ),
                                notification_type="workflow",
                            ),
                            user_id=workflow.user_id,
                        )
                    except Exception as notify_err:
                        logger.error(
                            "Failed to notify workflow owner: %s", str(notify_err)
                        )


workflow_engine = WorkflowEngineService()
