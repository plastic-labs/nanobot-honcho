#!/usr/bin/env node
/**
 * Convos Bridge for nanobot-honcho
 *
 * Wraps `convos agent serve` CLI and forwards messages to nanobot.
 *
 * Usage:
 *   1. npm install -g @xmtp/convos-cli
 *   2. convos init --env production
 *   3. convos conversations join "<invite-url>" --profile-name "YourAgent"
 *   4. node index.js <conversation-id> [--profile-name "YourAgent"]
 */

import { spawn } from "child_process";
import { createInterface } from "readline";

// Configuration
const PYTHON_CALLBACK_URL =
  process.env.PYTHON_CALLBACK_URL || "http://localhost:18791/xmtp/inbound";
const CONVOS_ENV = process.env.CONVOS_ENV || "production";

// Parse args
const args = process.argv.slice(2);
if (args.length === 0) {
  console.error("Usage: node index.js <conversation-id> [--profile-name <name>]");
  console.error("");
  console.error("First, join a conversation:");
  console.error('  convos conversations join "<invite-url>" --profile-name "Agent" --env production');
  console.error("");
  console.error("Then run this bridge with the conversation ID from the join output.");
  process.exit(1);
}

const conversationId = args[0];
const profileNameIdx = args.indexOf("--profile-name");
const profileName = profileNameIdx >= 0 ? args[profileNameIdx + 1] : "Agent";

console.log(`Starting Convos bridge...`);
console.log(`  Conversation: ${conversationId}`);
console.log(`  Profile: ${profileName}`);
console.log(`  Environment: ${CONVOS_ENV}`);
console.log(`  Callback URL: ${PYTHON_CALLBACK_URL}`);

// Track sender addresses for Honcho peer mapping
// In Convos, we use the sender's display name or inboxId
const senderMap = new Map();

// Spawn convos agent serve
const convos = spawn("convos", [
  "agent", "serve",
  conversationId,
  "--profile-name", profileName,
  "--env", CONVOS_ENV,
], {
  stdio: ["pipe", "pipe", "inherit"], // stdin: pipe, stdout: pipe, stderr: inherit
});

// Read stdout line by line (ndjson)
const rl = createInterface({ input: convos.stdout });

rl.on("line", async (line) => {
  let event;
  try {
    event = JSON.parse(line);
  } catch (e) {
    console.error("Failed to parse event:", line);
    return;
  }

  console.log(`Event: ${event.type}`);

  if (event.type === "ready") {
    console.log(`Ready! Conversation ID: ${event.conversationId}`);
    if (event.inviteUrl) {
      console.log(`Invite URL: ${event.inviteUrl}`);
    }
  } else if (event.type === "message") {
    // Forward message to nanobot
    const senderInboxId = event.senderInboxId || event.sender || "unknown";
    const senderName = event.senderName || event.displayName || senderInboxId;
    const content = event.text || event.content || "";
    const messageId = event.id || event.messageId || "";

    // Skip empty messages or system events
    if (!content || content.trim() === "") return;

    // Use sender name as address for Honcho (Convos doesn't expose wallet addresses easily)
    // This means each display name gets its own Honcho peer
    const senderAddress = `convos:${senderName}`;

    console.log(`Message from ${senderName}: ${content.substring(0, 50)}...`);

    // Store message ID for potential reply context
    senderMap.set(senderAddress, { messageId, senderInboxId });

    // Forward to nanobot
    try {
      const response = await fetch(PYTHON_CALLBACK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_inbox_id: senderInboxId,
          sender_address: senderAddress,
          conversation_id: conversationId,
          content: content,
          timestamp: new Date().toISOString(),
          // Convos-specific metadata
          message_id: messageId,
          sender_name: senderName,
          // Bridge URL for routing responses
          bridge_url: `http://localhost:${BRIDGE_PORT}`,
        }),
      });

      if (!response.ok) {
        console.error(`Failed to forward message: ${response.status}`);
      }
    } catch (error) {
      console.error("Error forwarding message:", error);
    }
  } else if (event.type === "member_joined") {
    console.log(`Member joined: ${event.name || event.inboxId}`);
  } else if (event.type === "sent") {
    console.log(`Message sent: ${event.id || "ok"}`);
  } else if (event.type === "error") {
    console.error(`Convos error: ${event.message || event.error}`);
  }
});

// Set up HTTP server to receive outbound messages from nanobot
import { createServer } from "http";

const server = createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/send") {
    let body = "";
    for await (const chunk of req) body += chunk;

    try {
      const { message } = JSON.parse(body);

      if (!message) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Missing message" }));
        return;
      }

      // Send to Convos via stdin
      const cmd = JSON.stringify({ type: "send", text: message }) + "\n";
      convos.stdin.write(cmd);

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ success: true }));
    } catch (error) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: String(error) }));
    }
  } else if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({
      status: "ok",
      conversationId,
      profileName,
      env: CONVOS_ENV,
    }));
  } else {
    res.writeHead(404);
    res.end("Not found");
  }
});

const BRIDGE_PORT = parseInt(process.env.CONVOS_BRIDGE_PORT || "18793", 10);
server.listen(BRIDGE_PORT, "127.0.0.1", () => {
  console.log(`HTTP server listening on http://127.0.0.1:${BRIDGE_PORT}`);
  console.log(`  GET  /health - Check bridge status`);
  console.log(`  POST /send   - Send outbound message`);
});

// Handle process exit
convos.on("close", (code) => {
  console.log(`Convos CLI exited with code ${code}`);
  process.exit(code || 0);
});

process.on("SIGINT", () => {
  console.log("Shutting down...");
  convos.kill();
  server.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("Shutting down...");
  convos.kill();
  server.close();
  process.exit(0);
});
