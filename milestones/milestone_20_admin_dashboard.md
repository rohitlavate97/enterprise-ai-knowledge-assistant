# Milestone 20: Admin Dashboard

## Goal
Implement a comprehensive, secure **Admin Dashboard** allowing Administrators to monitor system health in real-time, view usage analytics, manage users/roles, inspect audit logs, and oversee documents and workflows.

Features:
1. **Audit Logging Infrastructure**: An `AuditLog` database model + Alembic migration tracking actions (user access, agent runs, document uploads/deletions, and approval decisions).
2. **Admin Analytics API**: Endpoint `GET /api/v1/admin/analytics` yielding metrics on user counts, document storage sizing, ingestion statuses, and active workflows.
3. **Live System Health WebSocket**: An endpoint `WS /api/v1/admin/system-health/ws` pushing real-time metrics (CPU, RAM, database latency) with resilient frontend reconnection handling.
4. **FastAPI Endpoints for Audit Logs**: Admin-only paginated endpoint to query audit logs.
5. **Streamlit UI Interface**:
   - Metrics cards showing system-wide statistics.
   - Visual charts displaying document ingestion status and workflow state breakdowns.
   - Live WebSocket-driven system health panel.
   - User and team listing panels.
   - Searchable, paginated Audit Log inspection table.
6. **Unit and Integration Tests**: Pytest verification for analytics endpoints, audit log generation, and WebSocket connections.

## Status
- [ ] Create SQLAlchemy model `AuditLog` + Alembic migration (`app/models/audit_log.py`)
- [ ] Define Pydantic validation schemas (DTOs) for analytics and audit logs (`app/schemas/admin.py`)
- [ ] Implement `AuditLogRepository` and logging helper service (`app/repositories/audit_log_repository.py`)
- [ ] Register FastAPI router and endpoints under `/api/v1/admin` (`app/api/v1/admin.py`)
- [ ] Implement WebSocket endpoint for live health updates (`app/api/v1/admin.py`)
- [ ] Add audit logging triggers to RAG query, document upload, workflow run, and approval decisions
- [ ] Write integration and WebSocket tests (`tests/test_admin_dashboard.py`)
- [ ] Create "Admin Dashboard" workspace tab in Streamlit frontend (`frontend/app.py`)
- [ ] Verify Ruff linting and MyPy type safety pass cleanly

## Key Technical Decisions & Justifications
- **Structured Audit Logging**: Storing audit records with JSON payloads captures the exact context of write and reasoning actions, establishing accountability.
- **WebSocket Health Push**: Shifting health updates from REST polling to a WebSocket stream reduces server-side database workload and provides instant UI responsiveness.

## Completed Tasks Record
* *Commit 66 (Planned):* Create SQLAlchemy model for AuditLog, register metadata, and generate Alembic migration.
* *Commit 67 (Planned):* Create Pydantic DTO validation schemas for analytics and audit logs.
* *Commit 68 (Planned):* Implement Audit Log repository and central tracking helpers.
* *Commit 69 (Planned):* Implement FastAPI REST and WebSocket endpoints.
* *Commit 70 (Planned):* Wire audit logging triggers into API routes and workflow loop.
* *Commit 71 (Planned):* Write pytest integration tests for analytics and health WebSockets.
* *Commit 72 (Planned):* Build the Admin Dashboard tab in Streamlit app.py.
* *Commit 73 (Planned):* Verify Ruff, MyPy, and Pytest pass, and update CHANGELOG.
