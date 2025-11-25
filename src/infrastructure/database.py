"""Database infrastructure with SQLAlchemy async engine and session management."""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLAlchemy async engine and sessions."""

    def __init__(self, database_url: str) -> None:
        """Initialize database manager.

        Args:
            database_url: SQLite database URL (e.g., sqlite+aiosqlite:///./data/db.db)
        """
        self.database_url = database_url
        self._ensure_data_directory()

        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {
                "timeout": 30.0,
                "check_same_thread": False,
            }

        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"Database engine created: {database_url}")

    def _ensure_data_directory(self) -> None:
        """Ensure the database directory exists."""
        if ":///" in self.database_url:
            db_path = self.database_url.split("///")[1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        """Close the database engine."""
        await self.engine.dispose()
        logger.info("Database engine closed")
