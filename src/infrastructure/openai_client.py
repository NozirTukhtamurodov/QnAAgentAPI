"""OpenAI client wrapper with tool-calling support."""

import logging
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Wrapper for OpenAI async client with tool-calling capabilities."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
        max_retries: int = 3,
    ) -> None:
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            base_url: Base URL for API (supports OpenRouter, Ollama)
            model: Model name to use
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(
            f"OpenAI client initialized with model: {model}, base_url: {base_url}"
        )

    async def create_chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatCompletion:
        """Create a chat completion with optional tool calling.

        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            ChatCompletion: OpenAI chat completion response
        """
        logger.debug(f"Creating chat completion with {len(messages)} messages")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
            logger.debug(f"Tool calling enabled with {len(tools)} tools")

        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        try:
            response: ChatCompletion = await self.client.chat.completions.create(
                **kwargs
            )
            logger.debug(f"Chat completion successful: {response.id}")
            return response

        except Exception as e:
            logger.error(f"Error creating chat completion: {e}")
            raise

    async def close(self) -> None:
        """Close the OpenAI client."""
        await self.client.close()
        logger.info("OpenAI client closed")
