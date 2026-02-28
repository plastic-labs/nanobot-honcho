"""XMTP channel implementation using Node.js bridge."""

import asyncio
from typing import Any

import aiohttp
from aiohttp import web
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import XmtpConfig


class XmtpChannel(BaseChannel):
    """
    XMTP channel that connects to a Node.js bridge.

    The bridge uses @xmtp/agent-sdk to handle the XMTP protocol.
    Communication between Python and Node.js is via HTTP:
    - Bridge POSTs inbound messages to Python callback server
    - Python POSTs outbound messages to bridge /send endpoint

    Honcho peer mapping uses wallet address (not conversation ID) so the
    same wallet across different XMTP conversations is recognized as the
    same user with shared context.
    """

    name = "xmtp"

    def __init__(self, config: XmtpConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: XmtpConfig = config
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._http_session: aiohttp.ClientSession | None = None
        self._agent_address: str | None = None
        # Map wallet address -> (conversation_id, bridge_url) for reply routing
        self._conversation_map: dict[str, tuple[str, str]] = {}

    async def start(self) -> None:
        """Start the XMTP channel by starting HTTP server and verifying bridge."""
        self._running = True

        # Create HTTP client session
        self._http_session = aiohttp.ClientSession()

        # Set up HTTP server for inbound messages
        self._app = web.Application()
        self._app.router.add_post("/xmtp/inbound", self._handle_inbound)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(
            self._runner,
            "127.0.0.1",
            self.config.callback_port
        )
        await self._site.start()

        logger.info(f"XMTP callback server listening on http://127.0.0.1:{self.config.callback_port}/xmtp/inbound")

        # Verify bridge health and get agent address
        await self._check_bridge_health()

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the XMTP channel."""
        self._running = False

        if self._site:
            await self._site.stop()
            self._site = None

        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        self._app = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through XMTP via the bridge."""
        if not self._http_session:
            logger.warning("XMTP channel not started")
            return

        # chat_id is the wallet address; look up conversation_id and bridge_url from map
        route_info = self._conversation_map.get(msg.chat_id)

        if not route_info:
            logger.warning(f"No conversation ID found for wallet {msg.chat_id}")
            return

        conversation_id, bridge_url = route_info

        try:
            url = f"{bridge_url}/send"
            payload = {
                "conversationId": conversation_id,
                "message": msg.content
            }

            async with self._http_session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"Failed to send XMTP message: {resp.status} {body}")
                else:
                    logger.debug(f"Sent XMTP message to {msg.chat_id}")

        except Exception as e:
            logger.error(f"Error sending XMTP message: {e}")

    async def _check_bridge_health(self) -> None:
        """Check bridge health and log agent address."""
        if not self._http_session:
            return

        try:
            url = f"{self.config.bridge_url}/health"
            async with self._http_session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._agent_address = data.get("address")
                    status = data.get("status")
                    env = data.get("env")

                    if self._agent_address:
                        logger.info(f"XMTP bridge connected - Agent address: {self._agent_address}")
                        logger.info(f"  Environment: {env}")
                        logger.info(f"  Users can message your agent at {self._agent_address}")
                        logger.info(f"  Test at: https://xmtp.chat")
                    else:
                        logger.warning(f"XMTP bridge status: {status} (agent not ready)")
                else:
                    logger.warning(f"XMTP bridge health check failed: {resp.status}")

        except aiohttp.ClientError as e:
            logger.warning(f"Could not connect to XMTP bridge at {self.config.bridge_url}: {e}")
            logger.warning("Make sure the bridge is running: cd bridge-xmtp && npm start")

    async def _handle_inbound(self, request: web.Request) -> web.Response:
        """Handle inbound message from bridge."""
        try:
            data = await request.json()
        except Exception as e:
            logger.warning(f"Invalid JSON in XMTP inbound: {e}")
            return web.json_response({"error": "Invalid JSON"}, status=400)

        sender_inbox_id = data.get("sender_inbox_id", "")
        sender_address = data.get("sender_address", "")
        conversation_id = data.get("conversation_id", "")
        content = data.get("content", "")
        timestamp = data.get("timestamp", "")
        # Bridge URL for routing responses (Convos uses different port than XMTP)
        bridge_url = data.get("bridge_url", self.config.bridge_url)

        if not sender_address or not conversation_id or not content:
            logger.warning(f"Missing fields in XMTP inbound: {data}")
            return web.json_response({"error": "Missing required fields"}, status=400)

        logger.info(f"XMTP message from {sender_address}: {content[:50]}...")

        # Store conversation_id and bridge_url for reply routing
        # Use wallet address as the key
        self._conversation_map[sender_address] = (conversation_id, bridge_url)

        # Use wallet address as both sender_id and chat_id
        # This enables Honcho to recognize the same wallet across conversations
        await self._handle_message(
            sender_id=sender_address,
            chat_id=sender_address,  # Wallet-based, not conversation-based
            content=content,
            metadata={
                "conversation_id": conversation_id,
                "sender_inbox_id": sender_inbox_id,
                "timestamp": timestamp,
            }
        )

        return web.json_response({"status": "ok"})
