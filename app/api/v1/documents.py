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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_log_repository import audit_log_repo
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    QueryRequest,
    QueryResponse,
    SearchResultResponse,
)
from app.schemas.user import UserRole
from app.services.ai_service import ai_service
from app.services.document_processing import process_document_task
from app.services.document_service import document_service
from app.services.vector_service import vector_service

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

    # Log document upload audit action

    await audit_log_repo.log(
        db,
        action="UPLOAD_DOCUMENT",
        details=f"Uploaded document '{db_doc.title}' (ID: {db_doc.id}).",
        user_id=current_user.id,
        payload={"document_id": str(db_doc.id), "title": db_doc.title},
    )

    # 6. Trigger asynchronous background processing task
    session_factory = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    background_tasks.add_task(process_document_task, session_factory, db_doc.id)

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


@router.get("/search", response_model=list[SearchResultResponse])
async def search_documents(  # noqa: PLR0913
    query: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 5,
    threshold: float = 0.3,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
) -> Any:
    """Perform semantic search across document chunks.

    Access scopes:
    - Standard Users are restricted to their own department (and optionally
      team) documents.
    - Admins and Superadmins can query globally or override with any
      department/team scope.
    """
    # 1. Enforce RBAC tenant scoping rules
    if current_user.role != UserRole.ADMIN:
        # Standard user is locked to their own department
        target_department_id = current_user.department_id
        target_team_id = (
            team_id if team_id == current_user.team_id else current_user.team_id
        )

        # If user is not in any department, they cannot view department-scoped documents
        if target_department_id is None:
            return []
    else:
        # Admins can query globally or filter by requested parameters
        target_department_id = department_id
        target_team_id = team_id

    # 2. Invoke vector search
    results = vector_service.search_similar_chunks(
        query=query,
        limit=limit,
        department_id=target_department_id,
        team_id=target_team_id,
    )

    # 3. Filter by similarity threshold
    return [r for r in results if r["score"] >= threshold]


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> Any:
    """Coordinate RAG operations: retrieve matching document chunks, then reason.

    Access scopes:
    - Standard Users are restricted to their own department (and optionally
      team) documents.
    - Admins can query globally or override with any department/team scope.
    """
    # 1. Enforce RBAC tenant scoping rules
    if current_user.role != UserRole.ADMIN:
        # Standard user is locked to their own department
        target_department_id = current_user.department_id
        target_team_id = (
            request.team_id
            if request.team_id == current_user.team_id
            else current_user.team_id
        )

        # If user is not in any department, they cannot view documents
        if target_department_id is None:
            return QueryResponse(
                answer="No relevant documents found.",
                has_sufficient_context=False,
                confidence_score=0.0,
                sources=[],
            )
    else:
        # Admins can query globally or filter by requested parameters
        target_department_id = request.department_id
        target_team_id = request.team_id

    # 2. Retrieve matching chunks from Vector DB
    results = vector_service.search_similar_chunks(
        query=request.question,
        limit=request.limit,
        department_id=target_department_id,
        team_id=target_team_id,
    )

    # 3. Filter by similarity threshold
    sources = [r for r in results if r["score"] >= request.threshold]

    # 4. If no sources found, return empty query response
    if not sources:
        return QueryResponse(
            answer="No relevant documents found.",
            has_sufficient_context=False,
            confidence_score=0.0,
            sources=[],
        )

    # 5. Compile context and call PydanticAI reasoning layer
    context_chunks = [s["text"] for s in sources]
    agent_res = await ai_service.answer_with_context(
        question=request.question,
        context_chunks=context_chunks,
    )

    # Convert dictionary matches to SearchResultResponse models
    source_responses = [SearchResultResponse(**s) for s in sources]

    return QueryResponse(
        answer=agent_res.answer,
        has_sufficient_context=agent_res.has_sufficient_context,
        confidence_score=agent_res.confidence_score,
        sources=source_responses,
    )


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

    vector_service.delete_document_points(doc_id)

    # Remove database record
    await document_service.delete_document_record(db, doc_id)

    # Log document deletion audit action

    await audit_log_repo.log(
        db,
        action="DELETE_DOCUMENT",
        details=f"Deleted document '{db_doc.title}' (ID: {db_doc.id}).",
        user_id=current_user.id,
        payload={"document_id": str(db_doc.id), "title": db_doc.title},
    )
