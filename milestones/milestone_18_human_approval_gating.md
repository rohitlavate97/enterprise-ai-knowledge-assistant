# Milestone 18: Human Approval Gating

## Goal
Implement a robust, database-backed **Human-in-the-Loop (HITL) Approval Gating** workflow. This gates all write, destructive, or externally visible actions (such as document deletion) behind a formal authorization portal.

Features:
1. **Approval Database Models**: An `ApprovalRequest` entity tracking requesters, reviewers, actions, entity payloads, and states (`pending`, `approved`, `rejected`).
2. **Agent Tool Integration**: Modify document agent's `delete_document` tool to create a pending approval request instead of executing or throwing refusions.
3. **Approval REST Endpoints**: API routes under `/api/v1/approvals` for users to list their requests and admins to review (approve/reject) them.
4. **Action Execution on Approval**: Triggering the actual document deletion (SQL record cascade + Qdrant vector point purge) automatically once approved.
5. **Streamlit UI Portal**: An "Approvals Gate" workspace tab for monitoring requests, with click-to-approve/reject capabilities for Administrators.
6. **Integration and Gating Tests**: Unit and integration tests verifying gating blocks, state updates, and secure post-approval action runs.

## Status
- [x] Create SQLAlchemy model `ApprovalRequest` + Alembic migration (`app/models/approval.py`)
- [x] Define Pydantic validation schemas (DTOs) for approvals (`app/schemas/approval.py`)
- [x] Implement `ApprovalRepository` and service actions layer (`app/repositories/approval_repository.py`)
- [x] Update `delete_document` tool in Document Agent to submit approval requests (`app/services/document_agent.py`)
- [x] Register FastAPI router and endpoints under `/api/v1/approvals` (`app/api/v1/approvals.py`)
- [x] Write integration and approval-gating tests (`tests/test_human_approval.py`)
- [x] Create "Approvals Gate" workspace tab in Streamlit frontend (`frontend/app.py`)
- [x] Verify Ruff linting and MyPy type safety pass cleanly

## Key Technical Decisions & Justifications
- **Stateful Request Tracking**: Storing request payloads and metadata in the database guarantees persistence, traceability of administrative actions, and auditability.
- **Asynchronous Execution Post-Approval**: Once approved by an Admin via the REST endpoint, the target operation (e.g. document deletion) is run inline or dispatched to background workers, immediately releasing the request thread.

## Completed Tasks Record
* *Commit 50 (Completed):* Create SQLAlchemy model for ApprovalRequest, register base metadata, and generate Alembic migrations.
* *Commit 51 (Completed):* Create Pydantic DTO validation schemas.
* *Commit 52 (Completed):* Implement Approval Repository layer and wire get/list/update operations.
* *Commit 53 (Completed):* Integrate approval creation into document agent's delete_document tool.
* *Commit 54 (Completed):* Implement FastAPI endpoints under `/api/v1/approvals`.
* *Commit 55 (Completed):* Write pytest integration tests for approval gating and execution.
* *Commit 56 (Completed):* Add Approvals Portal tab to Streamlit app.py.
* *Commit 57 (Completed):* Verify Ruff, MyPy, and Pytest pass, and update CHANGELOG.
