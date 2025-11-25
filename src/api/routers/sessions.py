"""Session management API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_session_service
from api.routers.utils import convert_messages_to_responses, handle_router_error
from api.routers.verifications import verify_session_exists
from domain.entities import ChatSession
from domain.schemas import (
    CreateSessionRequest,
    MessageHistoryResponse,
    SessionListResponse,
    SessionResponse,
    UpdateSessionRequest,
)
from logic.sessions import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Creates a new chat session with a unique ID",
)
async def create_session(
    request: CreateSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Create a new chat session."""
    try:
        session = await session_service.create_session(name=request.name)
        return SessionResponse(
            id=session.id,
            name=session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except Exception as e:
        raise handle_router_error("creating session", "new", e)


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List all chat sessions",
    description="Retrieve a list of all chat sessions with pagination support",
)
async def list_sessions(
    session_service: Annotated[SessionService, Depends(get_session_service)],
    limit: int = 100,
    offset: int = 0,
) -> SessionListResponse:
    """List all chat sessions with pagination."""
    try:
        sessions, total = await session_service.list_sessions(
            limit=limit, offset=offset
        )

        session_responses = [
            SessionResponse(
                id=session.id,
                name=session.name,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
            for session in sessions
        ]

        return SessionListResponse(sessions=session_responses, total=total)
    except Exception as e:
        raise handle_router_error("listing sessions", "all", e)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a chat session",
    description="Retrieve details of a specific chat session by ID",
)
async def get_session(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
) -> SessionResponse:
    """Get a specific chat session by ID."""
    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update a chat session",
    description="Update a chat session's name",
)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Update a chat session's name."""
    try:
        updated_session = await session_service.update_session(session_id, request.name)
        if updated_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        return SessionResponse(
            id=updated_session.id,
            name=updated_session.name,
            created_at=updated_session.created_at,
            updated_at=updated_session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_router_error("updating session", session_id, e)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
    description="Delete a chat session and all its messages",
)
async def delete_session(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> None:
    """Delete a chat session and all its messages."""
    try:
        await session_service.delete_session(session.id)
    except Exception as e:
        raise handle_router_error("deleting session", session.id, e)


@router.get(
    "/{session_id}/messages",
    response_model=MessageHistoryResponse,
    summary="Get message history",
    description="Retrieve all messages for a specific chat session",
)
async def get_message_history(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> MessageHistoryResponse:
    """Get all messages for a session."""
    try:
        messages, total = await session_service.get_message_history(session.id)
        message_responses = convert_messages_to_responses(messages)

        return MessageHistoryResponse(
            session_id=session.id,
            messages=message_responses,
            total=total,
        )
    except Exception as e:
        raise handle_router_error("getting message history for session", session.id, e)
