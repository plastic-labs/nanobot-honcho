"""Spawn tool for creating background subagents."""

from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """
    Tool to spawn a subagent for background task execution.
    
    The subagent runs asynchronously and announces its result back
    to the main agent when complete.
    """
    
    def __init__(self, manager: "SubagentManager"):
        self._manager = manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the origin context for subagent announcements."""
        self._origin_channel = channel
        self._origin_chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return (
            "Spawn a subagent to handle a task. "
            "Set wait=true to block until the subagent finishes and get its result "
            "directly (use for tasks you need before continuing). "
            "Set wait=false (default) to run in the background — the subagent "
            "will report back when done."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
                "wait": {
                    "type": "boolean",
                    "description": "If true, block until the subagent completes and return its result directly. If false (default), run in the background.",
                    "default": False,
                },
            },
            "required": ["task"],
        }

    async def execute(self, task: str, label: str | None = None, wait: bool = False, **kwargs: Any) -> str:
        """Spawn a subagent to execute the given task."""
        if wait:
            return await self._manager.run_sync(task=task, label=label)
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
