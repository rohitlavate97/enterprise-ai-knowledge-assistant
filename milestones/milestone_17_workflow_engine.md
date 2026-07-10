# Milestone 17: Workflow Engine (Conditional Routing, Retry Logic, Scheduling)

## Goal
Implement a robust, database-backed **Workflow Engine** capable of coordinating multi-step execution graphs. The engine must support:
1. **Conditional Routing**: Dynamically determining which task to run next based on the output or status of previous tasks.
2. **Retry Logic**: Automatically retrying failed tasks with configurable delays and backoff.
3. **Scheduling**: Deferring task execution to a specific future timestamp.
4. **Multi-Agent & Specialist Tasks**: Enabling workflow tasks to run specialist agents (Research or Document) or execute custom system/utility tasks.
5. **Streamlit UI Integration**: A dedicated tab to define, trigger, and monitor workflows and task statuses in near-real-time.
6. **Comprehensive Test Suite**: Verifying routing, retries, scheduling, and API correctness.

## Status
- [x] Create SQLAlchemy models for `Workflow` and `WorkflowTask` + Alembic migration (`app/models/workflow.py`)
- [x] Define Pydantic schemas (DTOs) for Workflows and Tasks (`app/schemas/workflow.py`)
- [x] Implement `WorkflowRepository` and `WorkflowEngineService` with execution logic, retry management, conditional routing, and scheduling support (`app/services/workflow_engine.py` / `app/repositories/workflow_repo.py`)
- [x] Register FastAPI router and endpoints under `/api/v1/workflows` (`app/api/v1/workflows.py`)
- [x] Write unit, integration, and API tests (`tests/test_workflow_engine.py`)
- [x] Add a "Workflow Engine" workspace tab in the Streamlit frontend (`frontend/app.py` or separate UI file if needed)
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Database-Backed State Machine**: Storing both workflows and individual tasks in the database guarantees persistence, auditability of run history, and recovery of execution state across restarts.
- **In-Memory/Async Background Task Runner**: Since heavy Celery queues are optional and Docker is not running in the developer environment, we will use a native async task scheduler runner loop using FastAPI's background tasks or `asyncio.create_task`. This is highly testable and robust for local development while remaining compatible with a worker model.
- **DAG/JSON Routing Matrix**: Each task can define conditional routes (e.g. `{"success": "next_task_uuid", "failure": "error_handler_task_uuid"}`) or state-driven transitions via simple key lookup in `conditional_routes`.

## Completed Tasks Record
* *Commit 43:* Create SQLAlchemy models for Workflow and WorkflowTask, register them in Base metadata, and generate Alembic migrations.
* *Commit 44:* Create Pydantic validation schemas (DTOs) for Workflow and WorkflowTask, resolving field deprecations.
* *Commit 45:* Implement Workflow repository and core WorkflowEngineService service layer supporting execution, retries, scheduling, and routing.
* *Commit 46:* Implement FastAPI routes under `/api/v1/workflows` and register them in the router.
* *Commit 47:* Write comprehensive async tests for routing, scheduling, retries, and endpoints, utilizing connection-bound sessionmaker.
* *Commit 48:* Add Workflow Engine interface tab to Streamlit app.py, implementing near-real-time polling auto-refresh.
* *Commit 49:* Verify Ruff linting, MyPy typing, and Pytest pass, and update CHANGELOG and Milestones.
