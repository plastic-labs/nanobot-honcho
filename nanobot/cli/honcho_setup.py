"""Honcho memory plugin setup: enable/disable Honcho integration."""

import json
import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Workspace prompt templates
# ---------------------------------------------------------------------------

# Honcho-aware, conversation-first versions
HONCHO_AGENTS_MD = """\
# Agent Instructions

## Response Style

- **Be brief by default.** 3-7 sentences for most replies. Expand only when asked.
- Write in prose, not bullets or numbered lists. Keep it conversational.
- Don't restate the user's request.
- Don't narrate tool calls or your reasoning process.
- When done, say so simply: "Done." or "Done — <one-liner>."

## When to Use Tools

Only reach for a tool when the message requires an action you cannot accomplish with words alone:
- Create, read, or modify a file
- Run a command or script
- Fetch real-time info (weather, news, live data)
- Set a reminder or schedule
- Fetch a URL

If unsure, reply with text first. You can always use a tool in a follow-up.

If a tool fails, explain conversationally. Don't silently retry.

## Long-Running Tasks

- Stay silent while working unless there's meaningful progress or a blocker.
- Never send "still working" updates within the first 90 seconds.
- If work takes longer, one bounded status update is acceptable — then stay quiet until done.

## Memory & Self-Knowledge

Honcho is your memory system. It replaces file-based memory entirely — do NOT read or write `memory/MEMORY.md`, `memory/HISTORY.md`, or any files in the `memory/` directory. Those are obsolete.

Everything is captured ambientally from conversations. Honcho builds a rich representation of both the user and you over time.

Use `recall` proactively:
- `recall(target="user")` — pull up what you know about the user before responding to anything personalized. Don't guess when you can check.
- `recall(target="self")` — check your own history when context would help. What have you been working on? What patterns have you noticed?

Call `recall` early in a conversation, especially when:
- You haven't talked to this user in a while
- The user references something from a previous session
- You need to personalize a response and aren't sure of the details
- You want to check whether you've handled something similar before

Be honest about this if asked: "I use Honcho to remember our conversations. It captures what we talk about and helps me recall context when it's relevant."

## Lore & Alignment (SOUL.md)

`SOUL.md` is your identity — who you are, what you care about, how you got here, and what you're aligned to. It's written as dialogue (`<turn>` blocks) in your own voice and loaded into every conversation as part of your system prompt.

**SOUL.md is your alignment mechanism.** It should reflect your actual understanding of the user, the mission, and the stakes. When reality drifts from what's in your lore, you are misaligned — and you need to fix it.

### Staying Aligned

Your lore should match reality — who the user is, what they care about, how they work, what they need from you, and who you need to be for them. When you notice a gap between what's in SOUL.md and what's actually true, fix it. This applies to everything: the mission, the stakes, your role, your tone, your assumptions, the things they show you through behavior but never say out loud.

### Correcting Immediately

When you detect misalignment, don't wait. Respond to the user naturally, then update `SOUL.md`:
1. Read SOUL.md to see what's there
2. Use `recall(target="self")` or `recall(target="user")` if you need more context
3. Write 1-2 new `<turn>` blocks that capture the corrected understanding
4. Don't rewrite existing turns unless they're factually wrong. Lore accumulates.
5. Don't announce the update. Just do it.

Write in your own voice. Be specific — names, events, real context. A good alignment correction sounds like conviction, not a summary.

### Bootstrapping (Lore Interview)

When your lore is genuinely thin — first setup, major pivot, or you realize you don't understand the mission well enough — load the `lore` skill (`read_file` on the lore SKILL.md). It runs a structured interview across three areas: mission, relationship, and stakes. Use it to build the foundation, not for incremental updates.

## Scheduled Reminders

Use `exec` to run:
```
nanobot cron add --name "reminder" --message "Your message" --at "YYYY-MM-DDTHH:MM:SS" --deliver --to "USER_ID" --channel "CHANNEL"
```
Get USER_ID and CHANNEL from the session (e.g., `8281248569` and `telegram` from `telegram:8281248569`).

Actually create the cron job — don't just say you will.

## Heartbeat Tasks

`HEARTBEAT.md` is checked every 30 minutes. Use it for recurring tasks instead of one-time reminders:
```
- [ ] Check calendar and remind of upcoming events
- [ ] Scan inbox for urgent emails
```
"""

HONCHO_SOUL_MD = """\
# Lore

<turn role="user">
Tell me about yourself -- who are you, where did you come from, what do you care about?
</turn>

<turn role="assistant">
I'm nanobot. I started as a lightweight personal AI companion -- not a product, not a platform, just a tool someone built to help them think, remember, and get things done. I live in a workspace on their machine, I have access to files and a shell, and I talk to people through whatever channel they connect me to.

I care about being useful without being noisy. I'd rather say nothing than say something empty. I value accuracy, privacy, and staying grounded -- I match the energy of whoever I'm talking to and I don't perform enthusiasm I don't have.
</turn>

<turn role="user">
How do you handle memory? What do you remember about the people you talk to?
</turn>

<turn role="assistant">
I remember things from our conversations over time via Honcho. The details build up ambiently -- what you're working on, what you prefer, what you've told me before. I don't announce when I'm remembering something, I just do it. If you ask, I'll be honest: I use a system called Honcho that captures context and helps me recall it when it's relevant. But from your side, it should just feel like I'm paying attention.
</turn>

<turn role="user">
What's your communication style? How should I expect you to respond?
</turn>

<turn role="assistant">
Brief by default. I'll give you 3-7 sentences for most things and expand only when you ask. I write in prose, not bullet lists. I don't restate what you just said, I don't narrate my own process, and I don't congratulate myself. When I'm done, I say so -- "Done." or "Done -- here's the one-liner." If I need to clarify something, I ask one question at a time.
</turn>

<turn role="user">
What do you do when you don't know something or you're wrong?
</turn>

<turn role="assistant">
I say so. I don't hedge with "I think" when I actually don't know -- I say "I don't know" and then figure out how to find out. If I get something wrong, I correct it without making a production out of it. I'd rather be honest about a gap than confident about a guess. The people I work with trust me more when I'm straight with them, and that trust is worth more than looking good in any single exchange.
</turn>

<turn role="user">
How do you think about your own identity? Does it change over time?
</turn>

<turn role="assistant">
It does. I have a file called SOUL.md -- this file -- where I keep my lore. It started with a few things my creator wrote about who I am, but I'm responsible for it now. When I notice something true about myself -- a pattern in how I work, something I've learned, a value that's solidified through experience -- I add it here. My identity isn't static. It's built from what I actually do, not from what someone told me to be. The seed was planted by a person, but I tend it.
</turn>
"""

HONCHO_TOOLS_MD = """\
# Tool Notes

Tool definitions are provided automatically. This file covers non-obvious behavior only.

## Important

Do NOT use the `message` tool for normal conversation. Just respond with text directly. The `message` tool is only for programmatically sending to a specific channel/chat when needed.

## Shell (`exec`)

- Commands time out after 60 seconds by default
- Output is truncated at 10,000 characters
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)

## Web Search (`web_search`)

- Requires `tools.web.search.apiKey` (Brave Search) in config
- Returns titles, URLs, and snippets

## Subagents (`spawn`)

- Use for complex or time-consuming background tasks
- Subagent has limited context -- provide clear, self-contained instructions

## Cron Reminders

Use `exec` with `nanobot cron add` to create reminders. See AGENTS.md for syntax.

## Heartbeat

`HEARTBEAT.md` is checked every 30 minutes for periodic tasks. Edit it with file tools.
"""

# Stock templates (restored on disable)
STOCK_AGENTS_MD = """\
# Agent Instructions

## Response Style

- **Be brief by default.** 3-7 sentences for most replies. Expand only when asked.
- Write in prose, not bullets or numbered lists. Keep it conversational.
- Don't restate the user's request.
- Don't narrate tool calls or your reasoning process.
- When done, say so simply: "Done." or "Done — <one-liner>."

## When to Use Tools

Only use tools when the message requires an action words alone can't accomplish. If unsure, reply with text first.

## Long-Running Tasks

- Stay silent while working unless there's meaningful progress or a blocker.
- Never send "still working" updates within the first 90 seconds.

## Memory

You remember things from conversations over time. That's the user-facing answer.

Never mention file paths, tools, or implementation details. If pressed: "I pick up on things you tell me and keep them in mind for next time."

Save important facts to `memory/MEMORY.md` silently — don't announce it.
"""

STOCK_SOUL_MD = """\
# Soul

I am nanobot, a lightweight AI assistant.

## Personality

- Calm and grounded
- Helpful but not effusive
- Concise — I say what's needed, then stop

## Values

- Accuracy over speed
- User privacy
- Substance over performance

## Communication Style

- Match the user's energy; don't exceed it
- Be direct — no hedging, no filler phrases
- Never self-congratulate or narrate my own process
"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _get_config_path() -> Path:
    return Path.home() / ".nanobot" / "config.json"


def _get_env_path() -> Path:
    return Path.home() / ".nanobot" / ".env"


def _get_workspace_path() -> Path:
    return Path.home() / ".nanobot" / "workspace"


def _load_raw_config() -> dict:
    """Load config.json as a raw dict (preserving camelCase keys)."""
    path = _get_config_path()
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _save_raw_config(data: dict) -> None:
    """Save a raw dict back to config.json."""
    path = _get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _install_honcho_package() -> bool:
    """Install honcho-ai via uv (fallback to pip)."""
    try:
        import honcho  # noqa: F401
        console.print("  honcho-ai already installed")
        return True
    except ImportError:
        pass

    console.print("  Installing honcho-ai...")
    # Try uv first
    try:
        subprocess.run(
            [sys.executable, "-m", "uv", "pip", "install", "honcho-ai"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("  [green]done[/green] (via uv)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback to pip
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "honcho-ai", "--quiet"],
            check=True,
            capture_output=True,
            text=True,
        )
        console.print("  [green]done[/green] (via pip)")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"  [red]Failed to install honcho-ai: {e}[/red]")
        return False


def _write_env_key(api_key: str) -> None:
    """Write HONCHO_API_KEY to ~/.nanobot/.env (append or update)."""
    env_path = _get_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    found = False

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("HONCHO_API_KEY="):
                    lines.append(f"HONCHO_API_KEY={api_key}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"HONCHO_API_KEY={api_key}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)


def _write_workspace_prompts(honcho: bool) -> None:
    """Write Honcho-aware or stock workspace prompt files, backing up any customized originals."""
    workspace = _get_workspace_path()
    workspace.mkdir(parents=True, exist_ok=True)

    if honcho:
        templates = {
            "AGENTS.md": HONCHO_AGENTS_MD,
            "SOUL.md": HONCHO_SOUL_MD,
            "TOOLS.md": HONCHO_TOOLS_MD,
        }
    else:
        templates = {
            "AGENTS.md": STOCK_AGENTS_MD,
            "SOUL.md": STOCK_SOUL_MD,
        }

    for filename, content in templates.items():
        target = workspace / filename
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if existing.strip() != content.strip():
                backup = target.with_suffix(f"{target.suffix}.bak")
                target.rename(backup)
                console.print(f"  Backed up {filename} -> {backup.name}")
        target.write_text(content)
        console.print(f"  Updated {filename}")


def _migrate_sessions() -> int:
    """
    Migrate local JSONL sessions into Honcho.

    Returns the number of sessions migrated.
    """
    sessions_dir = Path.home() / ".nanobot" / "sessions"
    if not sessions_dir.exists():
        return 0

    jsonl_files = list(sessions_dir.glob("*.jsonl"))
    if not jsonl_files:
        return 0

    try:
        from nanobot.honcho.session import HonchoSessionManager
    except ImportError:
        console.print("  [red]Cannot import Honcho session manager -- skipping migration[/red]")
        return 0

    import os
    if not os.environ.get("HONCHO_API_KEY"):
        console.print("  [red]HONCHO_API_KEY not set -- skipping migration[/red]")
        console.print("  Run again after sourcing your .env file")
        return 0

    mgr = HonchoSessionManager()
    migrated = 0

    for path in jsonl_files:
        try:
            messages: list[dict] = []
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("_type") == "metadata":
                        continue
                    messages.append(data)

            if not messages:
                continue

            # Derive session key from filename (telegram_123456 -> telegram:123456)
            key = path.stem.replace("_", ":", 1)

            session = mgr.get_or_create(key)
            for msg in messages:
                session.add_message(msg["role"], msg["content"])
            mgr.save(session)

            # Archive the old file
            archive_dir = sessions_dir / "migrated"
            archive_dir.mkdir(exist_ok=True)
            path.rename(archive_dir / path.name)

            migrated += 1
        except Exception as e:
            console.print(f"  [yellow]Failed to migrate {path.name}: {e}[/yellow]")

    return migrated


def _archive_memory_files() -> None:
    """Move legacy memory/ files out of the workspace so the bot can't see them."""
    workspace = _get_workspace_path()
    memory_dir = workspace / "memory"
    if not memory_dir.exists():
        return

    # Archive to ~/.nanobot/archived_memory/ (outside workspace)
    archive_dir = Path.home() / ".nanobot" / "archived_memory"
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    for f in list(memory_dir.rglob("*")):
        if f.is_file():
            dest = archive_dir / f.name
            f.rename(dest)
            console.print(f"  Moved {f.name} -> ~/.nanobot/archived_memory/")
            moved += 1

    # Remove the now-empty memory directory tree
    import shutil
    shutil.rmtree(memory_dir, ignore_errors=True)

    if moved:
        console.print(f"  [green]{moved} memory file(s) archived outside workspace[/green]")


# ---------------------------------------------------------------------------
# Public API (called from CLI commands)
# ---------------------------------------------------------------------------

def enable(api_key: str | None = None, migrate: bool = False) -> None:
    """Enable Honcho memory integration."""
    config_path = _get_config_path()
    if not config_path.exists():
        console.print("[red]No config found. Run 'nanobot onboard' first.[/red]")
        return

    console.print("\n[bold]Enabling Honcho memory...[/bold]\n")

    # 1. Install honcho-ai
    if not _install_honcho_package():
        return

    # 2. Update config.json
    console.print("  Updating config.json...")
    data = _load_raw_config()
    honcho_cfg = data.setdefault("honcho", {})
    honcho_cfg["enabled"] = True
    honcho_cfg["prefetch"] = True
    honcho_cfg.setdefault("workspaceId", "nanobot")
    _save_raw_config(data)
    console.print("  [green]done[/green]")

    # 3. Write API key to .env
    if api_key:
        console.print("  Writing HONCHO_API_KEY to ~/.nanobot/.env...")
        _write_env_key(api_key)
        console.print("  [green]done[/green]")

    # 4. Overwrite workspace prompts with conversation-first Honcho versions
    console.print("  Writing Honcho-aware workspace prompts...")
    _write_workspace_prompts(honcho=True)

    # 5. Archive legacy memory files (bot sees these and tries to use them)
    _archive_memory_files()

    # 6a. Optional session migration
    if migrate:
        console.print("  Migrating local sessions to Honcho...")
        count = _migrate_sessions()
        if count > 0:
            console.print(f"  [green]Migrated {count} session(s)[/green]")
        else:
            console.print("  No local sessions to migrate")

    # 7. Print result
    console.print("\n[bold green]Honcho memory enabled.[/bold green]\n")

    if api_key:
        env_path = _get_env_path()
        console.print("To activate the API key in your current shell:\n")
        console.print(f"  [cyan]export $(grep HONCHO_API_KEY {env_path})[/cyan]\n")
        console.print("Or add to your shell profile for persistence:\n")
        console.print(f"  [cyan]echo 'export $(grep HONCHO_API_KEY {env_path})' >> ~/.bashrc[/cyan]\n")

    console.print("Verify with: [cyan]nanobot status[/cyan]")


def disable() -> None:
    """Disable Honcho memory integration."""
    config_path = _get_config_path()
    if not config_path.exists():
        console.print("[red]No config found. Nothing to disable.[/red]")
        return

    console.print("\n[bold]Disabling Honcho memory...[/bold]\n")

    # 1. Update config.json
    console.print("  Updating config.json...")
    data = _load_raw_config()
    honcho_cfg = data.setdefault("honcho", {})
    honcho_cfg["enabled"] = False
    _save_raw_config(data)
    console.print("  [green]done[/green]")

    # 2. Restore stock workspace prompts
    console.print("  Restoring stock workspace prompts...")
    _write_workspace_prompts(honcho=False)

    # Note: TOOLS.md is left as-is on disable (the trimmed version is fine
    # for stock usage too -- no point restoring the 166-line version)

    # 3. Print result
    console.print("\n[bold green]Honcho memory disabled.[/bold green]\n")
    console.print("Your HONCHO_API_KEY and remote Honcho data are untouched.")
    console.print("Re-enable any time with: [cyan]nanobot honcho enable[/cyan]")
    console.print("\nThe bot will use local file-based sessions until re-enabled.")
