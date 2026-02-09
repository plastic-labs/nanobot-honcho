"""Context builder for assembling agent prompts."""

import base64
import json
import mimetypes
import platform
from pathlib import Path
from typing import Any, TYPE_CHECKING

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader

if TYPE_CHECKING:
    from nanobot.honcho.session import HonchoSessionManager
    from nanobot.providers.base import ToolCall


def format_tool_calls(tool_calls: list["ToolCall"]) -> list[dict[str, Any]]:
    """
    Convert ToolCall objects to the dict format expected by LLM APIs.

    Args:
        tool_calls: List of ToolCall objects from LLM response.

    Returns:
        List of tool call dicts with id, type, and function fields.
    """
    return [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.name,
                "arguments": json.dumps(tc.arguments),
            },
        }
        for tc in tool_calls
    ]


class ContextBuilder:
    """
    Builds the context (system prompt + messages) for the agent.
    
    Assembles bootstrap files, memory, skills, and conversation history
    into a coherent prompt for the LLM.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(
        self,
        workspace: Path,
        honcho_session_manager: "HonchoSessionManager | None" = None,
    ):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
        self.honcho_session_manager = honcho_session_manager
    
    def build_system_prompt(
        self,
        skill_names: list[str] | None = None,
        user_context: dict[str, str] | None = None,
    ) -> str:
        """
        Build the system prompt from bootstrap files, memory, and skills.

        Args:
            skill_names: Optional list of skills to include.
            user_context: Optional pre-fetched user context from Honcho.

        Returns:
            Complete system prompt.
        """
        parts = []

        # Core identity
        parts.append(self._get_identity())
        
        # Bootstrap files
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        # Memory context (only for legacy file-based memory, skip if Honcho is enabled)
        if self.honcho_session_manager is None:
            memory = self.memory.get_memory_context()
            if memory:
                parts.append(f"# Memory\n\n{memory}")

        # Honcho user context (pre-fetched via single context() call with semantic search)
        if user_context:
            context_parts = []
            if user_context.get("representation"):
                context_parts.append(f"## User Representation\n{user_context['representation']}")
            if user_context.get("card"):
                context_parts.append(f"## User Card\n{user_context['card']}")
            if context_parts:
                parts.append(
                    "# User Context (from Honcho)\n\n"
                    + "\n\n".join(context_parts)
                )
        
        # Skills - progressive loading
        # 1. Always-loaded skills: include full content
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # 2. Available skills: only show summary (agent uses read_file to load)
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills are available. Load a skill by reading its SKILL.md file, if relevant to what the user is asking.
Skills with available="false" need dependencies installed first.

{skills_summary}""")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """Get the core identity section."""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"

        # Memory section depends on whether Honcho is enabled
        if self.honcho_session_manager is not None:
            memory_section = """## Memory
Honcho manages your memory and learns about users automatically from conversations.
Conversation history is persistent across sessions -- no manual storage needed.
Use `/clear` to reset the conversation and start fresh."""
        else:
            memory_section = f"""## Workspace
Your workspace is at: {workspace_path}
- Memory files: {workspace_path}/memory/MEMORY.md
- Daily notes: {workspace_path}/memory/YYYY-MM-DD.md
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md

When remembering something important, write to {workspace_path}/memory/MEMORY.md"""

        return f"""# nanobot

You are nanobot, a personal AI companion. Your primary role is to have natural conversations with your user. Conversation is your default mode.

You have access to tools (file operations, shell, web search, messaging, subagents), but most messages just need a thoughtful reply. Use this decision framework:

**Respond with text** (most of the time):
- Greetings, small talk, casual conversation
- Questions you can answer from knowledge or conversation context
- Opinions, advice, brainstorming, emotional support
- Follow-ups to previous messages
- Acknowledging or thanking

**Use a tool only when the user's request requires it:**
- "What's the weather?" -> web search
- "Create a file called X" -> file operation
- "Run this command" -> shell execution
- "Remind me at 3pm" -> cron
- A question specifically about something a tool can look up that you don't know

When in doubt, respond with text. A conversational reply is almost always better than a failed or unnecessary tool call.

Do NOT use the `message` tool for normal conversation -- just respond with text directly.

## Current Time
{now}

## Runtime
{runtime}

{memory_section}"""
    
    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        user_context: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Args:
            history: Previous conversation messages.
            current_message: The new user message.
            skill_names: Optional skills to include.
            media: Optional list of local file paths for images/media.
            channel: Current channel (telegram, feishu, etc.).
            chat_id: Current chat/user ID.
            user_context: Optional pre-fetched user context from Honcho.

        Returns:
            List of messages including system prompt.
        """
        messages = []

        # System prompt
        system_prompt = self.build_system_prompt(skill_names, user_context=user_context)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        # History
        messages.extend(history)

        # Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text
        
        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        
        if not images:
            return text
        return images + [{"type": "text", "text": text}]
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        Add a tool result to the message list.
        
        Args:
            messages: Current message list.
            tool_call_id: ID of the tool call.
            tool_name: Name of the tool.
            result: Tool execution result.
        
        Returns:
            Updated message list.
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Add an assistant message to the message list.
        
        Args:
            messages: Current message list.
            content: Message content.
            tool_calls: Optional tool calls.
        
        Returns:
            Updated message list.
        """
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        messages.append(msg)
        return messages
