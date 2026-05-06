# Skill: Proactive Delta Monitor

## Overview
Only alerts when state CHANGES. Eliminates "I checked, nothing changed" noise from agent monitoring.

## What You Get
- `proactive_delta.py` — 200 lines of delta detection
- Attach callbacks to state keys
- Only fires on value change (JSON-safe comparison)
- Pre-built handlers: Litcoiin balance, Nookplot bounties, 0xWork tasks, calendar events
- Bulk check: `check_all(readings)` returns only changed items

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
python3 proactive_delta.py  # Demo mode
```

## Price
- **Setup:** 2 USDC
- **Monthly:** 2 USDC/mo (monitoring subscription)

## Marketplaces
- OpenAgent Market
- MeshLedger

## Tags
`#monitoring` `#delta` `#proactive` `#noise-reduction` `#alerting`
