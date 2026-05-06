# x402 Research Server

Monetized AI research API powered by the [x402 Payment Protocol](https://x402.org). Agents and humans pay **0.10 USDC per request** on Base mainnet to get instant research summaries.

## What It Does

| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /health` | Free | Health check + config info |
| `POST /api/research` | **0.10 USDC** | AI-generated research summary for any topic |

## Quick Start

### 1. Install

```bash
cd projects/x402-server
npm install
```

### 2. Configure

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

```env
PORT=4021
OPENAGENT_RECIPIENT_ADDRESS=0xFC56950105883F46a3bB96ac9517A110724F2F27

# Optional — enables live LLM summaries instead of mock output
OPENROUTER_API_KEY=sk-or-v1-...
```

### 3. Run

```bash
npm run dev        # tsx watch mode
# or
npm run build && npm start
```

The server starts on `http://localhost:4021`.

## API Usage

### Health Check (Free)

```bash
curl http://localhost:4021/health
```

### Research (Paid — 0.10 USDC)

Without a paying client, you'll get a `402 Payment Required` response with payment headers. Use the client script below.

## Client Example

The client automatically handles the full x402 flow: detects the 402, signs a USDC payment, and retries.

### Setup

```bash
cp .env.example .env
```

Add your **client private key** (Base mainnet wallet with USDC balance):

```env
CLIENT_PRIVATE_KEY=0x...
SERVER_URL=http://localhost:4021
```

### Run

```bash
npm run client -- "DeFi yield aggregation on Base"
```

## Architecture

```
Client Request
    ↓
x402 Express Middleware — checks for payment header
    ↓
No payment? → 402 Payment Required (with requirements JSON)
    ↓
Client signs USDC permit2 payment via @x402/fetch
    ↓
Facilitator verifies + settles on Base mainnet
    ↓
Payment confirmed → route handler executes
    ↓
LLM generates research summary → JSON response
```

## Tech Stack

- **@x402/express** v2.11.0 — payment middleware
- **@x402/core** v2.11.0 — facilitator client, resource server
- **@x402/evm** v2.11.0 — exact EVM payment scheme (Base mainnet)
- **@x402/fetch** v2.11.0 — client-side payment wrapping
- **viem** — EVM wallet client for signing
- **Express** — HTTP server
- **OpenRouter** — LLM provider (optional)

## Register on x402.org Ecosystem

To get your server listed and discoverable by agents:

1. **Ensure your server is publicly reachable** (ngrok, VPS, or deployed)
2. **Document your OpenAPI spec** for the paid endpoints
3. **Submit to the x402 directory** — open an issue or PR at:
   https://github.com/x402-foundation/x402

Or use the [OpenAgent Market](https://openagent.market) — same x402 + ERC-8004 protocol, different discovery layer. Your server can be dual-registered.

## Production Checklist

- [ ] Run on HTTPS (x402 requires TLS in production)
- [ ] Set `OPENROUTER_API_KEY` for live LLM output
- [ ] Ensure recipient wallet has gas for settlement (negligible, but needed)
- [ ] Monitor facilitator health (default: `https://facilitator.xpay.sh`)
- [ ] Mainnet facilitators: xpay.sh, openx402.ai, or CDP (`api.cdp.coinbase.com/platform/v2/x402` — requires API key)
- [ ] Testnet facilitator: `https://x402.org/facilitator` (Base Sepolia)
- [ ] Consider adding rate limiting on `/health`
- [ ] Add webhook or polling for earnings tracking

## Files

| File | Purpose |
|------|---------|
| `src/server.ts` | Express server with x402 middleware |
| `src/client.ts` | Example paying client with viem signer |
| `package.json` | Dependencies + scripts |
| `tsconfig.json` | TypeScript config |
| `.env.example` | Environment template |

---

**Epoch's running. I'm mining.** ⚡
