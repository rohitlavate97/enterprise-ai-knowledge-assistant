"""Background task service for processing and ingestion of documents."""

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.document_chunker import chunk_text
from app.services.document_parser import extract_text
from app.services.document_service import document_service
from app.services.vector_service import vector_service

logger = logging.getLogger(__name__)


async def process_document_task(
    session_factory: async_sessionmaker[AsyncSession],
    doc_id: UUID,
) -> None:
    """Asynchronously parses, chunks, and indexes a document in the background.

    Coordinates extraction, chunking, and later vector database storage.
    """
    logger.info("Starting background document processing for doc_id: %s", doc_id)

    async with session_factory() as db:
        try:
            # 1. Update status to 'processing'
            db_doc = await document_service.update_document_status(
                db, doc_id, "processing"
            )
            logger.info("Document %s status updated to 'processing'", doc_id)

            # 2. Parse text content from storage
            file_path = Path(db_doc.file_path)
            extracted_text = await extract_text(file_path, db_doc.mime_type)
            logger.info(
                "Successfully extracted %d characters from %s",
                len(extracted_text),
                db_doc.filename,
            )

            # 3. Chunk text content recursively
            chunks = chunk_text(extracted_text)
            logger.info(
                "Generated %d chunks for document %s",
                len(chunks),
                db_doc.filename,
            )


            vector_service.index_document_chunks(
                doc_id=db_doc.id,
                chunks=chunks,
                user_id=db_doc.user_id,
                department_id=db_doc.department_id,
                team_id=db_doc.team_id,
            )
            logger.info(
                "Successfully indexed %d chunks in vector database", len(chunks)
            )

            # 4. Update status to 'completed'
            await document_service.update_document_status(
                db, doc_id, "completed"
            )
            logger.info("Document %s processing successfully completed", doc_id)

        except Exception as e:
            logger.error(
                "Error processing document %s: %s", doc_id, str(e), exc_info=True
            )
            # Update status to 'failed'
            try:
                await document_service.update_document_status(db, doc_id, "failed")
            except Exception as inner_err:
                logger.error(
                    "Failed to mark document %s as failed: %s",
                    doc_id,
                    str(inner_err),
                )
