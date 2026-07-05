"""Integration and API tests for Document management and background processing."""

import io
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.repositories.user_repository import user_repo
from app.schemas.user import UserCreate, UserRole
from app.services.document_service import document_service


async def get_auth_headers(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    """Helper function to login a user and return authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_document_upload_and_processing_flow(db: AsyncSession) -> None:
    """Test uploading a document, background task execution, and deletion."""
    # 1. Create a user
    user_in = UserCreate(
        email="uploader@enterprise.com",
        full_name="Document Uploader",
        password="password123",
        role=UserRole.USER,
    )
    await user_repo.create(db, user_in, hash_password("password123"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        auth_headers = await get_auth_headers(
            client, "uploader@enterprise.com", "password123"
        )

        # 2. Upload file
        file_content = b"This is a test document containing text for parsing."
        file_data = {
            "file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")
        }

        # Override upload directory config to point to a test subfolder
        settings.UPLOAD_DIR = "storage/test_documents"

        res = await client.post(
            "/api/v1/documents/upload",
            files=file_data,
            headers=auth_headers,
        )
        assert res.status_code == status.HTTP_201_CREATED
        doc_data = res.json()
        doc_id = doc_data["id"]
        assert doc_data["filename"] == "test_doc.txt"
        assert doc_data["file_size"] == len(file_content)

        # 3. Check physical file exists
        db_doc = await document_service.get_document(db, UUID(doc_id))
        saved_file_path = Path(db_doc.file_path)
        assert saved_file_path.exists()
        assert saved_file_path.read_bytes() == file_content

        # 4. Fetch details to check status transitions
        res = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        # The background task completes synchronously, updating the status to completed
        assert res.json()["status"] == "completed"

        # 5. List documents
        res = await client.get("/api/v1/documents/", headers=auth_headers)
        assert res.status_code == status.HTTP_200_OK
        assert len(res.json()) >= 1

        # 6. Delete document
        res = await client.delete(
            f"/api/v1/documents/{doc_id}", headers=auth_headers
        )
        assert res.status_code == status.HTTP_204_NO_CONTENT

        # 7. Check physical file and DB record are deleted
        assert not saved_file_path.exists()

        with pytest.raises(HTTPException):
            await document_service.get_document(db, UUID(doc_id))
