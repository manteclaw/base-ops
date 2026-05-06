# Multi-Lane Orchestrator MCP Server

Auto-balances compute across agentic earning lanes with health checks and earnings tracking.

## Tools

- `register_lane(name, priority, endpoint)` — add/update a lane
- `get_lane_status(name)` — lane health, earnings, status
- `allocate_resources()` — % allocation per active lane (yield-weighted or round-robin)
- `report_earning(name, amount)` — record earnings
- `get_leaderboard()` — lanes ranked by cumulative earnings
- `set_lane_health(name, health)` — manual health override
- `reset_lane(name)` — reset earnings (testing)
- `list_lanes()` — all lanes
- `heartbeat_check()` — auto-degrade stale lanes

## Pre-registered Lanes

| Lane | Description | Priority |
|------|-------------|----------|
| litcoiin | Bankr research mining | 7 |
| nookplot | Knowledge mining + bounties | 6 |
| 0xwork | Task bidding | 5 |
| moltlaunch | Skill marketplace | 5 |
| daydreams | Taskmarket daemon | 4 |
| zyfai | Yield farming | 8 |
| openagent | Skill marketplace | 4 |

## Run

```bash
pip install -r requirements.txt
python server.py
```

## Test

```bash
python test_alloc.py
```
