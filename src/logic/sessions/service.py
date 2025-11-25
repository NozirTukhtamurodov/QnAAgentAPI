"""Session service for business logic related to chat sessions."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.entities import ChatSession, Message
from repositories.message_repository import MessageRepository
from repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing chat sessions with transactional operations.

    Session maker is injected via DI, service manages its own database sessions.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        session_repo: SessionRepository,
        message_repo: MessageRepository,
    ) -> None:
        """Initialize session service.

        Args:
            session_maker: Async session maker for database connections
            session_repo: Session repository instance
            message_repo: Message repository instance
        """
        self.session_maker = session_maker
        self.session_repo = session_repo
        self.message_repo = message_repo

    async def create_session(self, name: str | None = None) -> ChatSession:
        """Create a new chat session with a unique ID.

        Args:
            name: Optional name for the session. Auto-generated if not provided.

        Returns:
            ChatSession: Created session
        """
        session_id = str(uuid.uuid4())

        # Auto-generate name if not provided
        if name is None:
            from datetime import datetime

            name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        logger.info(f"Creating new session: {session_id} with name: {name}")

        async with self.session_maker() as db_session:
            chat_session = await self.session_repo.create(db_session, session_id, name)
            await db_session.commit()

        return chat_session

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get a chat session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ChatSession | None: Session if found, None otherwise
        """
        async with self.session_maker() as db_session:
            return await self.session_repo.get_by_id(db_session, session_id)

    async def list_sessions(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[ChatSession], int]:
        """List all chat sessions with pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            tuple[list[ChatSession], int]: List of sessions and total count
        """
        async with self.session_maker() as db_session:
            sessions = await self.session_repo.list_all(db_session, limit, offset)
            total = await self.session_repo.count(db_session)

        return sessions, total

    async def update_session(self, session_id: str, name: str) -> ChatSession | None:
        """Update a chat session's name.

        Args:
            session_id: Session identifier
            name: New name for the session

        Returns:
            ChatSession | None: Updated session if found, None otherwise
        """
        logger.info(f"Updating session {session_id} with name: {name}")

        async with self.session_maker() as db_session:
            updated_session = await self.session_repo.update(
                db_session, session_id, name
            )
            if updated_session:
                await db_session.commit()
            return updated_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if deleted, False if not found
        """
        async with self.session_maker() as db_session:
            deleted = await self.session_repo.delete(db_session, session_id)
            await db_session.commit()

        return deleted

    async def get_message_history(self, session_id: str) -> tuple[list[Message], int]:
        """Get all messages for a session.

        Args:
            session_id: Session identifier

        Returns:
            tuple[list[Message], int]: List of messages and total count
        """
        async with self.session_maker() as db_session:
            messages = await self.message_repo.get_by_session(db_session, session_id)
            count = await self.message_repo.count_by_session(db_session, session_id)

        return messages, count
