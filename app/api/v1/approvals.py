"""FastAPI router for Human-in-the-Loop approvals management."""

import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.approval_repository import approval_repo
from app.schemas.approval import ApprovalRequestResponse, ApprovalRequestReview
from app.schemas.user import UserRole
from app.services.document_service import document_service
from app.services.vector_service import vector_service

router = APIRouter(prefix="/approvals", tags=["approvals"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=list[ApprovalRequestResponse])
async def list_approvals(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    pending_only: bool = False,
) -> Any:
    """List approval requests.

    Administrators see all requests. Standard users only see their own.
    """
    if current_user.role == UserRole.ADMIN:
        if pending_only:
            return await approval_repo.list_pending(db, skip=skip, limit=limit)
        return await approval_repo.list_all(db, skip=skip, limit=limit)

    return await approval_repo.list_by_user(db, current_user.id, skip=skip, limit=limit)


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval(
    request_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Retrieve details of a specific approval request."""
    req = await approval_repo.get_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found.",
        )

    # Scoping check: Users can only see their own requests
    if current_user.role != UserRole.ADMIN and req.requested_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to other users' requests.",
        )

    return req


@router.post("/{request_id}/review", response_model=ApprovalRequestResponse)
async def review_approval(
    request_id: UUID,
    review_in: ApprovalRequestReview,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Approve or reject a pending approval request.

    Only accessible by users with Admin role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can review approval requests.",
        )

    req = await approval_repo.get_by_id(db, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found.",
        )

    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request is already processed.",
        )

    # 1. Update status
    updated_req = await approval_repo.update_status(
        db,
        req,
        status=review_in.status,
        reviewer_id=current_user.id,
        rejection_reason=review_in.rejection_reason,
        comment=review_in.comment,
    )

    # 2. If approved, execute action
    if (
        review_in.status == "approved"
        and updated_req.action_type == "delete_document"
    ):
        doc_id_str = updated_req.payload.get("document_id")
        if not doc_id_str:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing 'document_id' in action payload.",
            )

        try:
            doc_id = UUID(doc_id_str)
            # Fetch record first to get file path
            db_doc = await document_service.get_document(db, doc_id)

            # Remove file from disk
            file_path = Path(db_doc.file_path)
            if file_path.exists():
                file_path.unlink()

            # Purge vector index
            vector_service.delete_document_points(doc_id)

            # Remove database record
            await document_service.delete_document_record(db, doc_id)
            logger.info("Approval Gate: Document %s successfully deleted.", doc_id)
        except Exception as err:
            logger.error("Approval Gate execution failed: %s", str(err))
            # Update status back to pending or failed if execution fails?
            # Usually we raise error, but db transaction is committed for review
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Approved action execution failed: {str(err)}",
            ) from err

    return updated_req
