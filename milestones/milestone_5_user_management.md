# Milestone 5: User Management (Profiles, Teams, Departments, Roles)

## Goal
Extend the domain model and database schema to support Departments, Teams, and expanded User Profiles. Implement the repository, service, and API layers to manage these entities and support Role-Based Access Control (RBAC) constraints on administrative features.

## Status
- [x] Create SQLAlchemy models for `Department` and `Team`, and update `User` with foreign key relationships (`app/models/`)
- [x] Generate Alembic schema migration script for departments and teams tables
- [x] Create Pydantic DTO schemas for Departments, Teams, and profile updates (`app/schemas/`)
- [x] Implement database repository and service layer operations for Department and Team management
- [x] Implement FastAPI endpoints for CRUD operations on departments and teams, and assigning users
- [x] Write integration and API tests validating department/team constraints, user profile updates, and RBAC protection

## Key Technical Decisions & Justifications
- **Nullable Foreign Keys for Users:** Linking `department_id` and `team_id` as nullable columns on the `User` model ensures that system administrators and external actors do not require rigid corporate org mapping on initialization.
- **Cascading Constraints:** Deleting a department can cascade-nullify or block team/user deletion based on referential integrity checks, protecting against orphan data.

## Completed Tasks Record
* *Commit 10 (Actual):* Define Department and Team SQLAlchemy models and update User model + migration.
* *Commit 11 (Actual):* Define Pydantic schemas for Departments and Teams.
* *Commit 12 (Actual):* Create repository and service layers for Departments and Teams.
* *Commit 13 (Actual):* Implement FastAPI routers and endpoints.
* *Commit 14 (Actual):* Write test suites for User Management APIs and update docs.
