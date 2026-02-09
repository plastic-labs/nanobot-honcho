"""Subagent manager for background task execution."""

import asyncio
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.core import run_loop, register_standard_tools
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.budget import SpendBudget


class SubagentManager:
    """
    Manages background subagent execution.
    
    Subagents are lightweight agent instances that run in the background
    to handle specific tasks. They share the same LLM provider but have
    isolated context and a focused system prompt.
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        bus: MessageBus,
        model: str | None = None,
        brave_api_key: str | None = None,
        exec_config: "ExecToolConfig | None" = None,
        restrict_to_workspace: bool = False,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.provider = provider
        self.workspace = workspace
        self.bus = bus
        self.model = model or provider.get_default_model()
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.restrict_to_workspace = restrict_to_workspace
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._shared_budget: SpendBudget | None = None

    def set_shared_budget(self, budget: SpendBudget | None) -> None:
        """Set the shared budget for subagents to draw from."""
        self._shared_budget = budget
    
    async def spawn(
        self,
        task: str,
        label: str | None = None,
        origin_channel: str = "cli",
        origin_chat_id: str = "direct",
        context_summary: str | None = None,
        relevant_files: list[str] | None = None,
        user_context: dict[str, str] | None = None,
    ) -> str:
        """
        Spawn a subagent to execute a task in the background.

        Args:
            task: The task description for the subagent.
            label: Optional human-readable label for the task.
            origin_channel: The channel to announce results to.
            origin_chat_id: The chat ID to announce results to.
            context_summary: Optional summary of conversation context for the subagent.
            relevant_files: Optional list of file paths relevant to the task.
            user_context: Optional user preferences from Honcho.

        Returns:
            Status message indicating the subagent was started.
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or task[:30] + ("..." if len(task) > 30 else "")

        origin = {
            "channel": origin_channel,
            "chat_id": origin_chat_id,
        }

        # Create background task
        bg_task = asyncio.create_task(
            self._run_subagent(
                task_id, task, display_label, origin,
                context_summary=context_summary,
                relevant_files=relevant_files,
                user_context=user_context,
            )
        )
        self._running_tasks[task_id] = bg_task

        # Cleanup when done
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))

        logger.info(f"Spawned subagent [{task_id}]: {display_label}")
        return f"Subagent [{display_label}] started (id: {task_id}). I'll notify you when it completes."
    
    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
        context_summary: str | None = None,
        relevant_files: list[str] | None = None,
        user_context: dict[str, str] | None = None,
    ) -> None:
        """Execute the subagent task and announce the result."""
        logger.info(f"Subagent [{task_id}] starting task: {label}")

        try:
            # Build subagent tools (no message tool, no spawn tool, no edit tool)
            tools = ToolRegistry()
            allowed_dir = self.workspace if self.restrict_to_workspace else None
            register_standard_tools(
                tools,
                self.workspace,
                allowed_dir=allowed_dir,
                include_edit=False,
                brave_api_key=self.brave_api_key,
                exec_timeout=self.exec_config.timeout,
                restrict_to_workspace=self.restrict_to_workspace,
            )

            # Build messages with subagent-specific prompt
            system_prompt = self._build_subagent_prompt(
                task,
                context_summary=context_summary,
                relevant_files=relevant_files,
                user_context=user_context,
            )
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            # Run agent loop (limited iterations)
            final_result, budget_exhausted = await run_loop(
                messages=messages,
                tools=tools,
                provider=self.provider,
                model=self.model,
                max_iterations=15,
                budget=self._shared_budget,
                cost_source=f"subagent:{task_id}",
            )

            if budget_exhausted:
                final_result = "Budget exhausted - stopping subagent"
            elif final_result is None:
                final_result = "Task completed but no final response was generated."

            logger.info(f"Subagent [{task_id}] completed successfully")
            await self._announce_result(task_id, label, task, final_result, origin, "ok")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Subagent [{task_id}] failed: {e}")
            await self._announce_result(task_id, label, task, error_msg, origin, "error")
    
    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
    ) -> None:
        """Announce the subagent result to the main agent via the message bus."""
        status_text = "completed successfully" if status == "ok" else "failed"
        
        announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""
        
        # Inject as system message to trigger main agent
        msg = InboundMessage(
            channel="system",
            sender_id="subagent",
            chat_id=f"{origin['channel']}:{origin['chat_id']}",
            content=announce_content,
        )
        
        await self.bus.publish_inbound(msg)
        logger.debug(f"Subagent [{task_id}] announced result to {origin['channel']}:{origin['chat_id']}")
    
    def _build_subagent_prompt(
        self,
        task: str,
        context_summary: str | None = None,
        relevant_files: list[str] | None = None,
        user_context: dict[str, str] | None = None,
    ) -> str:
        """Build a focused system prompt for the subagent."""
        parts = [f"""# Subagent

You are a subagent spawned by the main agent to complete a specific task.

## Your Task
{task}

## Rules
1. Stay focused - complete only the assigned task, nothing else
2. Your final response will be reported back to the main agent
3. Do not initiate conversations or take on side tasks
4. Be concise but informative in your findings

## What You Can Do
- Read and write files in the workspace
- Execute shell commands
- Search the web and fetch web pages
- Complete the task thoroughly

## What You Cannot Do
- Send messages directly to users (no message tool available)
- Spawn other subagents

## Workspace
Your workspace is at: {self.workspace}"""]

        # Add conversation context if provided
        if context_summary:
            parts.append(f"""
## Conversation Context
The main agent provided this summary of the relevant conversation context:
{context_summary}""")

        # Add user preferences if available
        if user_context:
            context_lines = []
            if user_context.get("representation"):
                context_lines.append(f"User Profile: {user_context['representation']}")
            if user_context.get("card"):
                context_lines.append(f"User Notes: {user_context['card']}")
            if context_lines:
                parts.append(f"""
## User Context (from Honcho)
{chr(10).join(context_lines)}
Consider these user preferences when completing your task.""")

        # Add relevant files
        if relevant_files:
            files_list = "\n".join(f"- {f}" for f in relevant_files)
            parts.append(f"""
## Relevant Files
These files may be relevant to your task:
{files_list}""")

        parts.append("""
When you have completed the task, provide a clear summary of your findings or actions.""")

        return "\n".join(parts)
    
    def get_running_count(self) -> int:
        """Return the number of currently running subagents."""
        return len(self._running_tasks)
