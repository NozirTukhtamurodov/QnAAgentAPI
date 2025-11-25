"""Domain entities representing core business objects."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    """Represents a chat message in the system."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatSession(BaseModel):
    """Represents a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConversationSummary(BaseModel):
    """Represents a conversation summary for history optimization."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    session_id: str
    message_count: int
    summary_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
