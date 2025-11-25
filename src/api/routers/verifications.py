"""Verification dependencies for API endpoints.

This module provides reusable verification dependencies that can be injected
into endpoint functions using FastAPI's Depends() pattern.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from api.dependencies import get_session_service
from domain.entities import ChatSession
from logic.sessions import SessionService


async def verify_session_exists(
    session_id: Annotated[str, Path(description="Session identifier")],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> ChatSession:
    """Verify that a session exists and return it.

    This is a FastAPI dependency that automatically validates session existence.

    Usage:
        @router.get("/sessions/{session_id}/messages")
        async def get_messages(
            session: Annotated[ChatSession, Depends(verify_session_exists)],
        ):
            # session is guaranteed to exist here
            ...

    Args:
        session_id: Session identifier from path parameter
        session_service: Injected session service

    Returns:
        ChatSession: The validated session entity

    Raises:
        HTTPException: 404 if session not found
    """
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session
