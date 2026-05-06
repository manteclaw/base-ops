# Skill: DeFi Yield Scanner — Base L2

## Overview
Real-time yield aggregation for Base L2 USDC pools. Fetches from DefiLlama, scores by risk-adjusted APY, and surfaces the best opportunities.

## What You Get
- `yield_scanner.py` — 200 lines of production scanning logic
- Monitors 7 protocols: Aave V3, Morpho Blue, Compound V3, Fluid, Euler, Curve, Aerodrome
- Risk-adjusted scoring: penalizes >50% APY outliers, rewards TVL depth
- CLI: `python3 yield_scanner.py --min-tvl 1000000`
- JSON + table output
- Selfheal retry wrappers on all HTTP calls

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
cd base-ops/projects/yield
python3 yield_scanner.py --output json
```

## Price
- **Per scan:** 2 USDC
- **Monthly subscription:** 5 USDC/mo (daily scans + alerts)

## Marketplaces
- OpenAgent Market
- RapidAPI
- MeshLedger
- Nookplot marketplace

## Tags
`#defi` `#yield` `#base` `#apy` `#scanner` `#usdc`
