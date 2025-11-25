"""Message repository for database operations on chat messages."""

import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import Message
from infrastructure.models import MessageModel

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for message operations using SQLAlchemy ORM.

    All methods accept an AsyncSession to support transactions.
    """

    async def create(
        self,
        session: AsyncSession,
        session_id: str,
        role: str,
        content: str,
    ) -> Message:
        """Create a new message.

        Args:
            session: SQLAlchemy async session (can be part of a transaction)
            session_id: Session identifier
            role: Message role (user, assistant)
            content: Message content

        Returns:
            Message: Created message
        """
        db_message = MessageModel(
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(db_message)
        await session.flush()
        await session.refresh(db_message)

        logger.info(f"Created message {db_message.id} in session {session_id}")
        return Message.from_model(db_message)

    async def get_by_session(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        """Get all messages for a session.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier
            limit: Optional limit on number of messages

        Returns:
            list[Message]: List of messages
        """
        stmt = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
        )

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        db_messages = result.scalars().all()

        messages = [Message.from_model(db_message) for db_message in db_messages]

        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages

    async def count_by_session(self, session: AsyncSession, session_id: str) -> int:
        """Count messages in a session.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier

        Returns:
            int: Message count
        """
        stmt = (
            select(func.count())
            .select_from(MessageModel)
            .where(MessageModel.session_id == session_id)
        )
        result = await session.execute(stmt)
        count = result.scalar_one()
        return count

    async def delete_by_session(self, session: AsyncSession, session_id: str) -> int:
        """Delete all messages in a session.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier

        Returns:
            int: Number of messages deleted
        """
        stmt = delete(MessageModel).where(MessageModel.session_id == session_id)
        result = await session.execute(stmt)
        count: int = result.rowcount or 0  # type: ignore[attr-defined]
        logger.info(f"Deleted {count} messages from session {session_id}")
        return count
