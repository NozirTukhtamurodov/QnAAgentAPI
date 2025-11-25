"""Chat messaging API endpoints with SSE support."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from api.dependencies import get_agent_service
from api.routers.utils import (
    convert_message_to_response,
    create_error_event,
    create_sse_event,
    handle_router_error,
)
from api.routers.verifications import verify_session_exists
from domain.entities import ChatSession
from domain.schemas import MessageResponse, SendMessageRequest
from logic.chat import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions/{session_id}/chat", tags=["chat"])


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and get AI response",
    description="Send a user message and receive an AI-generated response",
)
async def send_message(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
    request: SendMessageRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> MessageResponse:
    """Send a message and get AI response."""
    try:
        assistant_message = await agent_service.process_message(
            session_id=session.id,
            user_message=request.content,
        )

        return convert_message_to_response(assistant_message)

    except Exception as e:
        raise handle_router_error("processing message for session", session.id, e)


@router.post(
    "/stream",
    summary="Send a message with SSE streaming",
    description="Send a user message and receive AI response via Server-Sent Events for real-time updates",
)
async def send_message_stream(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
    request: SendMessageRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> EventSourceResponse:
    """Send a message and stream AI response via SSE."""

    async def event_generator():
        """Generate SSE events for the chat response."""
        try:
            # Send typing indicator
            yield create_sse_event("typing", {"session_id": session.id, "typing": True})

            # Process message with agent
            assistant_message = await agent_service.process_message(
                session_id=session.id,
                user_message=request.content,
            )

            # Send the complete message
            yield create_sse_event(
                "message",
                {
                    "id": assistant_message.id,
                    "session_id": assistant_message.session_id,
                    "role": assistant_message.role,
                    "content": assistant_message.content,
                    "created_at": assistant_message.created_at.isoformat(),
                },
            )

            # Send completion event
            yield create_sse_event(
                "done",
                {
                    "session_id": session.id,
                    "message_id": assistant_message.id,
                },
            )

        except Exception as e:
            logger.error(
                f"Error in SSE stream for session {session.id}: {e}", exc_info=True
            )
            yield create_error_event(str(e), session.id)

    return EventSourceResponse(event_generator())


@router.get(
    "/updates",
    summary="Subscribe to chat updates via SSE",
    description="Subscribe to real-time updates for a chat session using Server-Sent Events",
)
async def subscribe_to_updates(
    session: Annotated[ChatSession, Depends(verify_session_exists)],
) -> EventSourceResponse:
    """Subscribe to chat updates via Server-Sent Events.

    This endpoint allows clients to receive real-time notifications about:
    - New messages
    - Typing indicators
    - Session updates
    """

    async def event_generator():
        """Generate SSE events for chat updates."""
        try:
            # Send connection established event
            yield create_sse_event(
                "connected",
                {
                    "session_id": session.id,
                    "timestamp": session.updated_at.isoformat(),
                },
            )

            # Keep connection alive with periodic heartbeats
            # In a real production system, this would listen to a message queue
            # or use a pub/sub system for real-time updates
            while True:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                yield create_sse_event(
                    "heartbeat",
                    {
                        "session_id": session.id,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                )

        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for session {session.id}")
            raise
        except Exception as e:
            logger.error(
                f"Error in SSE subscription for session {session.id}: {e}",
                exc_info=True,
            )
            yield create_error_event(str(e), session.id)

    return EventSourceResponse(event_generator())
