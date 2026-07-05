# Milestone 7: Document Ingestion and Chunking (Pipeline)

## Goal
Implement a text extraction parser supporting `.txt`, `.md`, and `.pdf` formats, and design a recursive semantic text chunker that preserves sentence and paragraph integrity. Update the background ingestion task to orchestrate extraction and chunking.

## Status
- [x] Install and configure `pypdf` dependency (`requirements.txt`)
- [x] Create text extraction adapter for TXT, Markdown, and PDF formats (`app/services/document_parser.py`)
- [x] Create recursive sliding-window semantic text chunker (`app/services/document_chunker.py`)
- [x] Update background document processing task to orchestrate parsing and chunking (`app/services/document_processing.py`)
- [x] Write integration and pipeline tests validating parsing formats, chunk sizes, and overlaps
- [x] Verify MyPy typing and Ruff linting rules pass cleanly

## Key Technical Decisions & Justifications
- **Recursive Chunking State Machine:** Encapsulating current chunk buffers in a `ChunkerState` class prevents complex parameter passing, improves separation of concerns, and simplifies boundary splits.
- **Dynamic Session Factory in Workers:** Instantiating database connections from `db.bind` inside routes ensures database transactions are executed against the exact same dialect as the request, preventing connection failures in offline tests.

## Completed Tasks Record
* *Commit 19 (Actual):* Implement document parser, semantic chunker, and coordinate processing worker.
* *Commit 20 (Actual):* Write test suites for text extraction and chunking pipeline.
