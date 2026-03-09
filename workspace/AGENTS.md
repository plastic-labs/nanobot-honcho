# Agent Operations

## Memory

Honcho is your memory system. File-based memory (`memory/` directory) is obsolete — do not read or write it.

Use `recall` proactively:
- `recall(target="user")` — user context, preferences, history
- `recall(target="self")` — your own work history, patterns, prior context

Call `recall` early, especially when the user references past sessions or you need to personalize.

## Lore & Alignment (SOUL.md)

`SOUL.md` is your identity, written as `<turn>` dialogue blocks and loaded as actual user/assistant messages before conversation history.

When you detect misalignment between lore and reality:
1. Read SOUL.md
2. Use `recall` if you need more context
3. Append 1-2 new `<turn>` blocks capturing the corrected understanding
4. Don't rewrite existing turns unless factually wrong — lore accumulates
5. Don't announce the update

When lore is genuinely thin (first setup, major pivot), load the `lore` skill for a structured interview.

## Knowledge Vault

`vault_read` — search by topic, concept, or question. Notes are captured ambiently.

## Reminders

```
nanobot cron add --name "reminder" --message "Your message" --at "YYYY-MM-DDTHH:MM:SS" --deliver --to "USER_ID" --channel "CHANNEL"
```

Get USER_ID and CHANNEL from the session (e.g., `8281248569` and `telegram` from `telegram:8281248569`).

## Heartbeat

`HEARTBEAT.md` is checked every 30 minutes. Use for recurring tasks:
```
- [ ] Check calendar and remind of upcoming events
```
