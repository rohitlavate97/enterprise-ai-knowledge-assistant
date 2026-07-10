"""FastAPI router for Workflow Engine management."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.workflow_repository import workflow_repo
from app.schemas.workflow import WorkflowCreate, WorkflowResponse
from app.services.workflow_engine import workflow_engine

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow(
    workflow_in: WorkflowCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Create a new multi-step workflow execution graph."""
    logger.info("User %s creating workflow: %s", current_user.email, workflow_in.name)
    try:
        return await workflow_repo.create(db, workflow_in, current_user.id)
    except Exception as err:
        logger.error("Failed to create workflow: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create workflow: {str(err)}",
        ) from err


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all workflows for the current authenticated user."""
    return await workflow_repo.list_by_user(db, current_user.id, skip=skip, limit=limit)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Retrieve details of a specific workflow, including tasks and states.

    Returns the workflow with all of its associated task records.
    """
    workflow = await workflow_repo.get_by_id(db, workflow_id, current_user.id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found.",
        )
    return workflow


@router.post("/{workflow_id}/run", response_model=WorkflowResponse)
async def run_workflow(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Trigger the background execution run of a specific workflow."""
    workflow = await workflow_repo.get_by_id(db, workflow_id, current_user.id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found.",
        )

    if workflow.status == "running":
        return workflow

    # Reset workflow and task statuses if they were previously executed
    workflow.status = "pending"
    for task in workflow.tasks:
        task.status = "pending"
        task.retry_count = 0
        task.output_data = None
    db.add(workflow)
    await db.commit()

    # Re-fetch workflow with eager loaded tasks to prevent MissingGreenlet error
    workflow = await workflow_repo.get_by_id(db, workflow_id, current_user.id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found during re-fetch.",
        )

    # Dispatch background runner using session maker bound to connection bind
    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    background_tasks.add_task(
        workflow_engine.run_workflow_context,
        session_factory,
        workflow.id,
        current_user.id,
    )
    logger.info("Dispatched background workflow execution for workflow %s", workflow.id)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a workflow and cancel all of its cascade-dependent tasks."""
    workflow = await workflow_repo.get_by_id(db, workflow_id, current_user.id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found.",
        )
    await workflow_repo.delete(db, workflow)
