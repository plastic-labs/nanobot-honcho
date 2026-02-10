---
name: honcho
description: Integrate Honcho long-term memory into an existing nanobot installation. Use when the user wants to add persistent user modeling, cross-session memory, or the Honcho SDK to their nanobot.
metadata: {"nanobot":{"emoji":"\ud83e\udde0","requires":{"env":["HONCHO_API_KEY"]}}}
---

# Honcho Integration Skill

Add [Honcho](https://honcho.dev) long-term memory to an existing nanobot instance. This creates a feature-flagged integration that is safe to merge with upstream nanobot.

## Prerequisites

- A working nanobot installation
- A Honcho API key from [app.honcho.dev](https://app.honcho.dev)
- `HONCHO_API_KEY` set in environment or `~/.nanobot/.env`

## What This Adds

- **Automatic user observation**: Honcho watches conversations and builds persistent user models
- **Semantic search**: Retrieve relevant context from past conversations
- **Dialectic reasoning**: Query what Honcho knows about a user via `peer.chat()`
- **Feature flag**: `honcho.enabled` in config (default `false` for upstream compat)
- **Zero side effects when disabled**: All imports are lazy, no crash without `honcho-ai`

## Integration Steps

Follow these steps in order. Each step is independent and testable.

### Step 1: Add `honcho-ai` as optional dependency

In `pyproject.toml`, add to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
honcho = ["honcho-ai>=2.0.1"]
```

Install with: `pip install -e ".[honcho]"` or `uv pip install honcho-ai`

### Step 2: Add HonchoConfig to the config schema

In `nanobot/config/schema.py`, add this model and a field on the root `Config` class:

```python
class HonchoConfig(BaseModel):
    """Honcho AI-native memory integration (optional feature flag)."""
    enabled: bool = False
    workspace_id: str = "nanobot"
    prefetch: bool = True
    context_tokens: int | None = None
    environment: str = "production"
```

Then add to the `Config` class:

```python
class Config(BaseSettings):
    # ... existing fields ...
    honcho: HonchoConfig = Field(default_factory=HonchoConfig)
```

### Step 3: Create the honcho package

Create `nanobot/honcho/__init__.py`:

```python
"""Honcho integration for AI-native memory.

This package is only active when honcho.enabled=true in config and
HONCHO_API_KEY is set. All honcho-ai imports are deferred to avoid
ImportError when the package is not installed.
"""
```

Create `nanobot/honcho/client.py` — the client singleton. Key patterns:
- Use `from __future__ import annotations` at the top
- Put `from honcho import Honcho` inside `if TYPE_CHECKING:` block
- Do the real import at runtime inside `get_honcho_client()` with a helpful `ImportError`

Refer to `{baseDir}/references/client.py` for the complete implementation.

Create `nanobot/honcho/session.py` — the session manager. Key patterns:
- Same lazy import pattern for `Honcho` and `SessionPeerConfig`
- `SessionPeerConfig` imported at runtime inside `_get_or_create_honcho_session()`
- User peer: `observe_me=True, observe_others=True`
- Assistant peer: `observe_me=False, observe_others=True`
- Session IDs sanitized to match `^[a-zA-Z0-9_-]+`

Refer to `{baseDir}/references/session.py` for the complete implementation.

### Step 4: Create the Honcho agent tools

Create `nanobot/agent/tools/honcho.py` — a tool the agent can call to query user context:

```python
class HonchoTool(BaseTool):
    name = "query_user_context"
    description = "Query what Honcho knows about the current user"
```

The tool should accept a `query` string and a `session_key`, then call `session_manager.get_user_context(session_key, query)`.

Refer to `{baseDir}/references/honcho_tool.py` for the complete implementation.

### Step 5: Wire into the agent loop

In `nanobot/agent/loop.py`, add `honcho_config` parameter to `AgentLoop.__init__()`:

```python
def __init__(self, ..., honcho_config: "HonchoConfig | None" = None):
    from nanobot.config.schema import HonchoConfig
    self.honcho_config = honcho_config
```

At the end of `_register_default_tools()`, add conditional registration:

```python
if self.honcho_config and self.honcho_config.enabled:
    import os
    if os.environ.get("HONCHO_API_KEY"):
        try:
            from nanobot.honcho.client import get_honcho_client, HonchoConfig as HClientConfig
            from nanobot.honcho.session import HonchoSessionManager
            from nanobot.agent.tools.honcho import HonchoTool

            client_config = HClientConfig(
                workspace_id=self.honcho_config.workspace_id,
                api_key=os.environ["HONCHO_API_KEY"],
                environment=self.honcho_config.environment,
            )
            get_honcho_client(client_config)
            session_mgr = HonchoSessionManager(
                context_tokens=self.honcho_config.context_tokens,
            )
            self._honcho_session_manager = session_mgr
            honcho_tool = HonchoTool(session_manager=session_mgr)
            self.tools.register(honcho_tool)
            logger.info("Honcho tools registered (query_user_context)")
        except ImportError:
            logger.warning("Honcho enabled but honcho-ai not installed")
        except Exception as e:
            logger.warning(f"Failed to initialize Honcho: {e}")
```

### Step 6: Pass config through CLI commands

In `nanobot/cli/commands.py`, pass `honcho_config=config.honcho` to every `AgentLoop()` instantiation (both `gateway` and `agent` commands).

### Step 7: Enable and test

```bash
# Set the API key
export HONCHO_API_KEY=your-key-here

# Enable in config
python -c "
import json
from pathlib import Path
p = Path.home() / '.nanobot' / 'config.json'
c = json.loads(p.read_text()) if p.exists() else {}
c.setdefault('honcho', {})['enabled'] = True
p.write_text(json.dumps(c, indent=2))
print('Honcho enabled')
"

# Test
nanobot agent -m "Hello, remember me?"
```

## Verification Checklist

After integration, verify:
- [ ] `python -c "from nanobot.config.schema import Config; c = Config(); print(c.honcho.enabled)"` prints `False`
- [ ] `python -c "import nanobot.honcho"` does not crash (even without `honcho-ai` installed)
- [ ] With `honcho-ai` installed and `HONCHO_API_KEY` set, agent logs show "Honcho tools registered"
- [ ] Without `HONCHO_API_KEY`, agent starts normally with no honcho errors

## SDK v2 Reference

The integration uses `honcho-ai>=2.0.1` (SDK v2). Key API surface:

| Method | Purpose |
|--------|---------|
| `honcho.peer(name)` | Get or create a peer (lazy, no API call) |
| `honcho.session(name)` | Get or create a session (lazy) |
| `session.add_peers([(peer, config)])` | Configure observation per session |
| `session.add_messages([peer.message(content)])` | Save messages |
| `session.context(summary, tokens)` | Fetch messages + user representation |
| `peer.chat(query, session)` | Dialectic reasoning about the user |
| `peer.conclusions.create(content, sessionId)` | Save explicit facts |

## Patterns to Follow

- **Lazy imports everywhere**: `from __future__ import annotations` + `TYPE_CHECKING` for type hints, runtime imports inside functions
- **Feature flag gating**: Always check `honcho_config.enabled` AND `HONCHO_API_KEY` before touching Honcho
- **Graceful degradation**: `ImportError` and generic `Exception` catches with logger warnings, never crash the agent
- **Sanitize IDs**: Honcho requires `^[a-zA-Z0-9_-]+` for peer/session IDs -- replace colons, dots, spaces with dashes
