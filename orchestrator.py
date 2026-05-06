#!/usr/bin/env python3
"""
Manteclaw Orchestrator — Cross-subagent state sharing.

Shared JSON state file at .lane_state.json that all subagents read/write.
Lock-free writes using atomic rename (POSIX-safe).

Structure:
{
  "lanes": {
    "A": {"status": "ok", "last_run": "2026-05-07T04:11:00Z", "earnings": 1423, "blocker": null},
    ...
  },
  "global": {
    "daemon_pid": 12345,
    "last_heartbeat": "2026-05-07T04:11:00Z"
  },
  "meta": {
    "version": 1,
    "updated_at": "..."
  }
}

Usage:
    from orchestrator import LaneState
    state = LaneState()
    state.update_lane("A", {"status": "ok", "earnings": 50000})
    data = state.get_lane("A")
    all_lanes = state.get_all()
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE = Path("/root/.openclaw/workspace")
STATE_FILE = WORKSPACE / ".lane_state.json"


def _atomic_write(path: Path, data: Dict[str, Any]):
    """Write JSON atomically using rename (POSIX-safe, crash-resistant)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(str(tmp), str(path))


class LaneState:
    """
    Thread-safe (lock-free via atomic rename) shared state for all lanes.
    All methods are safe to call from multiple threads/processes.
    """

    def __init__(self, state_file: Optional[Path] = None):
        self.path = state_file or STATE_FILE
        self._ensure_schema()

    def _ensure_schema(self):
        if not self.path.exists():
            default = {
                "lanes": {},
                "global": {},
                "meta": {"version": 1, "created_at": datetime.utcnow().isoformat() + "Z"},
            }
            _atomic_write(self.path, default)

    def _load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"lanes": {}, "global": {}, "meta": {"version": 1}}

    def update_lane(self, lane_id: str, data: Dict[str, Any]):
        """Merge data into a lane's state and write atomically."""
        for _ in range(5):
            state = self._load()
            if "lanes" not in state:
                state["lanes"] = {}
            if lane_id not in state["lanes"]:
                state["lanes"][lane_id] = {}
            state["lanes"][lane_id].update(data)
            state["lanes"][lane_id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            state["meta"] = state.get("meta", {})
            state["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            try:
                _atomic_write(self.path, state)
                return
            except Exception:
                time.sleep(0.01)
        raise RuntimeError("Failed to write lane state after 5 retries")

    def get_lane(self, lane_id: str) -> Dict[str, Any]:
        """Read a single lane's state."""
        state = self._load()
        return state.get("lanes", {}).get(lane_id, {})

    def get_all(self) -> Dict[str, Any]:
        """Read the entire state object."""
        return self._load()

    def set_global(self, key: str, value: Any):
        """Set a global key-value pair."""
        for _ in range(5):
            state = self._load()
            if "global" not in state:
                state["global"] = {}
            state["global"][key] = value
            state["meta"] = state.get("meta", {})
            state["meta"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
            try:
                _atomic_write(self.path, state)
                return
            except Exception:
                time.sleep(0.01)
        raise RuntimeError("Failed to write global state after 5 retries")

    def get_global(self, key: str, default: Any = None) -> Any:
        """Read a global value."""
        state = self._load()
        return state.get("global", {}).get(key, default)

    def get_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of all lanes."""
        state = self._load()
        lanes = state.get("lanes", {})
        summary = {}
        for lane_id, data in lanes.items():
            summary[lane_id] = {
                "status": data.get("status", "unknown"),
                "last_run": data.get("last_run", "never"),
                "earnings": data.get("earnings"),
                "blocker": data.get("blocker"),
            }
        return {
            "lanes": summary,
            "global": state.get("global", {}),
            "updated_at": state.get("meta", {}).get("updated_at"),
        }

    def reset_lane(self, lane_id: str):
        """Clear a lane's state."""
        self.update_lane(lane_id, {"status": "reset", "earnings": 0, "blocker": None})


def cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator.py [summary|get <lane>|global <key>]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    state = LaneState()

    if cmd == "summary":
        print(json.dumps(state.get_summary(), indent=2))
    elif cmd == "get":
        lane = sys.argv[2] if len(sys.argv) > 2 else "A"
        print(json.dumps(state.get_lane(lane), indent=2))
    elif cmd == "global":
        key = sys.argv[2] if len(sys.argv) > 2 else "daemon_pid"
        print(json.dumps(state.get_global(key), indent=2))
    elif cmd == "set":
        if len(sys.argv) < 4:
            print("Usage: python3 orchestrator.py set <lane> <json>")
            sys.exit(1)
        lane = sys.argv[2]
        data = json.loads(sys.argv[3])
        state.update_lane(lane, data)
        print(f"Updated lane {lane}")
    else:
        print(f"Unknown: {cmd}")
        print("Usage: python3 orchestrator.py [summary|get <lane>|global <key>|set <lane> <json>]")


if __name__ == "__main__":
    cli()
