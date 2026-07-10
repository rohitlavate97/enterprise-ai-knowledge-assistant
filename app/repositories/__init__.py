"""Database repository modules (data access layer)."""

from app.repositories.chat_repository import chat_repo
from app.repositories.department_repository import department_repo
from app.repositories.document_repository import document_repo
from app.repositories.team_repository import team_repo
from app.repositories.user_repository import user_repo
from app.repositories.workflow_repository import workflow_repo

__all__ = [
    "chat_repo",
    "department_repo",
    "document_repo",
    "team_repo",
    "user_repo",
    "workflow_repo",
]
