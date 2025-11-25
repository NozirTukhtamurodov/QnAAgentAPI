"""Example client for the QnA Agent API."""

import asyncio
import json
from typing import Any

import httpx


class QnAAgentClient:
    """Client for interacting with the QnA Agent API."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize the client.

        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def close(self) -> None:
        """Close the client."""
        await self.client.aclose()

    async def create_session(self) -> dict[str, Any]:
        """Create a new chat session.

        Returns:
            dict: Session information
        """
        response = await self.client.post("/sessions", json={})
        response.raise_for_status()
        return response.json()

    async def list_sessions(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """List all chat sessions.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            dict: List of sessions
        """
        response = await self.client.get(
            "/sessions",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()

    async def get_session(self, session_id: str) -> dict[str, Any]:
        """Get a specific session.

        Args:
            session_id: Session identifier

        Returns:
            dict: Session information
        """
        response = await self.client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    async def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier
        """
        response = await self.client.delete(f"/sessions/{session_id}")
        response.raise_for_status()

    async def get_messages(self, session_id: str) -> dict[str, Any]:
        """Get all messages in a session.

        Args:
            session_id: Session identifier

        Returns:
            dict: Message history
        """
        response = await self.client.get(f"/sessions/{session_id}/messages")
        response.raise_for_status()
        return response.json()

    async def send_message(self, session_id: str, content: str) -> dict[str, Any]:
        """Send a message and get AI response.

        Args:
            session_id: Session identifier
            content: Message content

        Returns:
            dict: AI response message
        """
        response = await self.client.post(
            f"/sessions/{session_id}/chat",
            json={"content": content},
        )
        response.raise_for_status()
        return response.json()

    async def send_message_stream(self, session_id: str, content: str) -> None:
        """Send a message and stream AI response via SSE.

        Args:
            session_id: Session identifier
            content: Message content
        """
        async with self.client.stream(
            "POST",
            f"/sessions/{session_id}/chat/stream",
            json={"content": content},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    try:
                        event_data = json.loads(data)
                        print(f"Event: {event_data}")
                    except json.JSONDecodeError:
                        print(f"Raw data: {data}")

    async def health_check(self) -> dict[str, Any]:
        """Check API health.

        Returns:
            dict: Health status
        """
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()


async def main():
    """Example usage of the QnA Agent API client."""
    client = QnAAgentClient()

    try:
        # Health check
        print("=== Health Check ===")
        health = await client.health_check()
        print(f"Status: {health['status']}")
        print()

        # Create a new session
        print("=== Creating Session ===")
        session = await client.create_session()
        session_id = session["id"]
        print(f"Session ID: {session_id}")
        print()

        # Send a message
        print("=== Sending Message ===")
        message = "What is Python?"
        print(f"User: {message}")
        response = await client.send_message(session_id, message)
        print(f"Assistant: {response['content']}")
        print()

        # Get message history
        print("=== Message History ===")
        history = await client.get_messages(session_id)
        print(f"Total messages: {history['total']}")
        for msg in history["messages"]:
            print(f"- {msg['role']}: {msg['content'][:100]}...")
        print()

        # Stream a message
        print("=== Streaming Message ===")
        await client.send_message_stream(session_id, "Tell me about FastAPI")
        print()

        # List sessions
        print("=== List Sessions ===")
        sessions = await client.list_sessions()
        print(f"Total sessions: {sessions['total']}")
        print()

        # Clean up - delete session
        print("=== Deleting Session ===")
        await client.delete_session(session_id)
        print(f"Session {session_id} deleted")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
