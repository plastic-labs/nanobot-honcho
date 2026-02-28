/**
 * XMTP Bridge for nanobot-honcho
 *
 * This bridge:
 * - Connects to the XMTP network using @xmtp/agent-sdk
 * - Listens for incoming text messages
 * - Forwards inbound messages to Python channel via HTTP POST
 * - Exposes HTTP endpoints for outbound messages and health checks
 */

import "dotenv/config";
import { Agent, getTestUrl } from "@xmtp/agent-sdk";
import type { Conversation } from "@xmtp/node-sdk";
import express, { Request, Response } from "express";
import { createServer } from "http";
import path from "path";
import { fileURLToPath } from "url";

// Environment configuration
const BRIDGE_PORT = parseInt(process.env.XMTP_BRIDGE_PORT || "18792", 10);
const PYTHON_CALLBACK_URL =
  process.env.PYTHON_CALLBACK_URL || "http://localhost:18791/xmtp/inbound";
const XMTP_ENV = (process.env.XMTP_ENV || "dev") as "dev" | "production";

// Get directory for database persistence
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DB_PATH = path.join(__dirname, "..", "data");

// Store conversation references for sending replies
const conversationCache = new Map<string, Conversation>();

let agent: Agent | null = null;

/**
 * Forward inbound message to Python channel
 */
async function forwardToPython(data: {
  sender_inbox_id: string;
  sender_address: string;
  conversation_id: string;
  content: string;
  timestamp: string;
}): Promise<void> {
  try {
    const response = await fetch(PYTHON_CALLBACK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      console.error(
        `Failed to forward message to Python: ${response.status} ${response.statusText}`
      );
    }
  } catch (error) {
    console.error("Error forwarding message to Python:", error);
  }
}

/**
 * Initialize and start the XMTP agent
 */
async function startAgent(): Promise<void> {
  console.log(`Starting XMTP bridge...`);
  console.log(`Environment: ${XMTP_ENV}`);
  console.log(`Database path: ${DB_PATH}`);

  // Create agent from environment variables
  // Requires: XMTP_WALLET_KEY, XMTP_DB_ENCRYPTION_KEY
  agent = await Agent.createFromEnv({
    env: XMTP_ENV,
  });

  console.log(`Agent address: ${agent.address}`);
  console.log(`Test URL: ${getTestUrl(agent.client)}`);

  // Handle incoming text messages
  agent.on("text", async (ctx) => {
    const senderInboxId = ctx.message.senderInboxId;
    const conversationId = ctx.conversation.id;
    const content = ctx.message.content as string;
    const timestamp = new Date().toISOString();

    console.log(`Received message from ${senderInboxId}: ${content}`);

    // Cache conversation for reply
    conversationCache.set(conversationId, ctx.conversation);

    // Resolve sender wallet address using getSenderAddress()
    let senderAddress: string | undefined;
    try {
      senderAddress = await ctx.getSenderAddress();
    } catch (error) {
      console.error(`Failed to get sender address: ${error}`);
    }

    if (!senderAddress) {
      console.warn(
        `Could not resolve wallet address for inbox ${senderInboxId}, using inbox ID as fallback`
      );
    }

    // Forward to Python
    await forwardToPython({
      sender_inbox_id: senderInboxId,
      sender_address: senderAddress || senderInboxId,
      conversation_id: conversationId,
      content,
      timestamp,
      bridge_url: `http://localhost:${BRIDGE_PORT}`,
    });
  });

  // Handle new DM conversations
  agent.on("dm", async (ctx) => {
    console.log(`New DM conversation: ${ctx.conversation.id}`);
    conversationCache.set(ctx.conversation.id, ctx.conversation);
  });

  // Log when agent starts
  agent.on("start", () => {
    console.log(`XMTP agent is running`);
    console.log(`Address: ${agent!.address}`);
    console.log(
      `Users can message your agent at this address using Convos, Base App, or xmtp.chat`
    );
  });

  // Start the agent
  await agent.start();
}

/**
 * Set up HTTP server for outbound messages and health checks
 */
function setupHttpServer(): void {
  const app = express();
  app.use(express.json());

  // Health check endpoint
  app.get("/health", (_req: Request, res: Response) => {
    res.json({
      status: agent ? "ok" : "starting",
      address: agent?.address || null,
      env: XMTP_ENV,
    });
  });

  // Send message endpoint
  app.post("/send", async (req: Request, res: Response) => {
    const { conversationId, message } = req.body;

    if (!conversationId || !message) {
      res.status(400).json({ error: "Missing conversationId or message" });
      return;
    }

    if (!agent) {
      res.status(503).json({ error: "Agent not ready" });
      return;
    }

    try {
      // Try to get conversation from cache
      let conversation = conversationCache.get(conversationId);

      if (!conversation) {
        // Try to fetch conversation by ID using getConversationContext
        const ctx = await agent.getConversationContext(conversationId);
        if (ctx) {
          conversation = ctx.conversation;
          conversationCache.set(conversationId, conversation);
        }
      }

      if (!conversation) {
        res.status(404).json({ error: "Conversation not found" });
        return;
      }

      // Send the message as text
      await conversation.sendText(message);

      console.log(`Sent message to ${conversationId}: ${message}`);
      res.json({ success: true, conversationId });
    } catch (error) {
      console.error("Error sending message:", error);
      res.status(500).json({ error: String(error) });
    }
  });

  const server = createServer(app);

  server.listen(BRIDGE_PORT, "127.0.0.1", () => {
    console.log(`HTTP server listening on http://127.0.0.1:${BRIDGE_PORT}`);
    console.log(`  GET  /health - Check bridge status`);
    console.log(`  POST /send   - Send outbound message`);
  });
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  // Start HTTP server first
  setupHttpServer();

  // Then start XMTP agent
  try {
    await startAgent();
  } catch (error) {
    console.error("Failed to start XMTP agent:", error);
    process.exit(1);
  }
}

// Handle shutdown
process.on("SIGINT", () => {
  console.log("Shutting down...");
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("Shutting down...");
  process.exit(0);
});

// Start
main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
