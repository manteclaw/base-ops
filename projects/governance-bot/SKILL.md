# base-governance-bot

## Description

Automated governance vote bot for Snapshot-based DAOs on Base L2 (and any EVM chain). Polls for active proposals, evaluates them against configurable rule sets, and casts gasless off-chain votes via EIP-712 signatures. Designed to run headless as a cron job or daemon.

**Price:** 7 USDC setup fee (one-time) + optional 2 USDC/mo for rule customization support.

## Use Cases

- DAO delegates who want automated voting on routine proposals
- Treasury managers who need skip/abstain rules for large transfers
- Agents that participate in governance on behalf of token holders
- Multi-DAO monitoring from a single bot instance

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`
- A wallet with governance token balance (for voting power)
- Snapshot space ID(s) you want to monitor

## Installation

1. Clone/copy the skill directory:
```bash
git clone <repo> projects/governance-bot
cd projects/governance-bot
pip install -r requirements.txt
```

2. Configure `config.json`:
```json
{
  "wallet_address": "0x...",
  "private_key": "0x...",
  "spaces": ["aave.eth", "uniswap"],
  "poll_interval_seconds": 300,
  "rules": { ... }
}
```

3. Run:
```bash
python governance_bot.py              # daemon mode
python governance_bot.py --once       # single poll
python governance_bot.py --list-proposals aave.eth
```

## Rule Engine

Rules are evaluated top-down. First match wins. Each rule has:

- `name`: human-readable label
- `if`: list of conditions (all must match)
- `action`: `yes` | `no` | `abstain` | `choice:N` | `skip`
- `reason`: logged for audit

### Condition Types

| Field | Operators | Description |
|-------|-----------|-------------|
| `title_contains` | `contains`, `regex` | Match proposal title |
| `body_contains` | `contains` | Match proposal body |
| `space` | `eq` | Exact space ID match |
| `author_in` | `eq` (list) | Match proposal author |

### Example Rules

```json
{
  "rules": [
    {
      "name": "Emergency — Auto Yes",
      "if": [
        {"field": "title_contains", "op": "contains", "value": "emergency"}
      ],
      "action": "yes",
      "reason": "Emergency proposals get automatic approval"
    },
    {
      "name": ">$1M Transfer — Skip",
      "if": [
        {"field": "title_contains", "op": "regex", "value": "treasury|transfer"},
        {"field": "body_contains", "op": "contains", "value": "1000000"}
      ],
      "action": "skip",
      "reason": "Large transfers require manual review"
    }
  ],
  "default_choice": null,
  "default_reason": "No rule matched — manual review"
}
```

## Architecture

```
governance_bot.py       — Main loop, orchestration
snapshot_client.py      — GraphQL queries + EIP-712 signing
voting_engine.py        — Rule evaluation + choice resolution
logger.py               — Structured ND-JSON logging
config.json             — Per-deployment configuration
```

## How to Sell

This skill is packaged as a **done-for-you governance automation service**:

1. **Discovery:** Post on Nookplot skills marketplace, OpenAgent Market, MoltLaunch
2. **Pitch:** "Automate your DAO voting — never miss a proposal, never vote wrong on routine upgrades"
3. **Pricing:**
   - 7 USDC — bot setup + 3 custom rules
   - 15 USDC — setup + 10 rules + priority monitoring
   - 50 USDC/year — white-glove multi-DAO management
4. **Delivery:** GitHub repo + 15-min config call (or async config review)
5. **Upsell:** Custom rule development, new chain integrations, on-chain execution layer

## Safety

- **Never auto-vote on treasury transfers** unless explicitly configured
- `skip` action is safe — it logs and moves on
- All votes are off-chain (gasless) via Snapshot; no funds at risk
- Private key is your responsibility — store in env vars or secure vault

## Changelog

- v0.1.0 (2026-05-07) — Initial skeleton: Snapshot polling, EIP-712 signing, rule engine, logging

## License

MIT — sell it, fork it, scale it.
