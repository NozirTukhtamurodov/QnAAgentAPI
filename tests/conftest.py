"""Pytest configuration and shared fixtures."""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.models import Base
from api.app import AppBuilder


@pytest_asyncio.fixture
async def test_db_engine():
    """Create a test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an HTTP client for testing with initialized app."""
    # Create a new app builder instance for each test
    app_builder = AppBuilder()

    # Override the database engine with test engine
    app_builder._async_engine = test_db_engine
    app_builder._session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Initialize other required resources
    from config import Settings
    from infrastructure.openai_client import OpenAIClient
    from logic.common import KnowledgeBaseService

    settings = Settings()
    app_builder._openai_client = OpenAIClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        timeout=settings.openai_timeout,
        max_retries=settings.openai_max_retries,
    )
    app_builder._kb_service = KnowledgeBaseService(settings.knowledge_base_dir)

    # Create client with the configured app
    async with AsyncClient(
        transport=ASGITransport(app=app_builder.app),
        base_url="http://test",
    ) as ac:
        yield ac
