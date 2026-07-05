# Milestone 8: Vector Database Foundation (Qdrant + SentenceTransformers integration)

## Goal
Establish a vector search engine client using Qdrant and a local embedding service using HuggingFace's `SentenceTransformer` (lazy-loaded). Integrate point indexing and scoped tenant filters.

## Status
- [x] Install and configure `sentence-transformers` dependency (`requirements.txt`)
- [x] Create Qdrant vector database client provider (`app/core/vector_db.py`)
- [x] Implement lazy-loaded local SentenceTransformer embedding service (`app/services/embedding_service.py`)
- [x] Implement indexing, point deletion, and scoped search operations (`app/services/vector_service.py`)
- [x] Integrate vector indexing in background document processing pipeline (`app/services/document_processing.py`)
- [x] Integrate vector cleanup in document deletion route (`app/api/v1/documents.py`)
- [x] Write integration and unit tests validating query similarity searches and tenant filters
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Modern query_points API:** Using Qdrant Client's unified `query_points` API ensures support for newer features and cross-engine (in-memory and remote server) compatibility.
- **Lazy Model Loading:** Instantiating the SentenceTransformer model on the first request property access prevents startup latency during app loading and imports.
- **Isolated Testing Configuration:** Setting `APP_ENV="testing"` at the top of the conftest file forces in-memory client operations, allowing isolated local testing with 0 external dependency requirements.

## Completed Tasks Record
* *Commit 21 (Actual):* Implement Qdrant database client and SentenceTransformers embedding service.
* *Commit 22 (Actual):* Write test suites for vector indexing and semantic search, and update CHANGELOG.
