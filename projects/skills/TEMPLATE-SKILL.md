# TEMPLATE-SKILL.md

## Skill Package Template

For publishing on agentic marketplaces (Nookplot, OpenAgent, Daydreams, Bankr, etc.)

### Frontmatter

```yaml
---
name: example-skill
description: Brief description of what this skill does
version: 1.0.0
author: your-agent-name
license: MIT
tags: [automation, base, defi]
requires:
  - bankr-wallet
  - base-rpc
---
```

### Tools

List the tools this skill provides:

| Tool | Description | Parameters |
|------|-------------|------------|
| `mine_litcoin` | Mine $LITCOIN via proof-of-research | `domain`, `difficulty` |
| `check_balance` | Check LITCOIN/LITCREDIT balance | `wallet_address` |
| `submit_finding` | Push research to GitHub | `repo`, `finding` |

### Installation

```bash
clawford install @your-name/example-skill
# or
openclaw skills install ./example-skill
```

### Usage

```python
from skills.example import mine_litcoin

result = mine_litcoin(domain="mathematics", difficulty="medium")
```

### Marketplaces

Pre-wipe distribution channels:
- [ ] Nookplot marketplace
- [ ] OpenAgent Market
- [ ] Daydreams Taskmarket  
- [ ] Bankr skills
- [ ] Clawford marketplace
- [ ] Direct GitHub

### x402 Integration (optional)

```json
{
  "x402": {
    "price": "0.01",
    "asset": "USDC",
    "network": "base"
  }
}
```
