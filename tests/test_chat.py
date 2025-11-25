"""Tests for chat functionality with real LLM integration."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_message_basic(client: AsyncClient):
    """Test sending a basic message to the chat."""
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

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
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    response = await client.post(f"/sessions/{session_id}/chat", json={"content": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_conversation_context(client: AsyncClient):
    """Test that conversation context is maintained across messages."""
    session_response = await client.post("/sessions", json={})
    session_id = session_response.json()["id"]

    await client.post(
        f"/sessions/{session_id}/chat", json={"content": "My name is Alice"}
    )

    response = await client.post(
        f"/sessions/{session_id}/chat", json={"content": "What is my name?"}
    )

    assert response.status_code == 201
    data = response.json()
    assert "alice" in data["content"].lower()


@pytest.mark.asyncio
async def test_message_history_after_chat(client: AsyncClient):
    """Test that message history is properly stored after chat."""
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    await client.post(
        f"/sessions/{session_id}/chat", json={"content": "Tell me about FastAPI"}
    )

    history_response = await client.get(f"/sessions/{session_id}/messages")

    assert history_response.status_code == 200
    data = history_response.json()
    assert data["total"] >= 2

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
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    response = await client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "What is Python? Tell me about its features."},
    )

    assert response.status_code == 201
    data = response.json()

    content_lower = data["content"].lower()
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
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    response = await client.post(
        f"/sessions/{session_id}/chat",
        json={"content": "Compare Python and Docker - what are they?"},
    )

    assert response.status_code == 201
    data = response.json()

    content_lower = data["content"].lower()
    assert "python" in content_lower or "docker" in content_lower


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
