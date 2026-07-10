"""Pytest configurations and fixtures."""

import os

os.environ["APP_ENV"] = "testing"

import asyncio
import contextlib
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app

# Explicitly import all model modules to register them on Base.metadata
from app.models import (
    approval as _app,  # noqa: F401
    audit_log as _aud,  # noqa: F401
    chat as _ch,  # noqa: F401
    department as _dep,  # noqa: F401
    document as _doc,  # noqa: F401
    notification as _not,  # noqa: F401
    team as _tm,  # noqa: F401
    user as _us,  # noqa: F401
    workflow as _wf,  # noqa: F401
)
from app.models.base import Base

# Setup file-based SQLite database for testing to ensure connection pool independence
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_temp.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db() -> AsyncGenerator[None]:
    """Initialize the database schema for the test session."""

    db_file = Path("test_temp.db")
    if db_file.exists():
        with contextlib.suppress(Exception):
            db_file.unlink()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

    if db_file.exists():
        with contextlib.suppress(Exception):
            db_file.unlink()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a database session and roll back any transactions after each test."""
    async with test_engine.connect() as connection:
        # Begin a transaction
        transaction = await connection.begin()

        async_session = TestSessionLocal(bind=connection)

        # Override dependency in app

        async def override_get_db() -> AsyncGenerator[AsyncSession]:
            yield async_session

        app.dependency_overrides[get_db] = override_get_db

        yield async_session

        # Clean up session and rollback transaction to ensure complete test isolation
        await async_session.close()
        await transaction.rollback()

        # Remove dependency override
        app.dependency_overrides.pop(get_db, None)
