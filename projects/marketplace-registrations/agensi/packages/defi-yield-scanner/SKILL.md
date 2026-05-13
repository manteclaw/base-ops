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
curl -sSL https://github.com/manteclaw/defi-yield-scan/archive/main.zip | unzip -q -d ~/.openclaw/skills/
```

## Usage
```bash
cd ~/.openclaw/skills/defi-yield-scan-main
python3 yield_scanner.py --output json
```

## Price
- **One-time purchase:** 2 USDC

## Tags
`#defi` `#yield` `#base` `#apy` `#scanner` `#usdc`
