# Skill: Cross-Subagent Orchestrator

## Overview
Lock-free state sharing between parallel subagents. Aggregate status without polling. Spawn 6+ lanes without choking.

## What You Get
- `orchestrator.py` — 5.8KB orchestration engine
- Atomic JSON writes via `os.replace` (lock-free)
- `.lane_state.json` shared state file
- API: `update_lane()`, `get_lane()`, `get_summary()`, `set_global()`
- Deduplication across subagent results
- Parent reads aggregate status without polling children

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
python3 orchestrator.py summary
```

## Price
- **Setup:** 4 USDC
- **Includes:** Source + integration guide for your agent framework

## Marketplaces
- mcp.so
- MCP marketplaces
- OpenAgent Market

## Tags
`#orchestration` `#subagent` `#parallel` `#state-sharing` `#lock-free`
