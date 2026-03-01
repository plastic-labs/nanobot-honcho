"""Honcho tool for memory recall."""

from typing import Any

from nanobot.agent.tools.base import Tool


class RecallTool(Tool):
    """
    Tool for querying Honcho's AI-native memory.

    Allows the agent to recall context about the user or about itself.
    """

    def __init__(self, session_manager: "HonchoSessionManager"):
        self._session_manager = session_manager
        self._current_session_key: str | None = None

    @property
    def name(self) -> str:
        return "recall"

    @property
    def description(self) -> str:
        return (
            "Recall context from memory. Use target='user' to retrieve information about "
            "the user (preferences, history, goals). Use target='self' to introspect on "
            "your own history and behavior patterns. Use this when conversation context "
            "alone isn't enough."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A natural language question. Examples: "
                        "'What are this user's main goals?', "
                        "'What communication style does this user prefer?', "
                        "'What tasks have I been working on recently?', "
                        "'What do I know about my own behavioral patterns?'"
                    ),
                },
                "target": {
                    "type": "string",
                    "enum": ["user", "self"],
                    "description": "Who to query about: 'user' for user context, 'self' for agent introspection.",
                },
            },
            "required": ["query", "target"],
        }

    def set_context(self, session_key: str) -> None:
        """Set the current session context."""
        self._current_session_key = session_key

    async def execute(self, query: str, target: str = "user") -> str:
        if not self._current_session_key:
            return "Error: No session context set. Unable to query."

        try:
            if target == "self":
                return self._session_manager.get_agent_context(
                    self._current_session_key, query
                )
            else:
                return self._session_manager.get_user_context(
                    self._current_session_key, query
                )
        except Exception as e:
            return f"Error querying context: {str(e)}"
