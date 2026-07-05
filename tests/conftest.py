"""Pytest configurations and fixtures."""

import os

os.environ["APP_ENV"] = "testing"

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.base import Base

# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


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
