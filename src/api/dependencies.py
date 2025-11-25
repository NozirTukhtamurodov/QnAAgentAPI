"""Dependency injection placeholders for FastAPI.

These functions are overridden by AppBuilder at runtime.
Services use these via Depends() for automatic dependency injection.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Settings
from infrastructure.openai_client import OpenAIClient
from logic.chat import AgentService
from logic.common import KnowledgeBaseService
from logic.sessions import SessionService
from repositories.message_repository import MessageRepository
from repositories.session_repository import SessionRepository
from repositories.summary_repository import SummaryRepository


# Placeholder dependencies - will be overridden by AppBuilder
def get_db() -> async_sessionmaker[AsyncSession]:
    """Database session maker dependency.

    This is a placeholder that will be overridden by AppBuilder.
    Use with FastAPI Depends():
        db: async_sessionmaker[AsyncSession] = Depends(get_db)

    Returns:
        async_sessionmaker: Session maker instance

    Raises:
        NotImplementedError: If called before AppBuilder initialization
    """
    raise NotImplementedError("Database session maker not initialized. Use AppBuilder.")


def get_settings() -> Settings:
    """Application settings dependency.

    This is a placeholder that will be overridden by AppBuilder.
    Use with FastAPI Depends():
        settings: Settings = Depends(get_settings)

    Returns:
        Settings: Application settings

    Raises:
        NotImplementedError: If called before AppBuilder initialization
    """
    raise NotImplementedError("Settings not initialized. Use AppBuilder.")


def get_openai_client() -> OpenAIClient:
    """OpenAI client dependency.

    This is a placeholder that will be overridden by AppBuilder.
    Use with FastAPI Depends():
        openai_client: OpenAIClient = Depends(get_openai_client)

    Returns:
        OpenAIClient: OpenAI client instance

    Raises:
        NotImplementedError: If called before AppBuilder initialization
    """
    raise NotImplementedError("OpenAI client not initialized. Use AppBuilder.")


def get_kb_service() -> KnowledgeBaseService:
    """Knowledge base service dependency.

    This is a placeholder that will be overridden by AppBuilder.
    Use with FastAPI Depends():
        kb_service: KnowledgeBaseService = Depends(get_kb_service)

    Returns:
        KnowledgeBaseService: Knowledge base service instance

    Raises:
        NotImplementedError: If called before AppBuilder initialization
    """
    raise NotImplementedError("Knowledge base service not initialized. Use AppBuilder.")


def get_session_repository() -> SessionRepository:
    """Session repository dependency.

    Returns:
        SessionRepository: Session repository instance
    """
    return SessionRepository()


def get_message_repository() -> MessageRepository:
    """Message repository dependency.

    Returns:
        MessageRepository: Message repository instance
    """
    return MessageRepository()


def get_summary_repository() -> SummaryRepository:
    """Summary repository dependency.

    Returns:
        SummaryRepository: Summary repository instance
    """
    return SummaryRepository()


def get_session_service(
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(get_db)],
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
) -> SessionService:
    """Session service dependency.

    Use with FastAPI Depends():
        service: SessionService = Depends(get_session_service)

    Args:
        session_maker: Database session maker (injected)
        session_repo: Session repository (injected)
        message_repo: Message repository (injected)

    Returns:
        SessionService: Session service instance
    """
    return SessionService(
        session_maker=session_maker,
        session_repo=session_repo,
        message_repo=message_repo,
    )


def get_agent_service(
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(get_db)],
    openai_client: Annotated[OpenAIClient, Depends(get_openai_client)],
    kb_service: Annotated[KnowledgeBaseService, Depends(get_kb_service)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)],
    session_repo: Annotated[SessionRepository, Depends(get_session_repository)],
    summary_repo: Annotated[SummaryRepository, Depends(get_summary_repository)],
) -> AgentService:
    """Agent service dependency.

    Use with FastAPI Depends():
        service: AgentService = Depends(get_agent_service)

    Args:
        session_maker: Database session maker (injected)
        openai_client: OpenAI client (injected)
        kb_service: Knowledge base service (injected)
        message_repo: Message repository (injected)
        session_repo: Session repository (injected)
        summary_repo: Summary repository (injected)

    Returns:
        AgentService: Agent service instance
    """
    return AgentService(
        session_maker=session_maker,
        openai_client=openai_client,
        kb_service=kb_service,
        message_repo=message_repo,
        session_repo=session_repo,
        summary_repo=summary_repo,
    )
