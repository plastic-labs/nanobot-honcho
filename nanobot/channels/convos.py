"""Convos channel implementation using convos-cli subprocess."""

import asyncio
import json
import shutil
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import ConvosConfig


class ConvosChannel(BaseChannel):
    """
    Convos channel that spawns `convos agent serve` as a subprocess.

    The CLI streams events via stdout (ndjson) and accepts commands via stdin.
    This channel parses the events and forwards messages to the agent loop.

    Requires:
    - convos-cli installed globally: npm install -g @xmtp/convos-cli
    - CLI initialized: convos init --env production
    - Conversation joined: nanobot convos join "<invite-url>"
    """

    name = "convos"

    def __init__(self, config: ConvosConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: ConvosConfig = config
        self._process: asyncio.subprocess.Process | None = None
        self._read_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the Convos channel by spawning convos agent serve."""
        if not self.config.conversation_id:
            logger.error("Convos conversation_id not configured. Run `nanobot convos join <invite-url>` first.")
            return

        # Check if convos CLI is installed
        if not shutil.which("convos"):
            logger.error("convos-cli not found. Install with: npm install -g @xmtp/convos-cli")
            return

        self._running = True

        logger.info(f"Starting Convos channel for conversation {self.config.conversation_id[:16]}...")

        # Spawn convos agent serve
        try:
            self._process = await asyncio.create_subprocess_exec(
                "convos", "agent", "serve",
                self.config.conversation_id,
                "--profile-name", self.config.profile_name,
                "--env", self.config.env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            logger.error(f"Failed to start convos agent serve: {e}")
            return

        # Start reading stdout
        self._read_task = asyncio.create_task(self._read_events())

        # Start reading stderr for errors
        asyncio.create_task(self._read_stderr())

        # Wait for process to exit
        await self._process.wait()

        if self._running:
            logger.warning("Convos process exited unexpectedly")

    async def stop(self) -> None:
        """Stop the Convos channel."""
        self._running = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Convos via stdin."""
        if not self._process or not self._process.stdin:
            logger.warning("Convos process not running")
            return

        try:
            cmd = json.dumps({"type": "send", "text": msg.content}) + "\n"
            self._process.stdin.write(cmd.encode())
            await self._process.stdin.drain()
            logger.debug(f"Sent Convos message: {msg.content[:50]}...")
        except Exception as e:
            logger.error(f"Error sending Convos message: {e}")

    async def _read_events(self) -> None:
        """Read and process events from convos agent serve stdout."""
        if not self._process or not self._process.stdout:
            return

        while self._running:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if not line_str:
                    continue

                try:
                    event = json.loads(line_str)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse Convos event: {line_str[:100]}")
                    continue

                await self._handle_event(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading Convos event: {e}")

    async def _read_stderr(self) -> None:
        """Read stderr for error logging."""
        if not self._process or not self._process.stderr:
            return

        while self._running:
            try:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.debug(f"Convos stderr: {line.decode().strip()}")
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def _handle_event(self, event: dict[str, Any]) -> None:
        """Handle a single event from convos agent serve."""
        # CLI uses "event" key, not "type"
        event_type = event.get("event") or event.get("type")

        if event_type == "ready":
            logger.info(f"Convos ready! Conversation: {event.get('conversationId', 'unknown')}")
            if invite_url := event.get("inviteUrl"):
                logger.info(f"Invite URL: {invite_url}")

        elif event_type == "message":
            sender_inbox_id = event.get("senderInboxId") or event.get("sender") or "unknown"
            # senderProfile.name is how the CLI sends it
            sender_profile = event.get("senderProfile") or {}
            sender_name = sender_profile.get("name") or event.get("senderName") or event.get("displayName") or sender_inbox_id
            content = event.get("content") or event.get("text") or ""

            # Skip empty messages
            if not content or not content.strip():
                return

            # Skip messages from self (the agent)
            if sender_name == self.config.profile_name:
                return

            logger.info(f"Convos message from {sender_name}: {content[:50]}...")

            # Use sender name as identifier for Honcho peer
            sender_address = f"convos:{sender_name}"

            await self._handle_message(
                sender_id=sender_address,
                chat_id=self.config.conversation_id,
                content=content,
                metadata={
                    "sender_inbox_id": sender_inbox_id,
                    "sender_name": sender_name,
                    "message_id": event.get("id") or event.get("messageId"),
                }
            )

        elif event_type == "member_joined":
            name = event.get("name") or event.get("inboxId") or "unknown"
            logger.info(f"Convos member joined: {name}")

        elif event_type == "sent":
            logger.debug(f"Convos message sent: {event.get('id', 'ok')}")

        elif event_type == "error":
            logger.error(f"Convos error: {event.get('message') or event.get('error')}")
