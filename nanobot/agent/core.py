"""Core agent loop logic shared between main agent and subagents."""

import json
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from nanobot.agent.context import format_tool_calls
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.budget import SpendBudget
from nanobot.providers.base import LLMProvider


def register_standard_tools(
    registry: ToolRegistry,
    workspace: Path,
    *,
    allowed_dir: Path | None = None,
    include_edit: bool = True,
    brave_api_key: str | None = None,
    exec_timeout: int = 30,
    restrict_to_workspace: bool = False,
) -> None:
    """Register standard file, web, and exec tools."""
    registry.register(ReadFileTool(allowed_dir=allowed_dir))
    registry.register(WriteFileTool(allowed_dir=allowed_dir))
    if include_edit:
        registry.register(EditFileTool(allowed_dir=allowed_dir))
    registry.register(ListDirTool(allowed_dir=allowed_dir))
    registry.register(ExecTool(
        working_dir=str(workspace),
        timeout=exec_timeout,
        restrict_to_workspace=restrict_to_workspace,
    ))
    registry.register(WebSearchTool(api_key=brave_api_key))
    registry.register(WebFetchTool())


async def run_loop(
    messages: list[dict[str, Any]],
    tools: ToolRegistry,
    provider: LLMProvider,
    model: str,
    *,
    max_iterations: int = 20,
    budget: SpendBudget | None = None,
    cost_source: str = "agent",
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> tuple[str | None, bool]:
    """
    Execute the core agent iteration loop.

    Args:
        messages: Initial messages list (modified in place).
        tools: Tool registry with available tools.
        provider: LLM provider for chat completions.
        model: Model identifier to use.
        max_iterations: Maximum number of iterations.
        budget: Optional spend budget to track costs.
        cost_source: Label for cost tracking.
        on_tool_call: Optional callback when a tool is called.

    Returns:
        Tuple of (final_content, budget_exhausted).
    """
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Check budget before LLM call
        if budget and budget.is_exhausted:
            return None, True

        # Call LLM
        response = await provider.chat(
            messages=messages,
            tools=tools.get_definitions(),
            model=model,
        )

        # Track spend
        if budget:
            budget.add_cost(
                cost=response.cost,
                input_tokens=response.usage.get("prompt_tokens", 0) if response.usage else 0,
                output_tokens=response.usage.get("completion_tokens", 0) if response.usage else 0,
                source=cost_source,
            )
            logger.debug(f"Budget [{cost_source}]: {budget.get_summary()}")

        # Handle tool calls
        if response.has_tool_calls:
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": format_tool_calls(response.tool_calls),
            })

            # Execute tools
            for tool_call in response.tool_calls:
                args_str = json.dumps(tool_call.arguments)
                logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                if on_tool_call:
                    on_tool_call(tool_call.name, tool_call.arguments)
                result = await tools.execute(tool_call.name, tool_call.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "content": result,
                })
        else:
            # No tool calls, we're done
            return response.content, False

    # Max iterations reached
    return None, False
