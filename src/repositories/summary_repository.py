"""Summary repository for database operations on conversation summaries."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import ConversationSummary
from infrastructure.models import ConversationSummaryModel

logger = logging.getLogger(__name__)


class SummaryRepository:
    """Repository for conversation summary operations using SQLAlchemy ORM.

    All methods accept an AsyncSession to support transactions.
    """

    async def get_for_session(
        self,
        session: AsyncSession,
        session_id: str,
    ) -> ConversationSummary | None:
        """Get the summary for a session.

        Since we only keep one summary per session (the latest),
        this simply retrieves it.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier

        Returns:
            ConversationSummary | None: Summary if found
        """
        stmt = select(ConversationSummaryModel).where(
            ConversationSummaryModel.session_id == session_id
        )
        result = await session.execute(stmt)
        db_summary = result.scalar_one_or_none()

        if not db_summary:
            return None

        return ConversationSummary.from_model(db_summary)

    async def upsert(
        self,
        session: AsyncSession,
        session_id: str,
        message_count: int,
        summary_text: str,
    ) -> ConversationSummary:
        """Create or update conversation summary for a session.

        Only keeps the latest summary - updates if one exists.

        Args:
            session: SQLAlchemy async session
            session_id: Session identifier
            message_count: Number of messages summarized
            summary_text: Summary content

        Returns:
            ConversationSummary: Created/updated summary
        """
        # Check if summary exists
        existing = await self.get_for_session(session, session_id)

        if existing:
            # Update existing summary
            stmt = select(ConversationSummaryModel).where(
                ConversationSummaryModel.session_id == session_id
            )
            result = await session.execute(stmt)
            db_summary = result.scalar_one()

            db_summary.message_count = message_count
            db_summary.summary_text = summary_text
            await session.flush()
            await session.refresh(db_summary)

            logger.info(
                f"Updated summary for session {session_id} ({message_count} messages)"
            )
        else:
            # Create new summary
            db_summary = ConversationSummaryModel(
                session_id=session_id,
                message_count=message_count,
                summary_text=summary_text,
            )
            session.add(db_summary)
            await session.flush()
            await session.refresh(db_summary)

            logger.info(
                f"Created summary for session {session_id} ({message_count} messages)"
            )

        return ConversationSummary.from_model(db_summary)
