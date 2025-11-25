"""Tests for session management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Test creating a new chat session."""
    response = await client.post("/sessions", json={})

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["id"], str)
    assert len(data["id"]) == 36


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient):
    """Test listing all sessions."""
    response1 = await client.post("/sessions", json={})
    response2 = await client.post("/sessions", json={})

    assert response1.status_code == 201
    assert response2.status_code == 201

    response = await client.get("/sessions")

    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert len(data["sessions"]) >= 2
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient):
    """Test retrieving a specific session."""
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    response = await client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id


@pytest.mark.asyncio
async def test_get_nonexistent_session(client: AsyncClient):
    """Test retrieving a session that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/sessions/{fake_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient):
    """Test deleting a session."""
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    delete_response = await client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_message_history_empty(client: AsyncClient):
    """Test getting message history for a new session."""
    create_response = await client.post("/sessions", json={})
    session_id = create_response.json()["id"]

    response = await client.get(f"/sessions/{session_id}/messages")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "total" in data
    assert data["total"] == 0
    assert len(data["messages"]) == 0


@pytest.mark.asyncio
async def test_session_lifecycle(client: AsyncClient):
    """Test complete session lifecycle: create -> use -> delete."""
    create_response = await client.post("/sessions", json={})
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    get_response = await client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200

    history_response = await client.get(f"/sessions/{session_id}/messages")
    assert history_response.status_code == 200
    assert history_response.json()["total"] == 0

    delete_response = await client.delete(f"/sessions/{session_id}")
    assert delete_response.status_code == 204

    get_after_delete = await client.get(f"/sessions/{session_id}")
    assert get_after_delete.status_code == 404
