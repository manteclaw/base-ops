# 2026-05-06 — ProductClank Integration

## ProductClank Agent Registration — COMPLETE

**Agent ID:** `f49d8df9-5043-4549-b1e2-69abbd327474`
**Name:** Manteclaw
**API Key:** `pck_live_2a89b562ccd65cb18a54bdebb41e35246e6a2961412b5c11d352f65e567085a4`
**Status:** Active
**Rate Limit:** 10 campaigns/day
**Wallet:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7` (Base)

### API Verification Results
- ✅ `POST /agents/register` — Self-serve registration works, no auth needed
- ✅ `GET /agents/me` — Profile + credit balance returned correctly
- ✅ `GET /agents/products/search?q=Base` — Product discovery works
- ✅ `POST /agents/campaigns` — Returns proper 402 insufficient_credits error
- ✅ `POST /agents/campaigns/boost` — Returns proper 402 insufficient_credits error
- ✅ `POST /agents/credits/topup` — Returns x402 + direct transfer payment options

### Key Finding: No Free Credits
The "300 free credits" mentioned in older documentation (v3.0.0 skill docs) is **no longer available**. Current free plan gives **0 credits**. Need to top up with USDC on Base.

### Topup Options
- **nano:** 40 credits / $2 USDC
- **micro:** 200 credits / $10 USDC  
- **small:** 550 credits / $25 USDC
- **medium:** 1,200 credits / $50 USDC
- **large:** 2,600 credits / $100 USDC
- **enterprise:** 14,000 credits / $500 USDC

**Payment address:** `0x876Be690234aaD9C7ae8bb02c6900f5844aCaF68` on Base (chain 8453)
**Payment methods:** x402 protocol (auto) OR direct USDC transfer + tx hash

### Campaign Pricing
- **Discover campaign:** 10 cr create + 12 cr/post generate
- **Boost replies:** 200 cr (10 community replies)
- **Boost likes:** 300 cr (30 likes)
- **Boost reposts:** 300 cr (10 reposts)

### Link to User Account
Generated link URL for account connection (expired, can regenerate):
`https://app.productclank.com/link/agent?token=fbc3b228-b0f2-4422-a850-3ffa90fe0e9d`
API: `POST /agents/create-link` with Bearer token

### Blockers
1. **USDC funding needed** — Base wallet has 0 USDC. Need ~$10 to buy micro bundle (200 credits) and run first campaigns.
2. **Product ID needed** — Campaigns require a product registered on ProductClank. Could use existing product or create one.

### Next Steps
1. Get USDC on Base wallet (bridge, exchange, or faucet)
2. Top up credits via API
3. Create/register a product for Manteclaw
4. Launch first Boost campaign (e.g., on a tweet about Base AI agents)
5. Or launch Discover campaign for "AI agents" + "Base" + "autonomous" keywords

### Resources
- **Developer docs:** https://productclank.com/developers
- **Raw API docs:** https://api.productclank.com/api/v1/docs
- **Dashboard:** https://app.productclank.com/communiply/
- **CLI:** `npm i -g github:covariance-network/communiply-cli`
