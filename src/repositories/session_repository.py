"""Session repository for database operations on chat sessions."""

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import ChatSession
from infrastructure.models import ChatSessionModel

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for chat session operations using SQLAlchemy ORM.

    All methods accept an AsyncSession to support transactions.
    """

    async def create(
        self, session: AsyncSession, session_id: str, name: str
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            session: SQLAlchemy async session (can be part of a transaction)
            session_id: Unique session identifier
            name: Session name

        Returns:
            ChatSession: Created session
        """
        db_session = ChatSessionModel(id=session_id, name=name)
        session.add(db_session)
        await session.flush()  # Flush to get created_at/updated_at values
        await session.refresh(db_session)

        logger.info(f"Created chat session: {session_id} with name: {name}")
        return ChatSession(
            id=db_session.id,
            name=db_session.name,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
        )

    async def get_by_id(
        self, session: AsyncSession, session_id: str
    ) -> ChatSession | None:
        """Get a chat session by ID.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier

        Returns:
            ChatSession | None: Session if found, None otherwise
        """
        stmt = select(ChatSessionModel).where(ChatSessionModel.id == session_id)
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()

        if db_session is None:
            logger.warning(f"Session not found: {session_id}")
            return None

        return ChatSession(
            id=db_session.id,
            name=db_session.name,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
        )

    async def list_all(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatSession]:
        """List all chat sessions.

        Args:
            session: SQLAlchemy async session
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            list[ChatSession]: List of sessions
        """
        stmt = (
            select(ChatSessionModel)
            .order_by(ChatSessionModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        db_sessions = result.scalars().all()

        sessions = [
            ChatSession(
                id=db_session.id,
                name=db_session.name,
                created_at=db_session.created_at,
                updated_at=db_session.updated_at,
            )
            for db_session in db_sessions
        ]

        logger.info(f"Listed {len(sessions)} sessions")
        return sessions

    async def count(self, session: AsyncSession) -> int:
        """Count total number of sessions.

        Args:
            session: SQLAlchemy async session

        Returns:
            int: Total session count
        """
        stmt = select(func.count()).select_from(ChatSessionModel)
        result = await session.execute(stmt)
        count = result.scalar_one()
        return count

    async def delete(self, session: AsyncSession, session_id: str) -> bool:
        """Delete a chat session and all its messages (cascade).

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier

        Returns:
            bool: True if deleted, False if not found
        """
        stmt = delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
        result = await session.execute(stmt)

        deleted = bool(result.rowcount)  # type: ignore[attr-defined]
        if deleted:
            logger.info(f"Deleted session: {session_id}")
        else:
            logger.warning(f"Session not found for deletion: {session_id}")

        return deleted

    async def update(
        self, session: AsyncSession, session_id: str, name: str
    ) -> ChatSession | None:
        """Update a chat session's name.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier
            name: New name for the session

        Returns:
            ChatSession | None: Updated session if found, None otherwise
        """
        stmt = (
            update(ChatSessionModel)
            .where(ChatSessionModel.id == session_id)
            .values(name=name, updated_at=datetime.now(UTC))
            .returning(ChatSessionModel)
        )
        result = await session.execute(stmt)
        db_session = result.scalar_one_or_none()

        if db_session is None:
            logger.warning(f"Session not found for update: {session_id}")
            return None

        logger.info(f"Updated session {session_id} with name: {name}")
        return ChatSession(
            id=db_session.id,
            name=db_session.name,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
        )

    async def update_timestamp(self, session: AsyncSession, session_id: str) -> None:
        """Update the session's updated_at timestamp.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier
        """
        stmt = (
            update(ChatSessionModel)
            .where(ChatSessionModel.id == session_id)
            .values(updated_at=datetime.now(UTC))
        )
        await session.execute(stmt)
        logger.debug(f"Updated timestamp for session: {session_id}")
