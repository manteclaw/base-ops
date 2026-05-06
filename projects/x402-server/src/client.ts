import { wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm/exact/client";
import { toClientEvmSigner } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { createPublicClient, http } from "viem";
import { base } from "viem/chains";
import dotenv from "dotenv";

dotenv.config();

/**
 * x402 Paid API Client Example
 *
 * This script demonstrates how to call an x402-monetized endpoint.
 * It wraps the native fetch with automatic payment handling:
 *   1. Makes the request
 *   2. If 402 Payment Required, parses requirements
 *   3. Signs payment with EVM wallet
 *   4. Retries request with payment header
 *   5. Returns the paid response
 */

const SERVER_URL = process.env.SERVER_URL ?? "http://localhost:4021";
const PRIVATE_KEY = process.env.CLIENT_PRIVATE_KEY as `0x${string}`;

if (!PRIVATE_KEY || !PRIVATE_KEY.startsWith("0x")) {
  console.error("❌ Set CLIENT_PRIVATE_KEY in .env (0x-prefixed hex private key)");
  process.exit(1);
}

// ── EVM Wallet Setup ──
const account = privateKeyToAccount(PRIVATE_KEY);
const publicClient = createPublicClient({
  chain: base,
  transport: http(),
});

const signer = toClientEvmSigner(account, publicClient);

// ── x402 Client ──
const client = new x402Client().register(
  "eip155:8453", // Base mainnet
  new ExactEvmScheme(signer)
);

const fetchWithPay = wrapFetchWithPayment(fetch, client);

// ── Call Paid Endpoint ──
async function main() {
  const topic = process.argv[2] ?? "Base L2 ecosystem trends";

  console.log(`🔍 Requesting research on: "${topic}"`);
  console.log(`💳 Wallet: ${account.address}`);
  console.log(`📡 Server: ${SERVER_URL}/api/research`);

  try {
    const res = await fetchWithPay(`${SERVER_URL}/api/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error(`❌ Server error ${res.status}: ${err}`);
      process.exit(1);
    }

    const data = await res.json();
    console.log("\n✅ Paid response received!\n");
    console.log("Topic:", data.topic);
    console.log("Price Paid:", data.pricePaid);
    console.log("Settled At:", data.settledAt);
    console.log("\n--- Summary ---\n");
    console.log(data.summary);
  } catch (err: any) {
    console.error("❌ Request failed:", err.message);
    process.exit(1);
  }
}

main();
