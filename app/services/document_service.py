"""Document management business logic service."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.document_repository import document_repo
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Service class for Document-related business operations."""

    async def create_document_record(
        self, db: AsyncSession, doc_in: DocumentCreate
    ) -> Document:
        """Create a new document metadata record."""
        return await document_repo.create(db, doc_in)

    async def get_document(self, db: AsyncSession, doc_id: UUID) -> Document:
        """Retrieve a document or raise 404 Not Found."""
        doc = await document_repo.get_by_id(db, doc_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )
        return doc

    async def list_documents(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """List all documents with pagination support."""
        return await document_repo.get_multi(db, skip=skip, limit=limit)

    async def update_document_status(
        self, db: AsyncSession, doc_id: UUID, new_status: str
    ) -> Document:
        """Update a document's processing status."""
        db_doc = await self.get_document(db, doc_id)
        update_in = DocumentUpdate(status=new_status)
        return await document_repo.update(db, db_doc, update_in)

    async def delete_document_record(self, db: AsyncSession, doc_id: UUID) -> Document:
        """Delete a document record from the database and return it."""
        db_doc = await self.get_document(db, doc_id)
        await document_repo.delete(db, db_doc)
        return db_doc


document_service = DocumentService()
