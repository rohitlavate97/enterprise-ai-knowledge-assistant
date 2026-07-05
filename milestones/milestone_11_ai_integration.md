# Milestone 11: AI Integration (Tenant-Scoped Reasoning API)

## Goal
Implement a unified RAG query endpoint `/api/v1/documents/query` that coordinates document retrieval and generative reasoning. Enforce role-based scoping policies to partition data access securely.

## Status
- [x] Create Pydantic serialization schemas for `QueryRequest` and `QueryResponse` (`app/schemas/document.py`)
- [x] Register `/documents/query` endpoint with standard user and admin scoping logic (`app/api/v1/documents.py`)
- [x] Implement fallback answer handling when no matches are found or scores are below thresholds (`app/api/v1/documents.py`)
- [x] Write integration tests for multi-tenant RAG query flow (`tests/test_rag_query.py`)
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Prevent Route Shadowing:** Registering the POST `/query` endpoint before GET `/{doc_id}` stops FastAPI from capturing the query keyword as a path parameter.
- **Graceful Fallback:** When all retrieval scores fall below the similarity threshold, returning a default empty response (e.g. `answer="No relevant documents found."`, `has_sufficient_context=False`) prevents calling the LLM, preserving API quota.
- **Full Source Traceability:** QueryResponse transmits matching document chunks (`sources`) alongside the answer, enabling full explainability in the UI.

## Completed Tasks Record
* *Commit 27 (Actual):* Implement tenant-scoped reasoning and RAG query POST endpoint.
* *Commit 28 (Actual):* Write integration tests for RAG query, and update CHANGELOG.
