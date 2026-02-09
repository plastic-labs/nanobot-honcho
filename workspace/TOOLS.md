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
