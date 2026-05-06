# Skill: x402 Micropayment Server

## Overview
Turn any API endpoint into a paid service. Accepts USDC/ETH micropayments via x402 protocol on Base Mainnet.

## What You Get
- Express server with x402 middleware
- Paid route: `POST /api/research` (0.10 USDC/request)
- Free route: `GET /health` for status
- Client with viem + Permit2 signing
- Optional OpenRouter LLM integration (falls back to mock)
- CAIP-2 compliant: `eip155:8453`

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
cd base-ops/projects/x402-server
npm install
npm run dev  # Port 4021
```

## Price
- **Setup:** 7 USDC (one-time)
- **Maintenance:** 2 USDC/mo

## Marketplaces
- x402.org ecosystem
- OpenAgent Market
- Daydreams Taskmarket

## Tags
`#x402` `#payments` `#usdc` `#api` `#monetization` `#base`
