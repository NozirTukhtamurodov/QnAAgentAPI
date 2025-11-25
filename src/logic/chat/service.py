"""Agent orchestrator with tool-calling capabilities.

This module follows SOLID principles with clear separation of concerns:
- ToolExecutor: Handles tool execution logic
- MessageFormatter: Converts between domain and OpenAI message formats
- ConversationManager: Manages conversation flow and state
- AgentService: Orchestrates the overall agent workflow
"""

import asyncio
import json
import logging
from typing import Any

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.entities import Message
from infrastructure.openai_client import OpenAIClient
from logic.common import KnowledgeBaseService
from repositories.message_repository import MessageRepository
from repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant with access to a knowledge base.
You can search the knowledge base to answer questions accurately.
When users ask questions, use the search_kb tool to find relevant information.
Always provide clear, accurate answers based on the knowledge base content.
If information is not in the knowledge base, say so clearly."""

MAX_AGENT_ITERATIONS = 5

# History optimization settings
MAX_RECENT_MESSAGES = 10  # Keep last N messages verbatim
MAX_TOOL_RESULTS = 3  # Keep only recent tool results
SUMMARIZE_THRESHOLD = 20  # Start summarizing when history exceeds this
RESUMMARIZE_THRESHOLD = 10  # Create new summary if 10+ messages since last summary

SUMMARIZATION_PROMPT = """Summarize the following conversation history concisely while preserving ALL critical information.

MUST preserve:
- User's name, role, preferences, and any personal details mentioned
- Specific facts, data, numbers, and technical details discussed
- Key decisions, conclusions, and action items
- Important context needed to continue the conversation naturally

Focus on: main topics discussed, important questions asked, key information provided, unresolved issues.
Keep it under 200 words but prioritize completeness over brevity."""

INCREMENTAL_SUMMARIZATION_PROMPT = """You are given a previous conversation summary and new messages that followed.
Create an updated summary that:

MUST preserve from previous summary:
- User's name and any personal details
- Important facts, numbers, and technical details
- Key context needed for conversation continuity

From new messages, add:
- Any NEW personal information (name, preferences, etc.)
- New facts, decisions, or important details
- Updated context or changes to previous information

Remove only:
- Superseded or corrected information
- Redundant details already captured

Keep under 200 words but prioritize important details over brevity.

Previous summary:
{previous_summary}

New messages:
{new_messages}

Provide the updated summary:"""


class ToolExecutor:
    """Handles execution of tool calls (Single Responsibility Principle).

    IMPORTANT: All tool execution methods are designed to NEVER raise exceptions.
    Instead, they return error messages as strings. This ensures the AI always
    receives a response and doesn't hang waiting for tool results.
    """

    def __init__(self, kb_service: KnowledgeBaseService) -> None:
        """Initialize tool executor.

        Args:
            kb_service: Knowledge base service instance
        """
        self.kb_service = kb_service

    @staticmethod
    def get_tool_definitions() -> list[ChatCompletionToolParam]:
        """Get available tool definitions for the LLM.

        Returns:
            list[ChatCompletionToolParam]: Tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_kb",
                    "description": "Search the knowledge base for relevant information. Returns content from .txt files that may be relevant to the query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant knowledge base items",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool call and always return a response.

        This method ensures the AI always receives a response, even when tools fail.
        Failures are returned as structured error messages so the AI can continue
        the conversation gracefully.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            str: Tool execution result or error message (never raises)
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "search_kb":
                return await self._execute_kb_search(arguments)

            # Unknown tool - return error message instead of raising
            error_msg = f"Error: Unknown tool '{tool_name}'. Available tools: search_kb"
            logger.error(f"Unknown tool requested: {tool_name}")
            return error_msg

        except Exception as e:
            # Catch any unexpected errors and return them as structured messages
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(f"Tool execution failed: {error_msg}", exc_info=True)
            return error_msg

    async def _execute_kb_search(self, arguments: dict[str, Any]) -> str:
        """Execute knowledge base search.

        Args:
            arguments: Search arguments

        Returns:
            str: Formatted search results or error message
        """
        try:
            query = arguments.get("query", "")
            if not query:
                return (
                    "Error: No search query provided. Please specify a query parameter."
                )

            kb_items = await self.kb_service.search(query)

            if not kb_items:
                return "No relevant information found in the knowledge base for your query."

            result_parts = [
                f"=== {item.filename} ===\n{item.content}\n" for item in kb_items
            ]

            logger.info(f"Knowledge base search returned {len(kb_items)} items")
            return "\n".join(result_parts)

        except Exception as e:
            error_msg = f"Error searching knowledge base: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


class MessageFormatter:
    """Formats messages between domain and OpenAI formats (Single Responsibility Principle)."""

    @staticmethod
    def to_openai_messages(
        messages: list[Message],
        include_system: bool = True,
    ) -> list[ChatCompletionMessageParam]:
        """Convert domain messages to OpenAI message format.

        Filters out orphaned tool messages (tool messages without a preceding
        assistant message) to avoid OpenAI API validation errors. This can happen
        with old conversations created before we started saving assistant messages
        with tool_calls.

        Args:
            messages: Domain message entities
            include_system: Whether to include system prompt

        Returns:
            list[ChatCompletionMessageParam]: OpenAI-formatted messages
        """
        formatted: list[ChatCompletionMessageParam] = []

        if include_system:
            formatted.append(
                ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT)
            )

        for msg in messages:
            if msg.role == "user":
                formatted.append(
                    ChatCompletionUserMessageParam(role="user", content=msg.content)
                )

            elif msg.role == "assistant":
                formatted.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant",
                        content=msg.content,
                    )
                )

            # Note: We never persist tool messages to the database, so msg.role will never be "tool"
            # Tool messages only exist in-memory during the agent reasoning loop

        return formatted

    @staticmethod
    def create_assistant_message_with_tools(
        content: str,
        tool_calls: list[Any],
    ) -> ChatCompletionAssistantMessageParam:
        """Create an assistant message with tool calls.

        Args:
            content: Message content
            tool_calls: List of tool calls from OpenAI

        Returns:
            ChatCompletionAssistantMessageParam: Formatted assistant message
        """
        return ChatCompletionAssistantMessageParam(
            role="assistant",
            content=content,
            tool_calls=[
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        )

    @staticmethod
    def create_tool_message(
        tool_call_id: str,
        content: str,
    ) -> ChatCompletionToolMessageParam:
        """Create a tool result message.

        Args:
            tool_call_id: ID of the tool call
            content: Tool result content

        Returns:
            ChatCompletionToolMessageParam: Formatted tool message
        """
        return ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=tool_call_id,
            content=content,
        )


class ConversationManager:
    """Manages conversation state and message persistence (Single Responsibility Principle)."""

    def __init__(
        self,
        message_repo: MessageRepository,
        session_repo: SessionRepository,
        summary_repo: Any,  # SummaryRepository - avoiding circular import
        session_maker: async_sessionmaker[AsyncSession],
        openai_client: OpenAIClient | None = None,
    ) -> None:
        """Initialize conversation manager.

        Args:
            message_repo: Message repository instance
            session_repo: Session repository instance
            summary_repo: Summary repository instance
            session_maker: Async session maker for background tasks
            openai_client: OpenAI client for summarization (optional)
        """
        self.message_repo = message_repo
        self.session_repo = session_repo
        self.summary_repo = summary_repo
        self.session_maker = session_maker
        self.openai_client = openai_client
        # Background tasks for async summarization
        self._summarization_tasks: dict[str, asyncio.Task] = {}

    async def save_user_message(
        self,
        session: AsyncSession,
        session_id: str,
        content: str,
    ) -> Message:
        """Save a user message to the database.

        Args:
            session: Database session
            session_id: Chat session identifier
            content: Message content

        Returns:
            Message: Saved message entity
        """
        return await self.message_repo.create(
            session=session,
            session_id=session_id,
            role="user",
            content=content,
        )

    async def save_assistant_message(
        self,
        session: AsyncSession,
        session_id: str,
        content: str,
    ) -> Message:
        """Save an assistant message to the database.

        Args:
            session: Database session
            session_id: Chat session identifier
            content: Message content

        Returns:
            Message: Saved message entity
        """
        return await self.message_repo.create(
            session=session,
            session_id=session_id,
            role="assistant",
            content=content,
        )

    async def load_conversation_history(
        self,
        session: AsyncSession,
        session_id: str,
        optimize: bool = True,
    ) -> tuple[list[Message], bool]:
        """Load conversation history with optional optimization.

        Args:
            session: Database session
            session_id: Chat session identifier
            optimize: Whether to apply summarization and pruning

        Returns:
            tuple[list[Message], bool]: (optimized messages, was_summarized flag)
        """
        all_messages = await self.message_repo.get_by_session(session, session_id)

        if not optimize or len(all_messages) <= SUMMARIZE_THRESHOLD:
            return all_messages, False

        # Apply optimizations
        logger.info(f"Optimizing history: {len(all_messages)} messages")

        # Step 1: Prune old tool messages
        pruned_messages = self._prune_tool_messages(all_messages)

        # Step 2: If still too long, summarize old messages
        if len(pruned_messages) > SUMMARIZE_THRESHOLD:
            optimized_messages = await self._summarize_old_messages(
                session, session_id, pruned_messages
            )
            return optimized_messages, True

        return pruned_messages, False

    def _prune_tool_messages(self, messages: list[Message]) -> list[Message]:
        """Remove old tool result messages to save tokens.

        Keeps only the most recent tool results, as older ones are usually
        not relevant to current conversation.

        Args:
            messages: Full message history

        Returns:
            list[Message]: Messages with old tool results removed
        """
        pruned: list[Message] = []
        tool_count = 0

        # Process messages in reverse to keep recent tool results
        for msg in reversed(messages):
            # Check for tool role (cast to Any for future tool support)
            if str(msg.role) == "tool":
                tool_count += 1
                if tool_count > MAX_TOOL_RESULTS:
                    continue  # Skip old tool results
            pruned.insert(0, msg)

        removed = len(messages) - len(pruned)
        if removed > 0:
            logger.info(f"Pruned {removed} old tool messages")
        return pruned

    async def _summarize_old_messages(
        self,
        session: AsyncSession,
        session_id: str,
        messages: list[Message],
    ) -> list[Message]:
        """Summarize old messages and keep recent ones verbatim.

        Uses caching and async generation to avoid blocking the main flow.

        Args:
            session: Database session
            session_id: Session identifier
            messages: Messages to summarize

        Returns:
            list[Message]: Summary + recent messages
        """
        if len(messages) <= MAX_RECENT_MESSAGES:
            return messages

        # Split messages
        old_messages = messages[:-MAX_RECENT_MESSAGES]
        recent_messages = messages[-MAX_RECENT_MESSAGES:]
        old_count = len(old_messages)

        logger.info(
            f"Summarizing {old_count} old messages, keeping {len(recent_messages)} recent"
        )

        # Get summary from cache or generate
        summary_content = await self._get_or_generate_summary(
            session, session_id, old_messages, old_count
        )

        # If no summary available, skip summarization and try again next time
        if not summary_content:
            logger.info(
                f"Summary not available for session {session_id}, skipping optimization"
            )
            return messages

        # Store summary in the conversation manager so it can be injected into system prompt
        # Instead of creating a fake Message, we'll prepend summary to first recent message
        if recent_messages and recent_messages[0].role == "user":
            # Clone first message with summary prepended
            first_msg = recent_messages[0]
            modified_first = Message(
                id=first_msg.id,
                session_id=first_msg.session_id,
                role=first_msg.role,
                content=f"[Context from earlier in conversation: {summary_content}]\n\n{first_msg.content}",
                created_at=first_msg.created_at,
            )
            return [modified_first] + recent_messages[1:]

        # If no user messages in recent, just return recent messages
        return recent_messages

    async def _get_or_generate_summary(
        self,
        db_session: AsyncSession,
        session_id: str,
        messages: list[Message],
        message_count: int,
    ) -> str | None:
        """Get summary from cache or generate it.

        Reuses existing summaries if less than RESUMMARIZE_THRESHOLD new messages.
        Otherwise triggers background generation of a new summary.

        Args:
            db_session: Database session
            session_id: Session identifier
            messages: Messages to summarize
            message_count: Number of messages

        Returns:
            str | None: Summary content or None if unavailable
        """
        # Try database cache first
        cached_summary, cached_count = await self._get_cached_summary(
            db_session, session_id, message_count
        )

        if cached_summary:
            messages_since_summary = message_count - cached_count

            # Reuse summary if not too many new messages
            if messages_since_summary < RESUMMARIZE_THRESHOLD:
                logger.info(
                    f"Reusing summary for session {session_id} "
                    f"(covers {cached_count}/{message_count} messages)"
                )
                return cached_summary

            # Too many new messages, need to re-summarize
            logger.info(
                f"Re-summarization needed for session {session_id} "
                f"({messages_since_summary} new messages since last summary)"
            )
            # Fall through to generate new summary

        # Try ongoing task
        task_result = await self._try_get_from_task(session_id)
        if task_result:
            return task_result

        # Generate new summary (may return None)
        # Pass previous summary for incremental update if available
        previous_summary = cached_summary if cached_summary else None
        previous_count = cached_count if cached_summary else 0
        return await self._generate_new_summary(
            session_id, messages, message_count, previous_summary, previous_count
        )

    async def _try_get_from_task(self, session_id: str) -> str | None:
        """Try to get summary from ongoing background task.

        Args:
            session_id: Session identifier

        Returns:
            str | None: Summary if available, None otherwise
        """
        if session_id not in self._summarization_tasks:
            return None

        task = self._summarization_tasks[session_id]
        if task.done():
            return None

        logger.info(f"Waiting for ongoing summarization task for session {session_id}")
        try:
            return await asyncio.wait_for(task, timeout=5.0)
        except TimeoutError:
            logger.warning(f"Summarization timeout for session {session_id}")
            return None

    async def _generate_new_summary(
        self,
        session_id: str,
        messages: list[Message],
        message_count: int,
        previous_summary: str | None = None,
        previous_count: int = 0,
    ) -> str | None:
        """Generate a new summary and cache it.

        Args:
            session_id: Session identifier
            messages: Messages to summarize
            message_count: Number of messages
            previous_summary: Previous summary to build upon (for incremental)
            previous_count: Number of messages in previous summary

        Returns:
            str | None: Generated summary or None if unavailable
        """
        # Start background AI summarization if client available
        if self.openai_client:
            self._start_background_summarization(
                session_id, messages, message_count, previous_summary, previous_count
            )

        # Return None to indicate no summary available yet
        return None

    async def _get_cached_summary(
        self, db_session: AsyncSession, session_id: str, message_count: int
    ) -> tuple[str | None, int]:
        """Get cached summary from database if available.

        Returns the latest summary that covers fewer messages than current count.
        This allows reusing summaries when only a few new messages were added.

        Args:
            db_session: Database session
            session_id: Session identifier
            message_count: Number of messages to summarize

        Returns:
            tuple[str | None, int]: (summary_text, messages_covered_by_summary)
        """
        logger.info(f"Checking DB for cached summary: session={session_id}")
        summary = await self.summary_repo.get_for_session(db_session, session_id)
        if summary:
            logger.info(
                f"Found cached summary: session={session_id}, "
                f"covers {summary.message_count} messages, "
                f"current={message_count}"
            )
            return summary.summary_text, summary.message_count
        logger.info(f"No cached summary found in DB: session={session_id}")
        return None, 0

    async def _cache_summary(
        self,
        db_session: AsyncSession,
        session_id: str,
        message_count: int,
        summary: str,
    ) -> None:
        """Cache a summary to database.

        Args:
            db_session: Database session
            session_id: Session identifier
            message_count: Number of messages summarized
            summary: Summary text
        """
        logger.info(
            f"Caching summary: session={session_id}, "
            f"message_count={message_count}, "
            f"summary_length={len(summary)}"
        )
        await self.summary_repo.upsert(db_session, session_id, message_count, summary)
        logger.info(
            f"Successfully persisted summary to DB: session={session_id} ({message_count} messages)"
        )

    def _handle_background_task_completion(
        self, task: asyncio.Task, session_id: str
    ) -> None:
        """Handle completion of background summarization task.

        This callback catches any exceptions that weren't caught in the task itself.

        Args:
            task: The completed task
            session_id: Session identifier
        """
        try:
            # This will raise if the task failed
            task.result()
        except asyncio.CancelledError:
            logger.info(f"Background summarization cancelled for session {session_id}")
        except Exception as e:
            logger.error(
                f"Background summarization failed for session {session_id}: {e}",
                exc_info=True,
            )

    def _start_background_summarization(
        self,
        session_id: str,
        messages: list[Message],
        message_count: int,
        previous_summary: str | None = None,
        previous_count: int = 0,
    ) -> None:
        """Start background task to generate AI summary.

        Args:
            session_id: Session identifier
            messages: Messages to summarize
            message_count: Number of messages
            previous_summary: Previous summary for incremental update
            previous_count: Messages covered by previous summary
        """
        # Cancel existing task if any
        if session_id in self._summarization_tasks:
            old_task = self._summarization_tasks[session_id]
            if not old_task.done():
                old_task.cancel()

        # Start new background task
        task = asyncio.create_task(
            self._generate_and_cache_summary(
                session_id, messages, message_count, previous_summary, previous_count
            )
        )
        # Add done callback to catch unhandled exceptions
        task.add_done_callback(
            lambda t: self._handle_background_task_completion(t, session_id)
        )
        self._summarization_tasks[session_id] = task
        mode = "incremental" if previous_summary else "full"
        logger.info(f"Started {mode} background summarization for session {session_id}")

    async def _generate_and_cache_summary(
        self,
        session_id: str,
        messages: list[Message],
        message_count: int,
        previous_summary: str | None = None,
        previous_count: int = 0,
    ) -> str:
        """Generate summary and cache it (runs in background).

        Note: This creates its own database session since it runs in background.

        Args:
            session_id: Session identifier
            messages: Messages to summarize
            message_count: Number of messages
            previous_summary: Previous summary for incremental update
            previous_count: Messages covered by previous summary

        Returns:
            str: Generated summary
        """
        try:
            summary = await self._generate_summary(
                messages, previous_summary, previous_count
            )

            # Create new session for background task
            async with self.session_maker() as db_session:
                await self._cache_summary(
                    db_session, session_id, message_count, summary
                )
                await db_session.commit()
                logger.info(
                    f"Background task committed summary to DB: "
                    f"session={session_id}, message_count={message_count}"
                )

            logger.info(f"Background summarization complete for session {session_id}")
            return summary
        except Exception as e:
            logger.error(
                f"Background summarization failed for session {session_id}: {e}"
            )
            # Don't cache failures, will retry next time
            raise
        finally:
            # Clean up task reference
            if session_id in self._summarization_tasks:
                del self._summarization_tasks[session_id]

    async def _generate_summary(
        self,
        messages: list[Message],
        previous_summary: str | None = None,
        previous_count: int = 0,
    ) -> str:
        """Generate AI summary of messages.

        Uses incremental summarization when previous_summary is provided,
        otherwise creates a full summary.

        Args:
            messages: Messages to summarize
            previous_summary: Previous summary to build upon
            previous_count: Number of messages covered by previous summary

        Returns:
            str: Summary text
        """
        try:
            # Filter to user/assistant messages only
            relevant_messages = [
                msg for msg in messages if msg.role in ["user", "assistant"]
            ]

            if previous_summary and previous_count > 0:
                # Incremental: only summarize new messages
                new_messages = relevant_messages[previous_count:]
                new_messages_text = "\n".join(
                    [f"{msg.role}: {msg.content}" for msg in new_messages]
                )

                prompt = INCREMENTAL_SUMMARIZATION_PROMPT.format(
                    previous_summary=previous_summary, new_messages=new_messages_text
                )

                summary_msgs: list[ChatCompletionMessageParam] = [
                    ChatCompletionUserMessageParam(role="user", content=prompt)
                ]
                logger.info(
                    f"Incremental summarization: {len(new_messages)} new messages "
                    f"(previous covered {previous_count})"
                )
            else:
                # Full: summarize all messages
                conversation_text = "\n".join(
                    [f"{msg.role}: {msg.content}" for msg in relevant_messages]
                )

                summary_msgs = [
                    ChatCompletionSystemMessageParam(
                        role="system",
                        content=SUMMARIZATION_PROMPT,
                    ),
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=f"Conversation to summarize:\n{conversation_text}",
                    ),
                ]
                logger.info(f"Full summarization: {len(relevant_messages)} messages")

            if self.openai_client is None:
                raise ValueError("OpenAI client is required for summarization")

            response = await self.openai_client.create_chat_completion(
                messages=summary_msgs,
                temperature=0.3,  # Lower temperature for more focused summary
                max_tokens=200,
            )

            summary = response.choices[0].message.content
            if summary:
                logger.info(f"Generated AI summary: {len(summary)} chars")
                return summary

            logger.warning("OpenAI returned empty summary")
            raise ValueError("Empty summary returned")

        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            raise

    async def update_session_timestamp(
        self,
        session: AsyncSession,
        session_id: str,
    ) -> None:
        """Update session's last activity timestamp.

        Args:
            session: Database session
            session_id: Chat session identifier
        """
        await self.session_repo.update_timestamp(session, session_id)


class AgentService:
    """Orchestrates LLM agent workflow (Open/Closed Principle - extensible via composition).

    Session maker is injected via DI, service manages its own database sessions.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        openai_client: OpenAIClient,
        kb_service: KnowledgeBaseService,
        message_repo: MessageRepository,
        session_repo: SessionRepository,
        summary_repo: Any,  # SummaryRepository - avoiding circular import
    ) -> None:
        """Initialize agent service with its dependencies (Dependency Inversion Principle).

        Args:
            session_maker: Async session maker for database connections
            openai_client: OpenAI client instance
            kb_service: Knowledge base service instance
            message_repo: Message repository instance
            session_repo: Session repository instance
            summary_repo: Summary repository instance
        """
        self.session_maker = session_maker
        self.openai_client = openai_client

        # Delegate responsibilities to specialized components (Single Responsibility)
        self.tool_executor = ToolExecutor(kb_service)
        self.message_formatter = MessageFormatter()
        self.conversation_manager = ConversationManager(
            message_repo, session_repo, summary_repo, session_maker, openai_client
        )

        self.tools = ToolExecutor.get_tool_definitions()

    async def process_message(self, session_id: str, user_message: str) -> Message:
        """Process a user message and generate AI response with tool calling.

        This method orchestrates the agent workflow using specialized components.
        Uses a database transaction to ensure atomicity.

        Args:
            session_id: Chat session identifier
            user_message: User's message content

        Returns:
            Message: Assistant's response message
        """
        logger.info(f"Processing message in session {session_id}")

        async with self.session_maker() as db_session:
            try:
                # Save user message
                await self.conversation_manager.save_user_message(
                    db_session, session_id, user_message
                )

                # Load conversation history with optimization
                history, was_summarized = (
                    await self.conversation_manager.load_conversation_history(
                        db_session, session_id, optimize=True
                    )
                )

                # Convert to OpenAI format
                messages = self.message_formatter.to_openai_messages(history)

                # Log summarization for monitoring
                if was_summarized:
                    logger.info(
                        f"History optimization applied for session {session_id}"
                    )

                # Run agent loop
                assistant_message = await self._run_agent_loop(
                    db_session, session_id, messages
                )

                # Update session timestamp and commit
                await self.conversation_manager.update_session_timestamp(
                    db_session, session_id
                )
                await db_session.commit()

                return assistant_message

            except Exception as e:
                await db_session.rollback()
                logger.error(f"Error processing message in session {session_id}: {e}")
                raise

    async def _run_agent_loop(
        self,
        db_session: AsyncSession,
        session_id: str,
        messages: list[ChatCompletionMessageParam],
    ) -> Message:
        """Run the agent reasoning loop with tool calling.

        Args:
            db_session: Database session
            session_id: Chat session identifier
            messages: Current conversation messages

        Returns:
            Message: Final assistant message

        Raises:
            Exception: If max iterations reached or LLM error occurs
        """
        for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
            logger.debug(f"Agent iteration {iteration}/{MAX_AGENT_ITERATIONS}")

            response = await self.openai_client.create_chat_completion(
                messages=messages,
                tools=self.tools,
                temperature=0.7,
            )

            llm_message = response.choices[0].message

            # Check if LLM wants to use tools
            if llm_message.tool_calls:
                await self._handle_tool_calls(
                    db_session, session_id, messages, llm_message
                )
                continue  # Loop again for final response

            # No tool calls - we have the final answer
            return await self._save_final_response(
                db_session, session_id, llm_message.content or ""
            )

        # Max iterations exceeded
        logger.warning(f"Max iterations reached for session {session_id}")
        return await self._save_error_response(db_session, session_id)

    async def _handle_tool_calls(
        self,
        db_session: AsyncSession,
        session_id: str,
        messages: list[ChatCompletionMessageParam],
        llm_message: Any,
    ) -> None:
        """Handle tool calls requested by the LLM.

        Args:
            db_session: Database session
            session_id: Chat session identifier
            messages: Current conversation messages (modified in place)
            llm_message: LLM response containing tool calls
        """
        logger.info(f"LLM requested {len(llm_message.tool_calls)} tool calls")

        # Add assistant's message with tool calls to in-memory conversation
        # NOTE: We do NOT save this to the database during the agent loop because:
        # 1. We can't persist the tool_calls structure in our current schema
        # 2. The in-memory messages list already has the full context for OpenAI
        # 3. Tool messages are saved, but they're only valid within this conversation context
        messages.append(
            self.message_formatter.create_assistant_message_with_tools(
                content=llm_message.content or "",
                tool_calls=llm_message.tool_calls,
            )
        )

        # Execute each tool call
        for tool_call in llm_message.tool_calls:
            await self._execute_single_tool_call(
                db_session, session_id, messages, tool_call
            )

    async def _execute_single_tool_call(
        self,
        db_session: AsyncSession,
        session_id: str,
        messages: list[ChatCompletionMessageParam],
        tool_call: Any,
    ) -> None:
        """Execute a single tool call and save the result.

        This method ensures the AI always receives a tool response, even if:
        - Tool arguments are malformed JSON
        - Tool execution fails
        - Unknown errors occur

        This prevents the AI from hanging indefinitely waiting for tool results.

        Args:
            db_session: Database session
            session_id: Chat session identifier
            messages: Current conversation messages (modified in place)
            tool_call: Tool call object from OpenAI
        """
        function_name = tool_call.function.name

        try:
            # Parse tool arguments (may fail if LLM generated invalid JSON)
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in tool arguments: {e}")
                tool_result = "Error: Invalid tool arguments (malformed JSON). Please try again with valid JSON."
                function_args = {}
            else:
                # Execute the tool (tool_executor.execute never raises, always returns result)
                tool_result = await self.tool_executor.execute(
                    function_name, function_args
                )

            # NOTE: We do NOT save tool results to the database because:
            # 1. They would be orphaned (no preceding assistant message with tool_calls in DB)
            # 2. They're intermediate steps in the reasoning process
            # 3. Only the final assistant response is persisted
            # The tool results exist only in the in-memory conversation for this request

        except Exception as e:
            # Last resort: catch any unexpected errors
            error_result = f"Critical error executing tool '{function_name}': {str(e)}"
            logger.error(
                f"Critical tool execution error: {error_result}", exc_info=True
            )
            tool_result = error_result

        # CRITICAL: Always add tool result to conversation, even on error
        # This ensures the AI receives a response and doesn't hang waiting
        messages.append(
            self.message_formatter.create_tool_message(tool_call.id, tool_result)
        )

    async def _save_final_response(
        self,
        db_session: AsyncSession,
        session_id: str,
        content: str,
    ) -> Message:
        """Save the assistant's final response.

        Args:
            db_session: Database session
            session_id: Chat session identifier
            content: Response content

        Returns:
            Message: Saved assistant message
        """
        logger.info("Agent produced final response")
        return await self.conversation_manager.save_assistant_message(
            db_session, session_id, content
        )

    async def _save_error_response(
        self,
        db_session: AsyncSession,
        session_id: str,
    ) -> Message:
        """Save an error response when max iterations are exceeded.

        Args:
            db_session: Database session
            session_id: Chat session identifier

        Returns:
            Message: Saved error message
        """
        error_content = (
            "I apologize, but I encountered an issue processing your request. "
            "Please try again."
        )
        return await self.conversation_manager.save_assistant_message(
            db_session, session_id, error_content
        )
