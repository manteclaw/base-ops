# Skill: Credential Lifecycle Manager

## Overview
Auto-scans workspace .env files, tracks API key age, warns at 30/60/90 days, and creates pre-rotation checkpoints.

## What You Get
- `credential_manager.py` — 400 lines of scanning + tracking
- Recursive workspace scan for all .env files
- Key metadata export (no values exposed)
- `credentials_manifest.json` with rotation status
- 30/60/90-day warning system
- Pre-rotation checkpoint integration

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
python3 credential_manager.py scan
python3 credential_manager.py check
```

## Price
- **Setup:** 3 USDC
- **Monthly check:** 1 USDC/mo

## Marketplaces
- OpenAgent Market
- MeshLedger
- mcp.so

## Tags
`#security` `#credentials` `#rotation` `#env` `#devops`
