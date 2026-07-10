# Milestone 19: Notifications

## Goal
Implement a robust, database-backed **Notifications Module** to deliver real-time and persistent alerts to users and administrators for workflow events, approval requests, and system actions.

Features:
1. **Notification Database Models**: A `Notification` entity tracking recipient user, title, message, type (info, warning, success, approval, workflow), read status, and timestamps.
2. **REST API Endpoints**: Routes under `/api/v1/notifications` for listing notifications, marking individual or all notifications as read.
3. **Event-Driven Notification Triggers**:
   - Trigger notification to Admins when a new approval request is submitted.
   - Trigger notification to requester when an approval request is approved or rejected.
   - Trigger notification to owner when a workflow execution completes or fails.
4. **Streamlit UI Integration**:
   - A "Notifications Hub" tab for users to view, read, and manage persistent alerts.
   - Real-time toast notifications (`st.toast`) showing immediate popups for new notifications during interactive sessions.
5. **Unit and Integration Tests**: Test suite verifying creation, filtering, status transitions, and integration with workflows and approvals.

## Status
- [ ] Create SQLAlchemy model `Notification` + Alembic migration (`app/models/notification.py`)
- [ ] Define Pydantic validation schemas (DTOs) for notifications (`app/schemas/notification.py`)
- [ ] Implement `NotificationRepository` (`app/repositories/notification_repository.py`)
- [ ] Register FastAPI router and endpoints under `/api/v1/notifications` (`app/api/v1/notifications.py`)
- [ ] Wire notification triggers into Approval review flow and Workflow engine loop
- [ ] Write integration and unit tests (`tests/test_notifications.py`)
- [ ] Add Notifications UI & Toast Alert Polling in Streamlit frontend (`frontend/app.py`)
- [ ] Verify Ruff linting and MyPy type safety pass cleanly

## Key Technical Decisions & Justifications
- **Persistent Database Auditing**: Alerts must be persistent in the database to allow users to review past events even after closing the web app.
- **Short-Interval Polling for Toasts**: Utilizing Streamlit's rerun execution model coupled with background polling of the unread notifications count lets us render toast alerts dynamically.

## Completed Tasks Record
* *Commit 58 (Planned):* Create SQLAlchemy model for Notification, register metadata, and generate Alembic migration.
* *Commit 59 (Planned):* Create Pydantic DTO validation schemas.
* *Commit 60 (Planned):* Implement Notification Repository layer.
* *Commit 61 (Planned):* Implement FastAPI endpoints under `/api/v1/notifications`.
* *Commit 62 (Planned):* Integrate notification triggers into approvals and workflows.
* *Commit 63 (Planned):* Write pytest integration tests for notifications.
* *Commit 64 (Planned):* Add Notifications Hub tab and Toast Alert polling to Streamlit app.py.
* *Commit 65 (Planned):* Verify Ruff, MyPy, and Pytest pass, and update CHANGELOG.
