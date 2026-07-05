# Milestone 9: Knowledge Retrieval (Semantic Search API)

## Goal
Implement a tenant-scoped semantic search API endpoint `/api/v1/documents/search` allowing users to query document chunks. Enforce strict role-based access control (RBAC) scopes to prevent unauthorized access across corporate partitions.

## Status
- [x] Create Pydantic serialization schema for similarity search matches (`app/schemas/document.py`)
- [x] Correct mapping bug in `UserRepository.create` to store `department_id`/`team_id` assignments (`app/repositories/user_repository.py`)
- [x] Implement tenant-scoped semantic search endpoint `/documents/search` with threshold filters (`app/api/v1/documents.py`)
- [x] Write integration and scoped search API tests (`tests/test_document_search.py`)
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Prevent Route Shadowing:** Placing the `/search` route before the `/{doc_id}` route prevents FastAPI from hijacking the search keyword as a path parameter, avoiding 422 errors.
- **Strict Tenant-Scoping Policy:** Standard users are programmatically locked to their own department (and optionally team) ID constraints, preventing cross-tenant data leakage. Admins can search globally or scope overrides.
- **Confidence Threshold Filtering:** Filtering outputs by a similarity score threshold (defaulting to 0.3) prevents irrelevant chunks with near-zero or negative similarity scores from contaminating search results.

## Completed Tasks Record
* *Commit 23 (Actual):* Implement tenant-scoped semantic search router and user model mappings.
* *Commit 24 (Actual):* Write integration tests for semantic search, and update CHANGELOG.
