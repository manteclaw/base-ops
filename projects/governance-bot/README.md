# Governance Vote Bot

Automated Snapshot governance voting for DAO delegates on Base L2.

## Features
- **Snapshot GraphQL polling** — fetches active proposals every 5 min
- **EIP-712 vote signing** — gasless off-chain votes
- **Rule-based voting engine** — configurable yes/no/abstain/choice rules
- **Duplicate vote detection** — skips already-voted proposals
- **Structured logging** — newline-delimited JSON audit trail
- **Selfheal retry** — automatic retry on Snapshot hub failures

## Quick Start

```bash
cd projects/governance-bot

# 1. Edit config.json with your wallet + private key
# 2. List active proposals for a space
python3 governance_bot.py --list-proposals aave.eth

# 3. Run one polling cycle (dry run, no votes cast)
python3 governance_bot.py --once

# 4. Run daemon mode
python3 governance_bot.py
```

## Config

```json
{
  "wallet_address": "0x...",
  "private_key": "0x...",
  "snapshot_hub": "https://hub.snapshot.org/graphql",
  "network": "8453",
  "poll_interval_seconds": 300,
  "spaces": ["aave.eth", "uniswap.eth"],
  "rules": {
    "rules": [
      {
        "name": "Safety abstain",
        "if": [
          {"field": "title_contains", "op": "contains", "value": "risk"}
        ],
        "action": "abstain",
        "reason": "Risk params need human review"
      }
    ],
    "default_choice": null
  }
}
```

## Price
- **Setup:** 7 USDC (one-time)
- **Maintenance:** 2 USDC/mo

## Tags
`#dao` `#governance` `#snapshot` `#eip-712` `#vote` `#delegate`
