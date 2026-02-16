"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import json_repair
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.context import ContextBuilder
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.memory import MemoryStore
from nanobot.agent.subagent import SubagentManager
from nanobot.session.manager import Session, SessionManager

if TYPE_CHECKING:
    from nanobot.config.schema import ExecToolConfig, HonchoConfig
    from nanobot.cron.service import CronService
    from nanobot.honcho.session import HonchoSessionManager


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_window: int = 50,
        brave_api_key: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        honcho_config: HonchoConfig | None = None,
        mcp_servers: dict | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.honcho_config = honcho_config
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_window = memory_window
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace

        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._running = False
        self._honcho: HonchoSessionManager | None = None
        self._honcho_migrated: set[str] = set()  # sessions already checked for migration
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._register_default_tools()

    # ── Honcho integration ──────────────────────────────────────────

    @property
    def honcho_active(self) -> bool:
        """True when Honcho is initialized and ready."""
        return self._honcho is not None

    def _honcho_set_context(self, session_key: str) -> None:
        """Set session context on Honcho tools and ensure the Honcho session exists."""
        if not self.honcho_active:
            return
        for tool_name in ("query_user_context",):
            tool = self.tools.get(tool_name)
            if tool and hasattr(tool, "set_context"):
                tool.set_context(session_key)
        self._honcho.get_or_create(session_key)
        if session_key not in self._honcho_migrated:
            self._honcho_migrated.add(session_key)
            self._maybe_migrate_local_session(session_key)

    def _maybe_migrate_local_session(self, session_key: str) -> None:
        """
        Auto-migrate local data to Honcho on first activation per session key.

        Migrates both:
        1. JSONL session history (per-session message files)
        2. MEMORY.md + HISTORY.md (consolidated memory from upstream's memory system)

        Called once per session key (guarded by _honcho_migrated set in _honcho_set_context).
        Skips if Honcho session already has messages (idempotent).
        Backwards compatible -- gracefully skips files that don't exist.
        """
        honcho_session = self._honcho.get_or_create(session_key)
        if honcho_session.messages:
            return

        migrated_anything = False

        # 1. Migrate JSONL session messages
        local_session = self.sessions.get_or_create(session_key)
        real_messages = [m for m in local_session.messages if m.get("role") in ("user", "assistant")]
        if real_messages:
            logger.info(f"Migrating {len(real_messages)} local messages to Honcho for {session_key}")
            ok = self._honcho.migrate_local_history(session_key, real_messages)
            if ok:
                sessions_dir = Path.home() / ".nanobot" / "sessions"
                from nanobot.utils.helpers import safe_filename
                safe_key = safe_filename(session_key.replace(":", "_"))
                src = sessions_dir / f"{safe_key}.jsonl"
                if src.exists():
                    archive_dir = sessions_dir / "migrated"
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    src.rename(archive_dir / src.name)
                    logger.info(f"Archived {src.name} to sessions/migrated/")
                migrated_anything = True
            else:
                logger.warning(f"Session migration failed for {session_key}, will retry next time")

        # 2. Migrate MEMORY.md + HISTORY.md (if they exist)
        memory_dir = self.workspace / "memory"
        if memory_dir.exists() and any(memory_dir.iterdir()):
            if self._honcho.migrate_memory_files(session_key, self.workspace):
                archive_dir = memory_dir / "migrated"
                archive_dir.mkdir(parents=True, exist_ok=True)
                for f in ("MEMORY.md", "HISTORY.md"):
                    src = memory_dir / f
                    if src.exists():
                        src.rename(archive_dir / src.name)
                        logger.info(f"Archived {f} to memory/migrated/")
                migrated_anything = True

        if migrated_anything:
            logger.info(f"Local data migration to Honcho complete for {session_key}")

    def _honcho_prefetch(self, session_key: str, user_message: str) -> str:
        """Fetch user context from Honcho for system prompt injection. Returns empty string if unavailable."""
        if not self.honcho_active or not self.honcho_config or not self.honcho_config.prefetch:
            return ""
        try:
            ctx = self._honcho.get_prefetch_context(session_key, user_message=user_message)
            parts = []
            if ctx.get("representation"):
                parts.append(f"User profile: {ctx['representation']}")
            if ctx.get("card"):
                parts.append(f"User context: {ctx['card']}")
            return "\n\n# Honcho User Context\n\n" + "\n\n".join(parts) if parts else ""
        except Exception as e:
            logger.warning(f"Honcho prefetch failed: {e}")
            return ""

    def _honcho_sync(self, session_key: str, user_content: str, assistant_content: str) -> None:
        """Sync a message pair to Honcho storage."""
        if not self.honcho_active:
            return
        try:
            honcho_session = self._honcho.get_or_create(session_key)
            honcho_session.add_message("user", user_content)
            honcho_session.add_message("assistant", assistant_content)
            self._honcho.save(honcho_session)
        except Exception as e:
            logger.warning(f"Honcho sync failed: {e}")

    # ── MCP integration ─────────────────────────────────────────────

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or not self._mcp_servers:
            return
        self._mcp_connected = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        self._mcp_stack = AsyncExitStack()
        await self._mcp_stack.__aenter__()
        await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    # ── Tool context ────────────────────────────────────────────────

    def _set_tool_context(self, channel: str, chat_id: str) -> None:
        """Update context for all tools that need routing info."""
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.set_context(channel, chat_id)

        if spawn_tool := self.tools.get("spawn"):
            if isinstance(spawn_tool, SpawnTool):
                spawn_tool.set_context(channel, chat_id)

        if cron_tool := self.tools.get("cron"):
            if isinstance(cron_tool, CronTool):
                cron_tool.set_context(channel, chat_id)

    # ── Tool registration ───────────────────────────────────────────

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File tools (restrict to workspace if configured)
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        self.tools.register(ReadFileTool(allowed_dir=allowed_dir))
        self.tools.register(WriteFileTool(allowed_dir=allowed_dir))
        self.tools.register(EditFileTool(allowed_dir=allowed_dir))
        self.tools.register(ListDirTool(allowed_dir=allowed_dir))

        # Shell tool
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))

        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())

        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)

        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)

        # Cron tool (for scheduling)
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

        # Honcho tools (opt-in: requires honcho.enabled + HONCHO_API_KEY)
        if self.honcho_config and self.honcho_config.enabled:
            import os
            if os.environ.get("HONCHO_API_KEY"):
                try:
                    from nanobot.honcho.client import get_honcho_client, HonchoClientConfig
                    from nanobot.honcho.session import HonchoSessionManager
                    from nanobot.agent.tools.honcho import HonchoTool

                    client_config = HonchoClientConfig(
                        workspace_id=self.honcho_config.workspace_id,
                        api_key=os.environ["HONCHO_API_KEY"],
                        environment=self.honcho_config.environment,
                    )
                    get_honcho_client(client_config)
                    self._honcho = HonchoSessionManager(
                        context_tokens=self.honcho_config.context_tokens,
                    )

                    self.tools.register(HonchoTool(session_manager=self._honcho))

                    logger.info("Honcho tools registered (query_user_context)")
                except ImportError:
                    logger.warning("Honcho enabled but honcho-ai not installed. Run: nanobot honcho enable")
                except Exception as e:
                    logger.warning(f"Failed to initialize Honcho: {e}")

    # ── Agent iteration loop ────────────────────────────────────────

    async def _run_agent_loop(self, initial_messages: list[dict]) -> tuple[str | None, list[str]]:
        """
        Run the agent iteration loop.

        Args:
            initial_messages: Starting messages for the LLM conversation.

        Returns:
            Tuple of (final_content, list_of_tools_used).
        """
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                messages.append({"role": "user", "content": "Reflect on the results and decide next steps."})
            else:
                final_content = response.content
                break

        return final_content, tools_used

    # ── Main loop ───────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )

                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_message(self, msg: InboundMessage, session_key: str | None = None) -> OutboundMessage | None:
        """
        Process a single inbound message.

        Args:
            msg: The inbound message to process.
            session_key: Override session key (used by process_direct).

        Returns:
            The response message, or None if no response needed.
        """
        # System messages route back via chat_id ("channel:chat_id")
        if msg.channel == "system":
            return await self._process_system_message(msg)

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Handle slash commands
        cmd = msg.content.strip().lower()
        if cmd in ("/new", "/clear"):
            # Capture messages before clearing (avoid race condition with background task)
            messages_to_archive = session.messages.copy()
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)

            # Rotate Honcho session (preserves old data for user modeling)
            if self.honcho_active:
                self._honcho.new_session(msg.session_key)
                logger.info(f"Rotated Honcho session for {msg.session_key}")

            async def _consolidate_and_cleanup():
                temp_session = Session(key=session.key)
                temp_session.messages = messages_to_archive
                await self._consolidate_memory(temp_session, archive_all=True)

            asyncio.create_task(_consolidate_and_cleanup())
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="Session cleared.")
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="nanobot commands:\n/new — Start a new conversation\n/clear — Clear session and start fresh\n/help — Show available commands")

        # Consolidate memory before processing if session is too large
        if len(session.messages) > self.memory_window:
            if self.honcho_active:
                # Honcho handles persistence via _honcho_sync; just trim locally
                keep_count = min(10, max(2, self.memory_window // 2))
                session.messages = session.messages[-keep_count:]
                self.sessions.save(session)
            else:
                asyncio.create_task(self._consolidate_memory(session))

        # Update tool contexts
        self._set_tool_context(msg.channel, msg.chat_id)

        # Honcho: set tool contexts + prefetch user context
        self._honcho_set_context(msg.session_key)
        honcho_context = self._honcho_prefetch(msg.session_key, msg.content)

        # Build initial messages
        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        # Inject Honcho context into system prompt
        if honcho_context and initial_messages and initial_messages[0].get("role") == "system":
            initial_messages[0]["content"] += honcho_context

        # Run agent loop
        final_content, tools_used = await self._run_agent_loop(initial_messages)

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        # Log response preview
        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")

        # Save to session (include tool names so consolidation sees what happened)
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content,
                            tools_used=tools_used if tools_used else None)

        if self.honcho_active:
            # Honcho is the source of truth -- sync there, keep local session as in-memory window only
            self._honcho_sync(msg.session_key, msg.content, final_content)
        else:
            self.sessions.save(session)

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},  # Pass through for channel-specific needs (e.g. Slack thread_ts)
        )

    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).

        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")

        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id

        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        self._set_tool_context(origin_channel, origin_chat_id)

        # Honcho: set tool contexts (no prefetch for system messages)
        self._honcho_set_context(session_key)

        initial_messages = self.context.build_messages(
            history=session.get_history(max_messages=self.memory_window),
            current_message=msg.content,
            channel=origin_channel,
            chat_id=origin_chat_id,
        )
        final_content, _ = await self._run_agent_loop(initial_messages)

        if final_content is None:
            final_content = "Background task completed."

        user_content = f"[System: {msg.sender_id}] {msg.content}"
        session.add_message("user", user_content)
        session.add_message("assistant", final_content)

        if self.honcho_active:
            self._honcho_sync(session_key, user_content, final_content)
        else:
            self.sessions.save(session)

        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )

    async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
        """Consolidate old messages into MEMORY.md + HISTORY.md.

        Args:
            archive_all: If True, clear all messages and reset session (for /new command).
                       If False, only write to files without modifying session.
        """
        memory = MemoryStore(self.workspace)

        if archive_all:
            old_messages = session.messages
            keep_count = 0
            logger.info(f"Memory consolidation (archive_all): {len(session.messages)} total messages archived")
        else:
            keep_count = self.memory_window // 2
            if len(session.messages) <= keep_count:
                logger.debug(f"Session {session.key}: No consolidation needed (messages={len(session.messages)}, keep={keep_count})")
                return

            messages_to_process = len(session.messages) - session.last_consolidated
            if messages_to_process <= 0:
                logger.debug(f"Session {session.key}: No new messages to consolidate (last_consolidated={session.last_consolidated}, total={len(session.messages)})")
                return

            old_messages = session.messages[session.last_consolidated:-keep_count]
            if not old_messages:
                return
            logger.info(f"Memory consolidation started: {len(session.messages)} total, {len(old_messages)} new to consolidate, {keep_count} keep")

        lines = []
        for m in old_messages:
            if not m.get("content"):
                continue
            tools = f" [tools: {', '.join(m['tools_used'])}]" if m.get("tools_used") else ""
            lines.append(f"[{m.get('timestamp', '?')[:16]}] {m['role'].upper()}{tools}: {m['content']}")
        conversation = "\n".join(lines)
        current_memory = memory.read_long_term()

        prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated long-term memory content. Only add facts that are clearly important and likely to recur. Do NOT extract trivia, one-off mentions, or casual details. If nothing new, return the existing content unchanged.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}

Respond with ONLY valid JSON, no markdown fences."""

        try:
            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )
            text = (response.content or "").strip()
            if not text:
                logger.warning("Memory consolidation: LLM returned empty response, skipping")
                return
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json_repair.loads(text)
            if not isinstance(result, dict):
                logger.warning(f"Memory consolidation: unexpected response type, skipping. Response: {text[:200]}")
                return

            if entry := result.get("history_entry"):
                memory.append_history(entry)
            if update := result.get("memory_update"):
                if update != current_memory:
                    memory.write_long_term(update)

            if archive_all:
                session.last_consolidated = 0
            else:
                session.last_consolidated = len(session.messages) - keep_count
            logger.info(f"Memory consolidation done: {len(session.messages)} messages, last_consolidated={session.last_consolidated}")
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).

        Args:
            content: The message content.
            session_key: Session identifier (overrides channel:chat_id for session lookup).
            channel: Source channel (for tool context routing).
            chat_id: Source chat ID (for tool context routing).


        Returns:
            The agent's response.
        """
        await self._connect_mcp()
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )

        response = await self._process_message(msg, session_key=session_key)
        return response.content if response else ""
