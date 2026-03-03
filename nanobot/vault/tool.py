"""VaultReadTool: search the knowledge vault for relevant context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class VaultReadTool(Tool):
    """Search the knowledge vault for relevant notes."""

    def __init__(self, vault_path: Path):
        self._vault_path = vault_path

    @property
    def name(self) -> str:
        return "vault_read"

    @property
    def description(self) -> str:
        return (
            "Search the knowledge vault for notes relevant to the current context. "
            "The vault contains captured insights, decisions, positions, and knowledge. "
            "Use this when you need background context on a topic the user has "
            "thought about before."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "What you're looking for — a topic, concept, or question. "
                        "Examples: 'fundraising strategy', 'architecture decisions', "
                        "'agent identity'."
                    ),
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, **kwargs: Any) -> str:
        if not self._vault_path.is_dir():
            return "Vault directory not found. No notes available."

        md_files = list(self._vault_path.rglob("*.md"))
        if not md_files:
            return "Vault is empty — no notes found."

        query_lower = query.lower()
        terms = query_lower.split()

        scored: list[tuple[float, Path, str]] = []
        for path in md_files:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            title = path.stem.replace("-", " ").replace("_", " ").lower()
            full_text = f"{title}\n{content}".lower()

            score = 0.0
            if query_lower in full_text:
                score += 10.0
            for term in terms:
                if term in title:
                    score += 3.0
                if term in full_text:
                    score += 1.0

            if score > 0:
                scored.append((score, path, content))

        if not scored:
            return f"No vault notes matched '{query}'."

        scored.sort(key=lambda x: x[0], reverse=True)
        results = scored[:5]

        parts = []
        for _score, path, content in results:
            parts.append(f"## [[{path.stem}]]\n{content.strip()}")

        return "\n\n---\n\n".join(parts)
