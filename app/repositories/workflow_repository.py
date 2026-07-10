"""Database Repository for Workflow and WorkflowTask models using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow, WorkflowTask
from app.schemas.workflow import WorkflowCreate, WorkflowTaskUpdate


class WorkflowRepository:
    """Database repository layer for managing Workflow and WorkflowTask records."""

    async def get_by_id(
        self, db: AsyncSession, workflow_id: UUID, user_id: UUID
    ) -> Workflow | None:
        """Retrieve a workflow by ID, scoped by user_id for multi-tenancy."""
        query = (
            select(Workflow)
            .where(Workflow.id == workflow_id, Workflow.user_id == user_id)
            .options(
                selectinload(Workflow.tasks),
                selectinload(Workflow.user),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, workflow_in: WorkflowCreate, user_id: UUID
    ) -> Workflow:
        """Create a new Workflow and its tasks in a single transaction."""
        db_workflow = Workflow(
            name=workflow_in.name,
            description=workflow_in.description,
            status="pending",
            user_id=user_id,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(db_workflow)
        await db.flush()  # Generate db_workflow.id for foreign keys

        # Create tasks
        task_id_map = {}  # Map step_number to generated UUID for routing resolution
        db_tasks = []

        # First pass: create all task objects to generate IDs
        for task_in in workflow_in.tasks:
            db_task = WorkflowTask(
                workflow_id=db_workflow.id,
                name=task_in.name,
                task_type=task_in.task_type,
                status="pending",
                input_data=task_in.input_data,
                step_number=task_in.step_number,
                max_retries=task_in.max_retries,
                retry_count=0,
                retry_delay=task_in.retry_delay,
                scheduled_at=task_in.scheduled_at,
                conditional_routes=task_in.conditional_routes,
            )
            db.add(db_task)
            db_tasks.append((task_in, db_task))

        await db.flush()

        # Map step number to task ID
        for task_in, db_task in db_tasks:
            task_id_map[task_in.step_number] = db_task.id

        # Second pass: wire dependencies and resolve conditional routes
        # that reference step_numbers
        for task_in, db_task in db_tasks:
            if task_in.depends_on_task_id:
                # If depends_on_task_id is already a UUID, use it directly;
                # otherwise if it's treated as a step number in input, resolve it.
                db_task.depends_on_task_id = task_in.depends_on_task_id

            # Resolve conditional routes if they map string outcome -> step number
            if db_task.conditional_routes:
                resolved_routes = {}
                for outcome, target in db_task.conditional_routes.items():
                    # If target is a number (step number), map to its UUID
                    try:
                        step_num = int(target)
                        if step_num in task_id_map:
                            resolved_routes[outcome] = str(task_id_map[step_num])
                        else:
                            resolved_routes[outcome] = str(target)
                    except ValueError:
                        resolved_routes[outcome] = str(target)
                db_task.conditional_routes = resolved_routes

        await db.commit()

        # Reload with tasks
        wf = await self.get_by_id(db, db_workflow.id, user_id)
        assert wf is not None
        return wf

    async def list_by_user(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Workflow]:
        """List workflows for a specific user, ordered by last updated."""
        query = (
            select(Workflow)
            .where(Workflow.user_id == user_id)
            .options(selectinload(Workflow.tasks))
            .order_by(Workflow.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_workflow_status(
        self, db: AsyncSession, db_workflow: Workflow, status: str, user_id: UUID
    ) -> Workflow:
        """Update a workflow's overall status."""
        db_workflow.status = status
        db_workflow.updated_by = user_id
        db.add(db_workflow)
        await db.commit()
        # Reload with tasks to avoid MissingGreenlet error when returning to router
        wf = await self.get_by_id(db, db_workflow.id, user_id)
        assert wf is not None
        return wf

    async def update_task(
        self, db: AsyncSession, db_task: WorkflowTask, task_in: WorkflowTaskUpdate
    ) -> WorkflowTask:
        """Update a task's progress status, output, and configuration details."""
        update_data = task_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)
        db.add(db_task)
        await db.commit()
        await db.refresh(db_task)
        return db_task

    async def delete(self, db: AsyncSession, db_workflow: Workflow) -> None:
        """Delete a workflow and all of its cascade-dependent tasks."""
        await db.delete(db_workflow)
        await db.commit()


workflow_repo = WorkflowRepository()
