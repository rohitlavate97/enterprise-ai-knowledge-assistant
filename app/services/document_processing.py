"""Background task service for processing and ingestion of documents."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.document_service import document_service

logger = logging.getLogger(__name__)


async def process_document_task(
    session_factory: async_sessionmaker[AsyncSession],
    doc_id: UUID,
) -> None:
    """Asynchronously parses, chunks, and indexes a document in the background.

    This serves as a placeholder for the future RAG processing pipeline.
    """
    logger.info("Starting background document processing for doc_id: %s", doc_id)

    async with session_factory() as db:
        try:
            # 1. Update status to 'processing'
            await document_service.update_document_status(db, doc_id, "processing")
            logger.info("Document %s status updated to 'processing'", doc_id)

            # 2. Simulate document parsing and chunking delay
            await asyncio.sleep(2)

            # 3. Update status to 'completed'
            await document_service.update_document_status(db, doc_id, "completed")
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
