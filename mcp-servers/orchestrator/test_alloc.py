#!/usr/bin/env python3
"""Quick standalone test of the orchestrator allocation logic."""

import json
import sys
sys.path.insert(0, "/root/.openclaw/workspace/mcp-servers/orchestrator")

from server import store, allocate_resources, report_earning, get_leaderboard

# Seed some fake earnings to test weighting
report_earning("zyfai", 12.50)
report_earning("litcoiin", 3.20)
report_earning("nookplot", 1.80)
report_earning("0xwork", 0.0)

print("=== Allocation (yield-weighted) ===")
print(allocate_resources())

print("\n=== Leaderboard ===")
print(get_leaderboard())

# Mark a lane dead and re-allocate
from server import set_lane_health
set_lane_health("0xwork", "dead")

print("\n=== Allocation after 0xwork marked dead ===")
print(allocate_resources())

print("\n=== All lanes ===")
print(json.dumps([l.model_dump() for l in store.all()], indent=2))
