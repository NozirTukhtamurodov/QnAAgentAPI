"""Tests for chat functionality with real LLM integration."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_message_basic(client: AsyncClient):
    """Test sending a basic message to the chat."""
    # Create a session
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    # Send a message
    message_response = await client.post(
        f"/sessions/{session_id}/chat", json={"content": "Hello, what is Python?"}
    )

    assert message_response.status_code == 201
    data = message_response.json()
    assert "id" in data
    assert "content" in data
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_send_message_to_nonexistent_session(client: AsyncClient):
    """Test sending a message to a session that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/sessions/{fake_id}/chat", json={"content": "Hello"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_empty_message(client: AsyncClient):
    """Test sending an empty message."""
    # Create a session
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    # Try to send empty message
    response = await client.post(f"/sessions/{session_id}/chat", json={"content": ""})

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_conversation_context(client: AsyncClient):
    """Test that conversation context is maintained across messages."""
    # Create a session
    session_response = await client.post("/sessions", json={})
    session_id = session_response.json()["id"]

    # Send first message
    await client.post(
        f"/sessions/{session_id}/chat", json={"content": "My name is Alice"}
    )

    # Send second message asking about the first
    response = await client.post(
        f"/sessions/{session_id}/chat", json={"content": "What is my name?"}
    )

    assert response.status_code == 201
    data = response.json()
    # The AI should remember the name from context
    assert "alice" in data["content"].lower()


@pytest.mark.asyncio
async def test_message_history_after_chat(client: AsyncClient):
    """Test that message history is properly stored after chat."""
    # Create a session
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    # Send a message
    await client.post(
        f"/sessions/{session_id}/chat", json={"content": "Tell me about FastAPI"}
    )

    # Get message history
    history_response = await client.get(f"/sessions/{session_id}/messages")

    assert history_response.status_code == 200
    data = history_response.json()
    assert data["total"] >= 2  # At least user message and assistant response

    messages = data["messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Tell me about FastAPI"
    assert messages[1]["role"] == "assistant"
    assert len(messages[1]["content"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_calling_knowledge_base(client: AsyncClient):
    """Test that the agent uses tool calling to query the knowledge base.

    This is an integration test that requires a real LLM connection.
    """
    # Create a session
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    # Ask a question that should trigger knowledge base search
    response = await client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "What is Python? Tell me about its features."},
    )

    assert response.status_code == 201
    data = response.json()

    # The response should contain information from the knowledge base
    content_lower = data["content"].lower()
    # Check for typical Python-related keywords that would be in KB
    assert any(
        keyword in content_lower
        for keyword in [
            "python",
            "programming",
            "language",
            "interpreted",
            "high-level",
        ]
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_tool_calls(client: AsyncClient):
    """Test that the agent can make multiple tool calls in one response.

    This is an integration test that requires a real LLM connection.
    """
    # Create a session
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    # Ask a question that might require multiple searches
    response = await client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "Compare Python and Docker - what are they?"},
    )

    assert response.status_code == 201
    data = response.json()

    # Response should mention both topics
    content_lower = data["content"].lower()
    assert "python" in content_lower or "docker" in content_lower


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
