"""FastAPI router for Document upload and management."""

import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.document_processing import process_document_task
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(  # noqa: PLR0913
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: Annotated[UUID | None, Form()] = None,
    team_id: Annotated[UUID | None, Form()] = None,
) -> Any:
    """Upload a document to the knowledge base and trigger background processing."""
    # 1. Create upload folder if it doesn't exist
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)

    # 2. Prevent directory traversal attacks by securing filename
    safe_filename = Path(file.filename or "uploaded_file").name

    # 3. Read file content to get size
    content = await file.read()
    file_size = len(content)

    # Generate unique storage filename
    storage_filename = f"{uuid4()}_{safe_filename}"
    file_path = upload_path / storage_filename

    # 4. Save file to disk
    try:
        with file_path.open("wb") as f:
            f.write(content)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file to disk: {str(err)}",
        ) from err

    # 5. Create database record
    doc_in = DocumentCreate(
        title=safe_filename,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        status="pending",
        user_id=current_user.id,
        department_id=department_id,
        team_id=team_id,
    )

    db_doc = await document_service.create_document_record(db, doc_in)

    # 6. Trigger asynchronous background processing task
    background_tasks.add_task(process_document_task, SessionLocal, db_doc.id)

    return db_doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all documents. Requires authentication."""
    _ = current_user
    return await document_service.list_documents(db, skip=skip, limit=limit)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """Retrieve document details by UUID. Requires authentication."""
    _ = current_user
    return await document_service.get_document(db, doc_id)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a document record and its physical file. Requires authentication."""
    _ = current_user
    # Fetch record first to get file path
    db_doc = await document_service.get_document(db, doc_id)

    # Remove file from disk if it exists
    file_path = Path(db_doc.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as err:
            # Log deletion error but proceed to remove database record
            logger.error(
                "Could not delete physical file at %s: %s",
                db_doc.file_path,
                str(err),
            )

    # Remove database record
    await document_service.delete_document_record(db, doc_id)
