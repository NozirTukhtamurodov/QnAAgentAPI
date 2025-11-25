"""FastAPI application builder with dependency injection and lifecycle management."""

import contextlib
import logging
import typing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api import dependencies
from config import Settings
from infrastructure.openai_client import OpenAIClient
from logic.common import KnowledgeBaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def include_routers(app: FastAPI) -> None:
    """Include all API routers.

    Args:
        app: FastAPI application instance
    """
    from api.routers.chat import router as chat_router
    from api.routers.health import router as health_router
    from api.routers.sessions import router as sessions_router

    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)


class AppBuilder:
    """Application builder with dependency injection and lifecycle management.

    This class follows the builder pattern and manages:
    - Application configuration
    - Database connection lifecycle
    - OpenAI client lifecycle
    - Knowledge base service initialization
    - Dependency injection setup
    """

    def __init__(self) -> None:
        """Initialize the application builder."""
        from config import get_settings

        self.settings = get_settings()

        # Async resources (initialized in startup)
        self._async_engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None
        self._openai_client: OpenAIClient | None = None
        self._kb_service: KnowledgeBaseService | None = None

        # Create FastAPI application
        self.app: FastAPI = FastAPI(
            title="QnA Agent API",
            description="Production-ready QnA Agent API with OpenAI and knowledge base",
            version="0.1.0",
            debug=self.settings.app_log_level == "DEBUG",
            lifespan=self.lifespan_manager,
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Configure middleware
        self._configure_middleware()

        # Configure exception handlers
        self._configure_exception_handlers()

        # Override dependencies with actual instances
        self._setup_dependency_overrides()

        # Include routers
        include_routers(self.app)

        # Add root endpoint
        self._add_root_endpoint()

    def _configure_middleware(self) -> None:
        """Configure FastAPI middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _configure_exception_handlers(self) -> None:
        """Configure global exception handlers."""

        @self.app.exception_handler(Exception)
        async def global_exception_handler(request, exc):
            """Global exception handler for unhandled errors."""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                },
            )

    def _setup_dependency_overrides(self) -> None:
        """Set up dependency injection overrides."""
        self.app.dependency_overrides[dependencies.get_settings] = self._get_settings
        self.app.dependency_overrides[dependencies.get_db] = self._get_db
        self.app.dependency_overrides[dependencies.get_openai_client] = (
            self._get_openai_client
        )
        self.app.dependency_overrides[dependencies.get_kb_service] = (
            self._get_kb_service
        )

    def _add_root_endpoint(self) -> None:
        """Add root API endpoint."""

        @self.app.get("/", tags=["root"])
        async def root() -> dict[str, str]:
            """Root endpoint with API information."""
            return {
                "name": "QnA Agent API",
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/health",
            }

    def _get_settings(self) -> Settings:
        """Dependency override for settings.

        Returns:
            Settings: Application settings instance
        """
        return self.settings

    def _get_db(self) -> async_sessionmaker[AsyncSession]:
        """Dependency override for database session maker.

        Returns:
            async_sessionmaker: Database session maker

        Raises:
            RuntimeError: If session maker not initialized
        """
        if self._session_maker is None:
            raise RuntimeError("Database session maker not initialized")
        return self._session_maker

    def _get_openai_client(self) -> OpenAIClient:
        """Dependency override for OpenAI client.

        Returns:
            OpenAI client: OpenAI client instance

        Raises:
            RuntimeError: If OpenAI client not initialized
        """
        if self._openai_client is None:
            raise RuntimeError("OpenAI client not initialized")
        return self._openai_client

    def _get_kb_service(self) -> KnowledgeBaseService:
        """Dependency override for knowledge base service.

        Returns:
            KnowledgeBaseService: Knowledge base service instance

        Raises:
            RuntimeError: If knowledge base service not initialized
        """
        if self._kb_service is None:
            raise RuntimeError("Knowledge base service not initialized")
        return self._kb_service

    async def init_async_resources(self) -> None:
        """Initialize async resources like database and OpenAI client."""
        logger.info("Starting QnA Agent API v0.1.0")
        logger.info(f"Log level: {self.settings.app_log_level}")
        logger.info(f"Model: {self.settings.openai_model}")

        # Initialize database engine
        self._async_engine = create_async_engine(
            self.settings.database_url,
            echo=self.settings.app_log_level == "DEBUG",
            pool_pre_ping=True,
        )
        logger.info("Database engine created")
        logger.info("Run 'alembic upgrade head' to apply migrations")

        # Create session maker
        self._session_maker = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Initialize OpenAI client
        self._openai_client = OpenAIClient(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            model=self.settings.openai_model,
            timeout=self.settings.openai_timeout,
            max_retries=self.settings.openai_max_retries,
        )
        logger.info("OpenAI client initialized")

        # Initialize knowledge base service
        self._kb_service = KnowledgeBaseService(self.settings.knowledge_base_dir)
        logger.info(
            f"Knowledge base service initialized: {self.settings.knowledge_base_dir}"
        )

    async def tear_down(self) -> None:
        """Clean up async resources."""
        logger.info("Shutting down QnA Agent API")

        # Close OpenAI client
        if self._openai_client is not None:
            await self._openai_client.close()
            logger.info("OpenAI client closed")

        # Dispose database engine
        if self._async_engine is not None:
            await self._async_engine.dispose()
            logger.info("Database engine disposed")

        logger.info("Cleanup completed")

    @contextlib.asynccontextmanager
    async def lifespan_manager(
        self, _: FastAPI
    ) -> typing.AsyncIterator[dict[str, typing.Any]]:
        """Lifespan context manager for FastAPI application.

        Args:
            _: FastAPI application instance (unused)

        Yields:
            dict: Lifespan state (empty dict)
        """
        try:
            await self.init_async_resources()
            yield {}
        finally:
            await self.tear_down()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    return AppBuilder().app
