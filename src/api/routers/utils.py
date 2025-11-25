"""Utility functions for API routers.

This module contains reusable helper functions following DRY and SOLID principles.
"""

import logging
from typing import Any

from fastapi import HTTPException, status

from domain.entities import Message
from domain.schemas import MessageResponse

logger = logging.getLogger(__name__)


def handle_router_error(
    operation: str, identifier: str, error: Exception
) -> HTTPException:
    """Handle router errors with consistent logging and HTTP responses.

    Args:
        operation: Description of the operation (e.g., "creating session")
        identifier: Resource identifier (e.g., session_id)
        error: The exception that occurred

    Returns:
        HTTPException: Formatted HTTP exception
    """
    logger.error(f"Error {operation} {identifier}: {error}", exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed {operation}",
    )


def convert_message_to_response(message: Message) -> MessageResponse:
    """Convert domain Message entity to API MessageResponse schema.

    Args:
        message: Domain message entity

    Returns:
        MessageResponse: API response schema
    """
    return MessageResponse(
        id=message.id or 0,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def convert_messages_to_responses(messages: list[Message]) -> list[MessageResponse]:
    """Convert list of domain Message entities to list of API MessageResponse schemas.

    Args:
        messages: List of domain message entities

    Returns:
        list[MessageResponse]: List of API response schemas
    """
    return [convert_message_to_response(msg) for msg in messages]


def create_sse_event(event: str, data: dict[str, Any]) -> dict[str, str]:
    """Create a Server-Sent Event (SSE) formatted event.

    Args:
        event: Event type (e.g., "message", "error", "typing")
        data: Event data to be JSON serialized

    Returns:
        dict: SSE event dictionary with 'event' and 'data' keys
    """
    import json

    return {
        "event": event,
        "data": json.dumps(data),
    }


def create_error_event(error: str, session_id: str) -> dict[str, str]:
    """Create an SSE error event.

    Args:
        error: Error message
        session_id: Session identifier

    Returns:
        dict: SSE error event
    """
    return create_sse_event(
        event="error",
        data={"error": error, "session_id": session_id},
    )
