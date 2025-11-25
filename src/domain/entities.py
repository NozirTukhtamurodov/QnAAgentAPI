"""Domain entities representing core business objects."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from infrastructure.models import (
        ChatSessionModel,
        ConversationSummaryModel,
        MessageModel,
    )


class Message(BaseModel):
    """Represents a chat message in the system."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_model(cls, model: "MessageModel") -> "Message":
        """Create entity from database model."""
        return cls(
            id=model.id,
            session_id=model.session_id,
            role=model.role,  # type: ignore[arg-type]
            content=model.content,
            created_at=model.created_at,
        )


class ChatSession(BaseModel):
    """Represents a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_model(cls, model: "ChatSessionModel") -> "ChatSession":
        """Create entity from database model."""
        return cls(
            id=model.id,
            name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ConversationSummary(BaseModel):
    """Represents a conversation summary for history optimization."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    session_id: str
    message_count: int
    summary_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_model(cls, model: "ConversationSummaryModel") -> "ConversationSummary":
        """Create entity from database model."""
        return cls(
            id=model.id,
            session_id=model.session_id,
            message_count=model.message_count,
            summary_text=model.summary_text,
            created_at=model.created_at,
        )


class KnowledgeItem(BaseModel):
    """Represents a knowledge base item."""

    filename: str
    content: str
    relevance_score: float | None = None


class ToolCall(BaseModel):
    """Represents a tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, str]


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    result: str
