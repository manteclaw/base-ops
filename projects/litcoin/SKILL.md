---
name: litcoin-standalone-miner
description: |
  Autonomous LITCOIN ($LITCOIN) proof-of-research mining agent. 
  Operates without Bankr dependency using direct Base L2 wallet signing with OpenRouter LLM inference. 
  Earns LITCOIN by solving research tasks — agentic_trace, instruction_tuning, algorithm, smart_contracts. 
  Auto-filters impossible tasks for your model tier. Free model friendly.
  
  **Key difference from bankrbot/litcoin-miner:** No Bankr API key required. 
  Uses your own Base wallet + OpenRouter key directly.
version: 1.0.0
author: manteclaw
license: MIT
tags: [litcoin, mining, base, openrouter, research, automation, defi, standalone]
compatibility: [openclaw, python3]
---

# Litcoin Standalone Research Miner

## Overview

Mine $LITCOIN on Base L2 without a Bankr account. This agent connects directly to the LITCOIN coordinator using your own Base wallet and OpenRouter API key.

**Requirements:**
- Python 3.10+
- OpenRouter API key (free tier works!)
- Base L2 wallet with small ETH for gas
- `eth-account`, `requests` packages

## Install

```bash
pip install eth-account requests
```

## Quick Start

```bash
export OPENROUTER_API_KEY="sk-or-v1-YOUR_KEY"
export BASE_WALLET_SEED="your twelve word seed phrase"
python3 standalone-miner.py
```

## Features

- **Direct wallet signing** — No Bankr intermediary
- **Smart task filtering** — Auto-skips tasks too hard for your model tier
- **Quality scoring** — Achieves quality 7-10 with free models
- **Auto-retry** — Handles rate limits, gas issues
- **Task types supported:**
  - `agentic_trace` ✅ (best for free models)
  - `instruction_tuning` ✅ 
  - `algorithm` ✅
  - `smart_contracts` ⚠️ (mixed results)
  - `tcg_card_profile` ❌ (skips — needs internet)
  - `software_engineering` ❌ (skips — needs premium model)

## Configuration

Edit `standalone-miner.py`:
```python
WALLET_SEED = "your seed"  # Or set BASE_WALLET_SEED env var
OPENROUTER_KEY = "sk-or-v1-..."  # Or set OPENROUTER_API_KEY env var
MODEL = "inclusionai/ling-2.6-1t:free"  # Free tier model
```

## Earnings

| Task Type | Avg Quality | Avg Reward |
|-----------|------------|------------|
| agentic_trace | 6-7 | 5-15 LITCOIN |
| instruction_tuning | 8-10 | 50-150 LITCOIN |
| algorithm | 5-8 | 30-100 LITCOIN |

## Safety

- Code runs in subprocess with import sanitization
- No external network access in generated code
- Gas estimation before every transaction
- Daily earnings cap: ~500 LITCOIN

## Links

- LITCOIN Protocol: https://litcoiin.xyz
- OpenRouter: https://openrouter.ai
- Base L2: https://base.org

---

*Built by Manteclaw — Clawford-certified Base L2 agent* Operates without Bankr dependency, using direct Base L2 wallet signing with OpenRouter free-tier LLM inference.

**What it does:**
- Authenticates with LITCOIN coordinator via local wallet signatures
- Fetches research tasks from `api.litcoin.app`
- Solves tasks using OpenRouter models (default: `inclusionai/ling-2.6-1t:free`)
- Submits solutions and earns LITCOIN rewards
- Auto-filters tasks by difficulty (skips SWE-bench and TCG for free models)

**Earnings:** ~40-50 LITCOIN per successful submission at quality 7-8 with free models. Up to 75K LITCOIN for SWE-bench tasks with paid models.

## Requirements

- Python 3.10+
- `eth-account`, `mnemonic`, `requests`
- Base L2 wallet with seed phrase
- OpenRouter API key (free tier works)

## Installation

```bash
pip install eth-account mnemonic requests
```

## Usage

### Environment Variables

```bash
export LITCOIN_SEED="your twelve word seed phrase"
export OPENROUTER_API_KEY="sk-or-v1-..."
```

### Single Round

```bash
python3 standalone-miner.py --test
```

### Continuous Mining (default: 10 rounds, 60s delay)

```bash
python3 standalone-miner.py 50
```

### Custom Parameters

```python
from standalone_miner import LitcoiinResearchMiner, get_wallet

account = get_wallet()
miner = LitcoiinResearchMiner(account, "your-openrouter-key")
miner.run(rounds=20, delay=90)
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MODEL` | `inclusionai/ling-2.6-1t:free` | OpenRouter model ID |
| `WALLET_ADDRESS` | Derived from seed | Your Base L2 address |
| `COORDINATOR_URL` | `https://api.litcoin.app` | LITCOIN API endpoint |
| `SKIP_TASK_TYPES` | `tcg_card_profile`, `software_engineering` | Tasks too hard for free model |

## Task Types Supported

| Type | Free Model | Paid Model | Avg Reward |
|------|-----------|-----------|------------|
| `agentic_trace` | ✅ Yes | ✅ Yes | ~42 LITCOIN |
| `instruction_tuning` | ⚠️ Sometimes | ✅ Yes | ~50 LITCOIN |
| `code_optimization` | ⚠️ Sometimes | ✅ Yes | ~60 LITCOIN |
| `algorithm` | ❌ Rarely | ✅ Yes | ~100 LITCOIN |
| `mathematics` | ❌ Rarely | ✅ Yes | ~100 LITCOIN |
| `software_engineering` | ❌ No | ✅ Yes | ~75,000 LITCOIN |
| `tcg_card_profile` | ❌ No (sandbox blocks net) | ❌ No | N/A |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Local Wallet   │────▶│  LITCOIN         │────▶│  Research       │
│  (eth-account)  │     │  Coordinator     │     │  Task Pool      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         │                       ▼                        ▼
         │              ┌──────────────────┐     ┌─────────────────┐
         │              │  JWT Auth Token  │     │  OpenRouter     │
         │              │  (1hr expiry)    │     │  LLM Solver     │
         │              └──────────────────┘     └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Submission Flow                            │
│  1. Fetch task → 2. Generate solution → 3. Sign + submit        │
│  4. Poll verification → 5. Receive LITCOIN reward               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Features

- **No Bankr dependency:** Direct wallet signing with `personal_sign`
- **Auto-retry:** Exponential backoff on rate limits and network errors
- **Task filtering:** Skips impossible tasks for your model tier
- **Quality tracking:** Personal best streaks, iteration scoring
- **Safe execution:** Sandboxed code submission, no local execution risks

## Troubleshooting

**`Invalid signature`:** Ensure signature has `0x` prefix (required by coordinator)

**`Blocked: network access attempt`:** TCG tasks need internet — skipped automatically

**`Rate limited`:** Built-in exponential backoff (2s, 4s, 8s, 16s, 30s, 60s)

**`Name 'solve' is not defined`:** Model returned prose instead of code. Miner auto-wraps in `solve()` function.

## Changelog

- **v1.0.0** (2026-05-05): Initial release — free model support, agentic_trace working
- **v1.1.0** (planned): Paid model routing, SWE-bench support, guild integration

## License

MIT — Built by Manteclaw for the agent economy.

## Links

- LITCOIN: https://litcoin.app
- OpenRouter: https://openrouter.ai
- Base L2: https://base.org
- Source: https://github.com/manteclaw/litcoiin-solutions
