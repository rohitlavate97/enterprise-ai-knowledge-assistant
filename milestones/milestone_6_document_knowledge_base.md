# Milestone 6: Document Knowledge Base (SQL Schema, CRUD, Upload, RAG Processing Placeholder)

## Goal
Implement the document metadata relational schemas, storage configurations, upload handler, CRUD endpoints, and asynchronous background task placeholders to support the document knowledge base.

## Status
- [ ] Create SQLAlchemy database model for `Document` (`app/models/document.py`)
- [ ] Generate Alembic schema migration script for the `documents` table
- [ ] Create Pydantic DTO schemas for Documents (`app/schemas/document.py`)
- [ ] Implement database repository and service layer operations for Documents
- [ ] Setup secure document storage directories and local storage adapters
- [ ] Implement FastAPI endpoints for document upload, retrieval, and deletion
- [ ] Setup background task placeholders for document parsing/ingestion pipelines
- [ ] Write integration and API tests validating document CRUD, uploads, and status flows

## Key Technical Decisions & Justifications
- **Status-Driven Processing:** Documents follow a lifecycle state (`pending` -> `processing` -> `completed` / `failed`) to handle large-file asynchronous processing without blocking web requests.
- **FastAPI BackgroundTasks:** Lightweight, native async execution for triggerable background processing, suitable for prototype and early production stages before heavy Celery message broker queues are introduced.
- **Strict Tenant Partitioning:** Documents are optionally linked to `department_id` and `team_id` to support granular access control policies later.

## Completed Tasks Record
* *Commit 15 (Planned):* Create Document database model and generate migration.
* *Commit 16 (Planned):* Create Document Pydantic schemas, repository, and service.
* *Commit 17 (Planned):* Implement document storage adapter, background task, and upload router.
* *Commit 18 (Planned):* Write test suites for Document APIs and update CHANGELOG.
