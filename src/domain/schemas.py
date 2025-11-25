"""API request and response schemas."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


# Request Schemas
class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""

    name: str | None = Field(
        None, max_length=255, description="Optional name for the chat session"
    )


class UpdateSessionRequest(BaseModel):
    """Request to update a chat session."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="New name for the chat session"
    )


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session."""

    content: str = Field(..., min_length=1, description="Message content")


# Response Schemas
class MessageResponse(BaseModel):
    """Response containing a single message."""

    id: int
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class SessionResponse(BaseModel):
    """Response containing session information."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""

    sessions: list[SessionResponse]
    total: int


class MessageHistoryResponse(BaseModel):
    """Response containing message history."""

    session_id: str
    messages: list[MessageResponse]
    total: int


class ChatUpdateEvent(BaseModel):
    """Server-sent event for chat updates."""

    event_type: Literal["message", "typing", "error"]
    session_id: str
    data: dict[str, str | int] | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"]
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
