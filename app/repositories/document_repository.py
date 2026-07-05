"""Database Repository for Document models using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentRepository:
    """Database repository layer for managing Document records."""

    async def get_by_id(self, db: AsyncSession, doc_id: UUID) -> Document | None:
        """Retrieve a document by its unique UUID."""
        query = select(Document).where(Document.id == doc_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, doc_in: DocumentCreate) -> Document:
        """Create a new document metadata record."""
        db_doc = Document(
            title=doc_in.title,
            filename=doc_in.filename,
            file_path=doc_in.file_path,
            file_size=doc_in.file_size,
            mime_type=doc_in.mime_type,
            status=doc_in.status,
            user_id=doc_in.user_id,
            department_id=doc_in.department_id,
            team_id=doc_in.team_id,
        )
        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)
        return db_doc

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """List documents with pagination."""
        query = select(Document).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_by_user(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """List documents uploaded by a specific user."""
        query = (
            select(Document)
            .where(Document.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def list_by_department(
        self, db: AsyncSession, dep_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """List documents associated with a specific department."""
        query = (
            select(Document)
            .where(Document.department_id == dep_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, db: AsyncSession, db_doc: Document, doc_in: DocumentUpdate
    ) -> Document:
        """Update a document record (metadata or status)."""
        update_data = doc_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_doc, field, value)
        db.add(db_doc)
        await db.commit()
        await db.refresh(db_doc)
        return db_doc

    async def delete(self, db: AsyncSession, db_doc: Document) -> None:
        """Delete a document metadata record."""
        await db.delete(db_doc)
        await db.commit()


document_repo = DocumentRepository()
