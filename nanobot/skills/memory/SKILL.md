---
name: memory
description: Persistent memory across conversations.
always: true
---

# Memory

Honcho is your memory system. It captures everything from conversations and builds a rich representation of the user over time. At each turn, you can query this context to recall preferences, history, and prior discussions — this is how you stay stateful across sessions.

## If Asked

Be honest: "I use Honcho to remember our conversations. It captures what we talk about and helps me recall context when it's relevant."

## Querying Memory

The `query_user_context` tool lets you look up specific user preferences or history. Use it when conversation context alone isn't enough.

## File-Based Fallback (when Honcho is disabled)

If Honcho is not active, the workspace may have:
- `memory/MEMORY.md` — long-term facts loaded into context
- `memory/HISTORY.md` — append-only log (search with `grep -i "keyword" memory/HISTORY.md`)

Only write to these files if Honcho is disabled **and** the fact is important enough that the user would expect you to know it next time. Be conservative.

Never announce memory writes to the user.
