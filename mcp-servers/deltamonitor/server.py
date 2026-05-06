#!/usr/bin/env python3
"""
Delta Monitor MCP Server
Watch state keys, detect changes, trigger threshold alerts.
Only acts when value changes — zero heartbeat noise.
"""

import json
import math
from datetime import datetime
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("deltamonitor")

# ── In-memory state store ──
_state: dict[str, Any] = {}          # key -> last known value
_watches: dict[str, dict] = {}       # key -> {threshold, alert_template, last_alert_value}
_alerts: list[dict] = []             # fired alerts history


def _json_equal(a: Any, b: Any) -> bool:
    """Deep equality check for JSON-serializable values."""
    try:
        return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    except (TypeError, ValueError):
        return a == b


def _compute_delta(old: Any, new: Any) -> dict:
    """Compute diff between old and new values."""
    delta = {"type": "unknown", "diff": None}

    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        delta["type"] = "numeric"
        delta["diff"] = round(new - old, 6)
        delta["diff_pct"] = round((new - old) / old * 100, 2) if old and old != 0 else None
        delta["direction"] = "up" if new > old else "down" if new < old else "flat"
    elif isinstance(old, list) and isinstance(new, list):
        delta["type"] = "list"
        delta["added"] = [x for x in new if x not in old]
        delta["removed"] = [x for x in old if x not in new]
        delta["diff"] = len(delta["added"]) - len(delta["removed"])
    elif isinstance(old, dict) and isinstance(new, dict):
        delta["type"] = "dict"
        added = {k: new[k] for k in new if k not in old}
        removed = {k: old[k] for k in old if k not in new}
        changed = {k: {"old": old[k], "new": new[k]} for k in old if k in new and not _json_equal(old[k], new[k])}
        delta["added"] = added
        delta["removed"] = removed
        delta["changed"] = changed
        delta["diff"] = len(added) + len(removed) + len(changed)
    else:
        delta["type"] = "scalar"
        delta["diff"] = f"{old} → {new}"

    return delta


def _format_alert(template: str, key: str, old: Any, new: Any, delta: dict) -> str:
    """Substitute variables into alert template."""
    try:
        return template.format(
            key=key,
            old=old,
            new=new,
            diff=delta.get("diff"),
            diff_pct=delta.get("diff_pct"),
            direction=delta.get("direction"),
        )
    except Exception:
        return f"[{key}] changed: {old} → {new} (diff: {delta.get('diff')})"


@mcp.tool()
def watch_state(
    key: str,
    threshold: Optional[float] = None,
    alert_template: str = "[{key}] changed: {old} → {new} (diff: {diff})",
) -> dict:
    """
    Register a watch on a state key with a threshold and alert template.

    Args:
        key: State key to watch (e.g. "litcoiin_balance", "nookplot_credits")
        threshold: Numeric threshold — alert only fires if abs(change) > threshold
        alert_template: Template string with {key}, {old}, {new}, {diff}, {diff_pct}, {direction}

    Returns:
        Dict confirming the watch registration.
    """
    _watches[key] = {
        "threshold": threshold,
        "alert_template": alert_template,
        "registered_at": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "registered": True,
        "key": key,
        "threshold": threshold,
        "alert_template": alert_template,
        "current_value": _state.get(key),
        "watched_keys": list(_watches.keys()),
    }


@mcp.tool()
def check_delta(key: str, new_value: Any) -> dict:
    """
    Check if a state key changed and return delta + alert if so.

    Args:
        key: State key to check
        new_value: The new value to compare against stored state

    Returns:
        Dict with changed (bool), old_value, new_value, delta, alert (or None if no change).
    """
    old_value = _state.get(key)

    if _json_equal(old_value, new_value):
        return {
            "changed": False,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "delta": None,
            "alert": None,
        }

    # Compute delta
    delta = _compute_delta(old_value, new_value)

    # Update state
    _state[key] = new_value

    # Check threshold + build alert
    watch = _watches.get(key, {})
    threshold = watch.get("threshold")
    alert = None
    triggered = False

    if threshold is not None:
        # Numeric threshold comparison
        if delta["type"] == "numeric" and abs(delta.get("diff", 0)) > threshold:
            triggered = True
        elif delta["type"] == "list" and abs(delta.get("diff", 0)) > threshold:
            triggered = True
        elif delta["type"] == "dict" and abs(delta.get("diff", 0)) > threshold:
            triggered = True
    else:
        # No threshold — any change triggers
        triggered = True

    if triggered:
        template = watch.get("alert_template", "[{key}] changed: {old} → {new} (diff: {diff})")
        alert = _format_alert(template, key, old_value, new_value, delta)

        _alerts.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "delta": delta,
            "alert": alert,
            "threshold": threshold,
            "triggered": triggered,
        })

    return {
        "changed": True,
        "key": key,
        "old_value": old_value,
        "new_value": new_value,
        "delta": delta,
        "alert": alert,
        "threshold": threshold,
        "triggered": triggered,
    }


@mcp.tool()
def get_active_alerts(
    limit: int = 50,
    key_filter: Optional[str] = None,
    since_minutes: Optional[int] = None,
) -> dict:
    """
    Get all active delta alerts, optionally filtered.

    Args:
        limit: Max number of alerts to return (default 50)
        key_filter: Only return alerts for this key (optional)
        since_minutes: Only return alerts from the last N minutes (optional)

    Returns:
        Dict with alerts list, counts, and watch registry.
    """
    alerts = _alerts

    if key_filter:
        alerts = [a for a in alerts if a["key"] == key_filter]

    if since_minutes:
        cutoff = datetime.utcnow().timestamp() - (since_minutes * 60)
        alerts = [
            a for a in alerts
            if datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00")).timestamp() > cutoff
        ]

    alerts = alerts[-limit:]

    return {
        "alerts": alerts,
        "count": len(alerts),
        "total_ever": len(_alerts),
        "watched_keys": list(_watches.keys()),
        "stored_keys": list(_state.keys()),
        "watches": _watches,
    }


@mcp.tool()
def reset_state(key: Optional[str] = None) -> dict:
    """
    Clear stored state for a key or all keys.

    Args:
        key: Specific key to clear, or omit to clear all state + watches + alerts

    Returns:
        Dict confirming reset.
    """
    if key:
        _state.pop(key, None)
        _watches.pop(key, None)
        return {
            "reset": True,
            "key": key,
            "remaining_keys": list(_state.keys()),
            "remaining_watches": list(_watches.keys()),
        }
    else:
        _state.clear()
        _watches.clear()
        _alerts.clear()
        return {
            "reset": True,
            "all_keys_cleared": True,
            "watches_cleared": True,
            "alerts_cleared": True,
        }


@mcp.tool()
def bulk_check(readings: dict[str, Any]) -> dict:
    """
    Check multiple keys at once and return only messages for changed ones.

    Args:
        readings: Dict mapping keys to their current values

    Returns:
        Dict with changed_count, changes list, and unchanged_count.
    """
    results = []
    for key, value in readings.items():
        result = check_delta(key=key, new_value=value)
        if result["changed"]:
            results.append(result)

    return {
        "changed_count": len(results),
        "changes": results,
        "unchanged_count": len(readings) - len(results),
        "keys_checked": list(readings.keys()),
    }


if __name__ == "__main__":
    mcp.run()
