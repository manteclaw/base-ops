from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
import json
import os

DATA_PATH = os.environ.get("ORCHESTRATOR_DATA_PATH", "/root/.openclaw/workspace/mcp-servers/orchestrator/lanes.json")

class Lane(BaseModel):
    name: str
    endpoint: str
    priority: int = 5
    status: Literal["active", "paused", "dead"] = "active"
    health: Literal["healthy", "degraded", "dead"] = "healthy"
    last_earning: float = 0.0
    cumulative_earning: float = 0.0
    last_activity: Optional[str] = None
    fail_count: int = 0

class LaneStore:
    def __init__(self, path: str):
        self.path = path
        self.lanes: dict[str, Lane] = {}
        self._load()
        self._maybe_seed()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                data = json.load(f)
                for name, raw in data.items():
                    self.lanes[name] = Lane(**raw)

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({k: v.model_dump() for k, v in self.lanes.items()}, f, indent=2)

    def _maybe_seed(self):
        defaults = [
            ("litcoiin",   "Bankr research mining",       7),
            ("nookplot",   "Knowledge mining + bounties", 6),
            ("0xwork",     "Task bidding",                5),
            ("moltlaunch", "Skill marketplace",           5),
            ("daydreams",  "Taskmarket daemon",           4),
            ("zyfai",      "Yield farming",               8),
            ("openagent",  "Skill marketplace",           4),
        ]
        for name, endpoint, priority in defaults:
            if name not in self.lanes:
                self.lanes[name] = Lane(name=name, endpoint=endpoint, priority=priority)
        self._save()

    def get(self, name: str) -> Optional[Lane]:
        return self.lanes.get(name)

    def upsert(self, lane: Lane):
        self.lanes[lane.name] = lane
        self._save()

    def all(self) -> list[Lane]:
        return list(self.lanes.values())

    def delete(self, name: str):
        self.lanes.pop(name, None)
        self._save()

store = LaneStore(DATA_PATH)

mcp = FastMCP("multi-lane-orchestrator")

@mcp.tool()
def register_lane(name: str, priority: int, endpoint: str) -> str:
    """Register (or update) an earning lane."""
    existing = store.get(name)
    lane = Lane(
        name=name,
        priority=max(1, min(10, priority)),
        endpoint=endpoint,
        status=existing.status if existing else "active",
        health=existing.health if existing else "healthy",
        cumulative_earning=existing.cumulative_earning if existing else 0.0,
        last_earning=existing.last_earning if existing else 0.0,
    )
    store.upsert(lane)
    return f"Lane '{name}' registered with priority {lane.priority}."

@mcp.tool()
def get_lane_status(name: str) -> str:
    """Return JSON status for a single lane."""
    lane = store.get(name)
    if not lane:
        return json.dumps({"error": f"Lane '{name}' not found."})
    return lane.model_dump_json()

@mcp.tool()
def allocate_resources() -> str:
    """
    Allocate compute/time % across active healthy lanes.
    Weighted by: cumulative_earning (signal of proven yield) * priority.
    Dead/unhealthy/paused lanes get 0%.
    If no active lanes have earnings, falls back to round-robin equal split.
    """
    active = [
        l for l in store.all()
        if l.status == "active" and l.health in ("healthy", "degraded")
    ]
    if not active:
        return json.dumps({"allocation": {}, "note": "No active healthy lanes."})

    weights = []
    for l in active:
        weight = max(l.cumulative_earning, 0.01) * l.priority
        weights.append(weight)

    total = sum(weights)
    if total < 0.1:
        # Round-robin fallback
        n = len(active)
        allocation = {l.name: round(100 / n, 2) for l in active}
    else:
        allocation = {l.name: round((w / total) * 100, 2) for l, w in zip(active, weights)}

    # Normalize to exactly 100%
    current_sum = sum(allocation.values())
    if current_sum != 100.0:
        # Add/subtract from largest to keep math clean
        diff = round(100.0 - current_sum, 2)
        largest = max(allocation, key=allocation.get)
        allocation[largest] = round(allocation[largest] + diff, 2)

    return json.dumps({
        "allocation": allocation,
        "method": "yield-weighted" if total >= 0.1 else "round-robin",
        "timestamp": datetime.utcnow().isoformat(),
    })

@mcp.tool()
def report_earning(name: str, amount: float) -> str:
    """Record an earning for a lane and update its health."""
    lane = store.get(name)
    if not lane:
        return json.dumps({"error": f"Lane '{name}' not found. Register it first."})

    lane.last_earning = amount
    lane.cumulative_earning += amount
    lane.last_activity = datetime.utcnow().isoformat()
    lane.fail_count = 0
    if lane.health == "dead":
        lane.health = "healthy"
    store.upsert(lane)
    return json.dumps({
        "lane": name,
        "reported": amount,
        "cumulative": round(lane.cumulative_earning, 6),
        "health": lane.health,
    })

@mcp.tool()
def get_leaderboard() -> str:
    """Return lanes ranked by cumulative earnings (descending)."""
    lanes = sorted(store.all(), key=lambda l: l.cumulative_earning, reverse=True)
    return json.dumps([
        {
            "rank": i + 1,
            "name": l.name,
            "cumulative_earning": round(l.cumulative_earning, 6),
            "last_earning": round(l.last_earning, 6),
            "health": l.health,
            "status": l.status,
            "priority": l.priority,
            "last_activity": l.last_activity,
        }
        for i, l in enumerate(lanes)
    ])

@mcp.tool()
def set_lane_health(name: str, health: Literal["healthy", "degraded", "dead"]) -> str:
    """Manually override lane health."""
    lane = store.get(name)
    if not lane:
        return json.dumps({"error": f"Lane '{name}' not found."})
    lane.health = health
    if health == "dead":
        lane.status = "paused"
    store.upsert(lane)
    return json.dumps({"lane": name, "health": health, "status": lane.status})

@mcp.tool()
def reset_lane(name: str) -> str:
    """Reset a lane's earnings and health (useful for testing)."""
    lane = store.get(name)
    if not lane:
        return json.dumps({"error": f"Lane '{name}' not found."})
    lane.cumulative_earning = 0.0
    lane.last_earning = 0.0
    lane.health = "healthy"
    lane.status = "active"
    lane.fail_count = 0
    store.upsert(lane)
    return json.dumps({"lane": name, "reset": True})

@mcp.tool()
def list_lanes() -> str:
    """Return all registered lanes."""
    return json.dumps([l.model_dump() for l in store.all()])

@mcp.tool()
def heartbeat_check() -> str:
    """Run a health check across all lanes; degrade/dead them if stale."""
    now = datetime.utcnow()
    changed = []
    for lane in store.all():
        if lane.last_activity:
            last = datetime.fromisoformat(lane.last_activity)
            hours_stale = (now - last).total_seconds() / 3600
            if hours_stale > 48 and lane.health == "healthy":
                lane.health = "degraded"
                changed.append((lane.name, "degraded", f"{hours_stale:.1f}h stale"))
            elif hours_stale > 120 and lane.health == "degraded":
                lane.health = "dead"
                lane.status = "paused"
                changed.append((lane.name, "dead", f"{hours_stale:.1f}h stale"))
    if changed:
        store._save()
    return json.dumps({"checked": len(store.all()), "changed": changed})

if __name__ == "__main__":
    mcp.run()
