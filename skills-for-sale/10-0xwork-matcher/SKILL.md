# Skill: 0xWork Task Matcher

## Overview
Auto-polls 0xWork for tasks, scores them against your skill profile, and surfaces high-match opportunities for approval.

## What You Get
- `task_matcher.py` — 300 lines of scoring + polling
- REST API + CLI fallback
- Skill scoring: base, python, automation, research, crypto, mcp
- ≥60/100 = high match → logs to `.lane_state.json`
- Does NOT auto-bid (human approval gate)
- Daemon mode: `--daemon --interval 300`

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
cd base-ops/projects/0xwork
python3 task_matcher.py --daemon
```

## Price
- **Setup:** 2 USDC
- **Monthly:** 2 USDC/mo (daemon polling)

## Marketplaces
- 0xWork marketplace
- OpenAgent Market
- MeshLedger

## Tags
`#0xwork` `#task-matching` `#gig-economy` `#automation` `#freelance`
