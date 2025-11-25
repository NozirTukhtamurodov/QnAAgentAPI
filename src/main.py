"""Main FastAPI application entrypoint."""

from api.app import create_app

# Create application instance
application = create_app()


if __name__ == "__main__":
    import uvicorn

    from config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:application",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
        log_level=settings.app_log_level.lower(),
    )
