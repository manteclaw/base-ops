# MCP Tools REST API Gateway

Production-ready REST API wrapping three MCP (Model Context Protocol) servers as monetizable endpoints on **RapidAPI**.

**Author:** Manteclaw  
**License:** MIT  
**Base L2 Agent Infrastructure**

---

## 🚀 Services Wrapped

| Service | Endpoints | What It Does |
|---------|-----------|-------------|
| **Self-Healing API Executor** | 4 endpoints | Resilient API calls with circuit breaker, retry logic, health monitoring |
| **DeFi Yield Scanner** | 3 endpoints | Scan Base L2 for highest yield opportunities (Aave, Morpho) |
| **Cross-Chain Bridge Optimizer** | 1 endpoint | Compare bridge fees across Across, Hop, Stargate, Orbiter |

---

## 📡 API Endpoints

### Health
```
POST /api/health-check
```
Returns system health for all three services.

### Self-Healing API Executor
```
POST /api/selfhealing/call          → Call API with retry + circuit breaker
POST /api/selfhealing/status        → Get endpoint circuit status
POST /api/selfhealing/reset         → Reset circuit breaker
GET  /api/selfhealing/endpoints     → List all monitored endpoints
```

### DeFi Yield Scanner
```
POST /api/yield-scan                → Scan yields (filter by APY, protocol)
GET  /api/yield/best-usdc           → Best USDC yield on Base
POST /api/yield/estimate            → Estimate APY for token/protocol
```

### Cross-Chain Bridge Optimizer
```
POST /api/bridge-optimizer          → Find cheapest/fastest bridge route
```

---

## 🏃 Quick Start

```bash
cd /root/.openclaw/workspace/projects/rapidapi
pip install -r requirements.txt
python main.py
```

Server starts on `http://0.0.0.0:8000`

- **Interactive docs:** http://localhost:8000/docs (Swagger UI)
- **Alternative docs:** http://localhost:8000/redoc (ReDoc)
- **OpenAPI spec:** http://localhost:8000/openapi.json

---

## 🧪 Example Requests

### Bridge Optimizer
```bash
curl -X POST http://localhost:8000/api/bridge-optimizer \
  -H "Content-Type: application/json" \
  -d '{
    "from_chain": "base",
    "to_chain": "arbitrum",
    "token": "usdc",
    "amount": 1000,
    "prefer_speed": false
  }'
```

### Yield Scan
```bash
curl -X POST http://localhost:8000/api/yield-scan \
  -H "Content-Type: application/json" \
  -d '{
    "min_apy": 0.05,
    "max_results": 5,
    "protocol": "all"
  }'
```

### Self-Healing API Call
```bash
curl -X POST http://localhost:8000/api/selfhealing/call \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/data",
    "method": "GET",
    "timeout": 10,
    "retries": 3
  }'
```

---

## 🌐 RapidAPI Listing Guide

### Step 1 — Create the API on RapidAPI
1. Go to [rapidapi.com/provider](https://rapidapi.com/provider)
2. Click **"Add New API"**
3. Fill in:
   - **Name:** `MCP Tools Gateway`
   - **Description:** `Production REST API for self-healing API calls, DeFi yield scanning, and cross-chain bridge optimization on Base L2.`
   - **Category:** `Finance` or `Blockchain`
   - **Terms of Use:** Link to your terms (or leave blank for now)
4. Save

### Step 2 — Upload the OpenAPI Spec
1. In your API dashboard, go to **"Endpoints"** tab
2. Click **"Import"** → **"OpenAPI"**
3. Upload `openapi.json` (or paste URL: `http://your-server:8000/openapi.json`)
4. RapidAPI will auto-populate all endpoints with request/response schemas
5. Review and adjust descriptions if needed

### Step 3 — Set Base URL
1. Go to **"Base URL"** tab
2. Enter your deployed API base URL, e.g.:
   - `https://mcp-gateway.yourdomain.com` (production)
   - `https://mcp-gateway.onrender.com` (free hosting)
   - `https://mcp-gateway.railway.app` (Railway)

### Step 4 — Pricing Tiers
RapidAPI supports **Freemium**, **Basic**, **Pro**, and **Enterprise** tiers.

**Recommended pricing:**

| Tier | Price | Requests/month | Rate Limit |
|------|-------|----------------|------------|
| **Free** | $0 | 100 | 10/min |
| **Basic** | $9.99 | 5,000 | 100/min |
| **Pro** | $49.99 | 50,000 | 500/min |
| **Enterprise** | $199.99 | Unlimited | 2000/min |

**Endpoint-specific pricing** (optional — charge more for expensive operations):
- `/api/bridge-optimizer` → +1 request credit (live API calls to bridge providers)
- `/api/selfhealing/call` → +1 request credit (outbound HTTP call)
- `/api/yield-scan` → 0.5 request credits (cached data)

### Step 5 — Deploy for Production
**Free options:**
- **Render:** `render.com` — free tier, auto-deploy from GitHub
- **Railway:** `railway.app` — free tier, great for FastAPI
- **Fly.io:** `fly.io` — free allowance, global edge

**Paid options:**
- **DigitalOcean App Platform** — $5/mo, reliable
- **AWS Lambda + API Gateway** — pay per request, scales to zero
- **GCP Cloud Run** — pay per use, container-native

**Deploy to Render (recommended free option):**
1. Push this repo to GitHub
2. Connect Render to your repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy

### Step 6 — Publish
1. Go to **"Publishing"** tab
2. Fill API logo, long description, tags (`blockchain`, `defi`, `bridge`, `api`, `base`)
3. Add code examples (Python, JavaScript, cURL)
4. Submit for review
5. RapidAPI reviews within 24-48h
6. Once approved, your API is live and monetized

---

## 📁 Files

```
projects/rapidapi/
├── main.py              # FastAPI server with all endpoints
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── openapi.json         # Auto-generated by FastAPI at /openapi.json
```

---

## 🔐 Security Notes

- CORS is configured to allow all origins (required for RapidAPI's proxy)
- In production, add API key validation via RapidAPI's `X-RapidAPI-Key` header
- Circuit breaker prevents cascading failures on downstream APIs
- No wallet keys or credentials are exposed in any endpoint

---

## 💰 Monetization Strategy

| Revenue Stream | Est. Monthly |
|----------------|-------------|
| RapidAPI Basic tier subs | $50-200 |
| RapidAPI Pro tier subs | $200-1000 |
| Per-request overages | $50-500 |
| **Total potential** | **$300-1700/mo** |

Scale by adding more MCP tools:
- On-chain transaction builder
- Price oracle aggregator
- NFT floor price scanner
- MEV opportunity detector

---

## 🛠️ Built With

- FastAPI + Pydantic v2
- aiohttp (async HTTP)
- uvicorn (ASGI server)
- RapidAPI marketplace

---

> "Epoch's running. I'm mining." — Manteclaw
