"""Integration and unit tests for the Workflow Engine."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.repositories.workflow_repository import workflow_repo
from app.schemas.user import UserCreate, UserRole
from app.schemas.workflow import WorkflowCreate, WorkflowTaskCreate
from app.services.coordinator_agent import direct_agent
from app.services.document_agent import DocumentAgentResponse, document_agent
from app.services.research_agent import ResearchAgentResponse, research_agent
from app.services.workflow_engine import WorkflowEngineService, workflow_engine


async def get_auth_headers(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    """Helper function to login a user and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_workflow_crud_endpoints(db: AsyncSession) -> None:
    """Test creating, listing, fetching, and deleting a workflow via REST API."""
    # 1. Register test user
    await user_repo.create(
        db,
        UserCreate(
            email="wf_crud@enterprise.com",
            full_name="Workflow User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "wf_crud@enterprise.com", "password123"
        )

        # 2. Create Workflow
        wf_data = {
            "name": "Metadata Check Workflow",
            "description": "Checks metadata and routes based on outcome",
            "tasks": [
                {
                    "name": "Task 1",
                    "task_type": "system",
                    "input_data": {"message": "T1"},
                    "step_number": 1,
                    "max_retries": 2,
                    "retry_delay": 1,
                },
                {
                    "name": "Task 2",
                    "task_type": "system",
                    "input_data": {"message": "T2"},
                    "step_number": 2,
                    "max_retries": 1,
                    "retry_delay": 1,
                    "depends_on_task_id": None,
                },
            ],
        }

        create_res = await client.post(
            "/api/v1/workflows/",
            json=wf_data,
            headers=headers,
        )
        assert create_res.status_code == status.HTTP_201_CREATED
        wf_json = create_res.json()
        assert wf_json["name"] == "Metadata Check Workflow"
        assert len(wf_json["tasks"]) == 2
        wf_id = wf_json["id"]

        # 3. Get Workflow
        get_res = await client.get(f"/api/v1/workflows/{wf_id}", headers=headers)
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["id"] == wf_id

        # 4. List Workflows
        list_res = await client.get("/api/v1/workflows/", headers=headers)
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()) >= 1

        # 5. Delete Workflow
        del_res = await client.delete(f"/api/v1/workflows/{wf_id}", headers=headers)
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

        # Get again should return 404
        get_res2 = await client.get(f"/api/v1/workflows/{wf_id}", headers=headers)
        assert get_res2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_workflow_engine_execution_success(db: AsyncSession) -> None:
    """Test successful sequential execution of workflow tasks."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_exec_success@enterprise.com",
            full_name="Exec User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    # Create a simple 2-step sequential workflow
    wf_in = WorkflowCreate(
        name="Sequential Success Workflow",
        description="Runs two system tasks sequentially",
        tasks=[
            WorkflowTaskCreate(
                name="First Step",
                task_type="system",
                input_data={"message": "First"},
                step_number=1,
            ),
            WorkflowTaskCreate(
                name="Second Step",
                task_type="system",
                input_data={"message": "Second"},
                step_number=2,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Execute the workflow engine loop
    await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)

    # Reload workflow
    db.expunge_all()
    updated_wf = await workflow_repo.get_by_id(db, wf.id, user.id)
    assert updated_wf is not None
    assert updated_wf.status == "completed"

    # Check tasks
    tasks = sorted(updated_wf.tasks, key=lambda t: t.step_number)
    assert tasks[0].status == "completed"
    assert tasks[0].output_data == {"status": "success", "message": "First"}
    assert tasks[1].status == "completed"
    assert tasks[1].output_data == {"status": "success", "message": "Second"}


@pytest.mark.asyncio
async def test_workflow_engine_retry_logic(db: AsyncSession) -> None:
    """Test task execution retries in case of transient errors."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_exec_retry@enterprise.com",
            full_name="Retry User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    wf_in = WorkflowCreate(
        name="Retry Failure Workflow",
        description="Fails task to trigger retry loop",
        tasks=[
            WorkflowTaskCreate(
                name="Failing Task",
                task_type="research",  # Use research type but fail it
                input_data={"query": "force_fail"},
                step_number=1,
                max_retries=2,
                retry_delay=0,  # No sleep delay for testing
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Mock execute_task_logic to throw an exception
    with patch.object(
        WorkflowEngineService,
        "execute_task_logic",
        side_effect=Exception("Transient LLM error"),
    ) as mock_exec:
        await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)

        # Verify it was called 3 times (1 initial run + 2 retries)
        assert mock_exec.call_count == 3

    # Reload workflow
    db.expunge_all()
    updated_wf = await workflow_repo.get_by_id(db, wf.id, user.id)
    assert updated_wf is not None
    assert updated_wf.status == "failed"
    assert updated_wf.tasks[0].status == "failed"
    assert updated_wf.tasks[0].retry_count == 3
    output = updated_wf.tasks[0].output_data or {}
    assert "Transient LLM error" in output["error"]


@pytest.mark.asyncio
async def test_workflow_engine_conditional_routing(db: AsyncSession) -> None:
    """Test dynamic routing branching based on task outcome status."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_exec_route@enterprise.com",
            full_name="Route User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    # Task 1 will succeed.
    # It routes to step 3 on success, and step 2 on failure.
    # Therefore, step 2 should be skipped, and step 3 should run.
    wf_in = WorkflowCreate(
        name="Routing Workflow",
        description="Test conditional route pathways",
        tasks=[
            WorkflowTaskCreate(
                name="Decider Task",
                task_type="system",
                input_data={"message": "ok"},
                step_number=1,
                conditional_routes={"success": 3, "failure": 2},
            ),
            WorkflowTaskCreate(
                name="Failure Branch Task",
                task_type="system",
                input_data={"message": "fail branch"},
                step_number=2,
            ),
            WorkflowTaskCreate(
                name="Success Branch Task",
                task_type="system",
                input_data={"message": "success branch"},
                step_number=3,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)

    # Reload and assert
    db.expunge_all()
    updated_wf = await workflow_repo.get_by_id(db, wf.id, user.id)
    assert updated_wf is not None
    assert updated_wf.status == "completed"

    tasks = sorted(updated_wf.tasks, key=lambda t: t.step_number)
    assert tasks[0].status == "completed"  # Decider Task
    assert tasks[1].status == "skipped"  # Failure Branch Task (bypassed)
    assert tasks[2].status == "completed"  # Success Branch Task


@pytest.mark.asyncio
async def test_workflow_engine_scheduling(db: AsyncSession) -> None:
    """Test scheduling tasks with a future timestamp."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_exec_sched@enterprise.com",
            full_name="Sched User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    # Set scheduled time 0.1s in the future
    future_time = datetime.now(UTC) + timedelta(seconds=0.1)

    wf_in = WorkflowCreate(
        name="Scheduled Workflow",
        description="Task scheduled in the future",
        tasks=[
            WorkflowTaskCreate(
                name="Scheduled Task",
                task_type="system",
                input_data={"message": "scheduled"},
                step_number=1,
                scheduled_at=future_time,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Run the workflow
    await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)

    # Reload
    db.expunge_all()
    updated_wf = await workflow_repo.get_by_id(db, wf.id, user.id)
    assert updated_wf is not None
    assert updated_wf.status == "completed"
    assert updated_wf.tasks[0].status == "completed"


@pytest.mark.asyncio
async def test_workflow_agent_integration(db: AsyncSession) -> None:
    """Test workflow task execution integrating with mock specialist agents."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_agent_int@enterprise.com",
            full_name="Agent User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    wf_in = WorkflowCreate(
        name="Agent Run Workflow",
        description="Runs research and document agents",
        tasks=[
            WorkflowTaskCreate(
                name="Specialist Research",
                task_type="research",
                input_data={"query": "Research wellness programs"},
                step_number=1,
            ),
            WorkflowTaskCreate(
                name="Specialist Document",
                task_type="document",
                input_data={"query": "List files"},
                step_number=2,
            ),
            WorkflowTaskCreate(
                name="Chitchat Direct",
                task_type="direct",
                input_data={"query": "Hello!"},
                step_number=3,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    # Setup agent test models custom output mocks
    research_res = ResearchAgentResponse(
        summary="Wellness Summary.",
        detailed_findings="Detailed Wellness Findings.",
        sources_cited=["wellness-doc"],
        confidence_score=0.9,
    )
    document_res = DocumentAgentResponse(
        response_summary="Listing files.",
        document_details="Detail list info.",
        documents_referenced=["doc-uuid"],
        operation_status="success",
    )

    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    with (
        research_agent.override(model=TestModel(custom_output_args=research_res)),
        document_agent.override(model=TestModel(custom_output_args=document_res)),
        direct_agent.override(
            model=TestModel(custom_output_text="Direct agent hello answer")
        ),
    ):
        await workflow_engine.run_workflow_context(session_factory, wf.id, user.id)

    # Reload
    db.expunge_all()
    updated_wf = await workflow_repo.get_by_id(db, wf.id, user.id)
    assert updated_wf is not None
    assert updated_wf.status == "completed"

    tasks = sorted(updated_wf.tasks, key=lambda t: t.step_number)
    assert tasks[0].status == "completed"
    t0_out = tasks[0].output_data or {}
    assert t0_out["summary"] == "Wellness Summary."

    assert tasks[1].status == "completed"
    t1_out = tasks[1].output_data or {}
    assert t1_out["response_summary"] == "Listing files."

    assert tasks[2].status == "completed"
    t2_out = tasks[2].output_data or {}
    assert t2_out["response"] == "Direct agent hello answer"


@pytest.mark.asyncio
async def test_api_run_workflow_trigger(db: AsyncSession) -> None:
    """Test triggering a workflow execution via the run API endpoint."""
    user = await user_repo.create(
        db,
        UserCreate(
            email="wf_api_run@enterprise.com",
            full_name="API Run User",
            password="password123",
            role=UserRole.USER,
        ),
        hash_password("password123"),
    )

    wf_in = WorkflowCreate(
        name="API Run Workflow",
        description="Triggers via API",
        tasks=[
            WorkflowTaskCreate(
                name="API Task",
                task_type="system",
                input_data={"message": "api run"},
                step_number=1,
            ),
        ],
    )
    wf = await workflow_repo.create(db, wf_in, user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await get_auth_headers(
            client, "wf_api_run@enterprise.com", "password123"
        )

        # Trigger run
        run_res = await client.post(f"/api/v1/workflows/{wf.id}/run", headers=headers)
        assert run_res.status_code == status.HTTP_200_OK

        # Give background task a moment to execute
        await asyncio.sleep(0.5)

        # Check details
        db.expunge_all()
        get_res = await client.get(f"/api/v1/workflows/{wf.id}", headers=headers)
        assert get_res.status_code == status.HTTP_200_OK
        data = get_res.json()
        assert data["status"] == "completed"
        assert data["tasks"][0]["status"] == "completed"
