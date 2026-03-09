"""Context builder for assembling agent messages."""

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any


class ContextBuilder:
    """
    Builds the message array for the agent.

    Assembles lore turns from SOUL.md, Honcho session context,
    and conversation history into a message list for the LLM.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace

    # ── Message assembly ─────────────────────────────────────────────

    def build_messages(
        self,
        current_message: str,
        history: list[dict[str, Any]] | None = None,
        honcho_context: dict[str, Any] | None = None,
        media: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the complete message list for an LLM call.

        Message array structure:
          1. Lore turns from SOUL.md (identity narrative)
          2. Honcho context injection (peer_representation, peer_card, summary)
          3. Session history messages
          4. Current user message

        Args:
            current_message: The new user message.
            history: Previous conversation messages (from local session or Honcho).
            honcho_context: Optional dict with keys:
                - peer_representation: str | None
                - peer_card: list[str] | str | None
                - summary: str | None
            media: Optional list of local file paths for images/media.

        Returns:
            List of messages for the LLM.
        """
        messages = []

        # 1. Lore turns from SOUL.md
        messages.extend(self._parse_lore_file())

        # 2. Honcho context injection (representation, card, summary)
        if honcho_context:
            context_parts = []
            if honcho_context.get("peer_representation"):
                context_parts.append(
                    f"<peer_representation>{honcho_context['peer_representation']}</peer_representation>"
                )
            if honcho_context.get("peer_card"):
                card = honcho_context["peer_card"]
                if isinstance(card, list):
                    card = "\n".join(card)
                context_parts.append(f"<peer_card>{card}</peer_card>")
            if honcho_context.get("summary"):
                context_parts.append(
                    f"<summary>{honcho_context['summary']}</summary>"
                )

            if context_parts:
                context_content = "Here's your context for this session:\n\n" + "\n\n".join(context_parts)
                if history:
                    context_content += "\n\nWhat follows is your recent chat history with me."
                messages.append({"role": "user", "content": context_content})
                messages.append({
                    "role": "assistant",
                    "content": "Got it, I have context on you and a summary of where we left off. Ready.",
                })

        # 3. Session history
        if history:
            messages.extend(history)

        # 4. Current message (with optional image attachments)
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    # ── Lore parsing ─────────────────────────────────────────────────

    def _parse_lore_file(self) -> list[dict[str, str]]:
        """
        Parse SOUL.md into a list of user/assistant message dicts.

        Extracts <turn role="user|assistant">...</turn> blocks.
        Text outside turn blocks is discarded.
        """
        soul_path = self.workspace / "SOUL.md"
        if not soul_path.exists():
            return []

        text = soul_path.read_text(encoding="utf-8")
        turns = re.findall(
            r'<turn\s+role="(user|assistant)">\s*(.*?)\s*</turn>',
            text,
            re.DOTALL,
        )
        return [{"role": role, "content": content.strip()} for role, content in turns]

    # ── Helpers ───────────────────────────────────────────────────────

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
        """Add a tool result to the message list."""
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
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """Add an assistant message to the message list."""
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}

        if tool_calls:
            msg["tool_calls"] = tool_calls

        # Thinking models reject history without this
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content

        messages.append(msg)
        return messages
