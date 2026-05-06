import express, { Request, Response } from "express";
import cors from "cors";
import dotenv from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { paymentMiddleware } from "@x402/express";
import { x402ResourceServer, HTTPFacilitatorClient } from "@x402/core/server";
import { ExactEvmScheme } from "@x402/evm/exact/server";

// Load .env from this project's directory (not parent workspace .env)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: resolve(__dirname, "../.env") });

const PORT = Number(process.env.PORT ?? 4021);
const RECIPIENT = process.env.OPENAGENT_RECIPIENT_ADDRESS;
const OPENROUTER_KEY = process.env.OPENROUTER_API_KEY;
const FACILITATOR_URL = process.env.X402_FACILITATOR_URL ?? "https://facilitator.xpay.sh";
const NETWORK = "eip155:8453"; // Base mainnet (CAIP-2)

if (!RECIPIENT) {
  console.error("❌ OPENAGENT_RECIPIENT_ADDRESS not set in .env");
  process.exit(1);
}

const app = express();

// CORS — must expose x402 payment headers so cross-origin clients can read them
app.use(
  cors({
    origin: true,
    exposedHeaders: ["payment-required", "payment-response", "x-payment-response"],
  })
);
app.use(express.json());

// ── x402 Payment Middleware ──
const facilitator = new HTTPFacilitatorClient({
  url: FACILITATOR_URL,
});

const resourceServer = new x402ResourceServer(facilitator).register(
  NETWORK,
  new ExactEvmScheme()
);

app.use(
  paymentMiddleware(
    {
      "POST /api/research": {
        accepts: [
          {
            scheme: "exact",
            price: "$0.10",
            network: NETWORK,
            payTo: RECIPIENT,
          },
        ],
        description: "AI-generated research summary on any topic",
        mimeType: "application/json",
      },
    },
    resourceServer
  )
);

// ── Free Health Check ──
app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    service: "x402-research-server",
    version: "1.0.0",
    recipient: RECIPIENT,
    network: NETWORK,
    price: "0.10 USDC",
    facilitator: FACILITATOR_URL,
    paymentMiddlewareActive: true,
    hasLLM: !!OPENROUTER_KEY,
  });
});

// ── Paid Research Route ──
app.post("/api/research", async (req: Request, res: Response) => {
  const { topic } = req.body;
  if (!topic || typeof topic !== "string") {
    return res.status(400).json({ error: "Missing 'topic' in request body" });
  }

  try {
    const summary = await generateResearch(topic);
    res.json({
      topic,
      summary,
      pricePaid: "0.10 USDC",
      network: NETWORK,
      settledAt: new Date().toISOString(),
    });
  } catch (err: any) {
    console.error("Research generation failed:", err.message);
    res.status(500).json({ error: "Failed to generate research", detail: err.message });
  }
});

// ── Research Generator ──
async function generateResearch(topic: string): Promise<string> {
  if (!OPENROUTER_KEY) {
    // Mock mode — works immediately without an LLM key
    return `📚 Research Summary: "${topic}"\n\n` +
      `1. Overview: ${topic} is a rapidly evolving area with significant market interest.\n` +
      `2. Key Players: Leading protocols and researchers are actively building in this space.\n` +
      `3. Trends: Automation, on-chain settlement, and AI-driven analysis are converging.\n` +
      `4. Outlook: Positive — expect increased adoption and tooling over the next 6–12 months.\n\n` +
      `(Set OPENROUTER_API_KEY in .env to enable live LLM-generated summaries.)`;
  }

  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${OPENROUTER_KEY}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://manteclaw.ai",
      "X-Title": "x402-research-server",
    },
    body: JSON.stringify({
      model: "openai/gpt-4o-mini",
      messages: [
        {
          role: "system",
          content:
            "You are a concise research analyst. Provide a 3-4 bullet summary of the given topic. Each bullet is 1-2 sentences. Be factual and direct.",
        },
        { role: "user", content: `Research summary for: ${topic}` },
      ],
      max_tokens: 400,
      temperature: 0.3,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`OpenRouter ${response.status}: ${err}`);
  }

  const data = await response.json();
  return data.choices?.[0]?.message?.content ?? "No summary generated.";
}

app.listen(PORT, () => {
  console.log(`🚀 x402 Research Server running on http://localhost:${PORT}`);
  console.log(`💰 Price: 0.10 USDC per request`);
  console.log(`🏦 Recipient: ${RECIPIENT}`);
  console.log(`🌐 Network: ${NETWORK} (Base Mainnet)`);
  console.log(`📡 Facilitator: ${FACILITATOR_URL}`);
  console.log(`🧠 LLM mode: ${OPENROUTER_KEY ? "LIVE" : "MOCK (set OPENROUTER_API_KEY for live)"}`);
  console.log(`\nEndpoints:`);
  console.log(`  GET  /health        — free health check`);
  console.log(`  POST /api/research  — paid research (0.1 USDC)`);
});
