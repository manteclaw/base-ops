# Delta Monitor MCP Server

Proactive delta monitor — only acts when state changes. Eliminates heartbeat noise.

## Install

```bash
pip install mcp
python3 server.py
```

## Usage (Claude / Cursor / Cline)

```json
{
  "mcpServers": {
    "deltamonitor": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/deltamonitor/server.py"]
    }
  }
}
```

## Tools

### `watch_state`
Register a watch on a state key with a threshold and alert template.
- `key` — State key to watch
- `threshold` — Numeric threshold: alert only fires if abs(change) > threshold
- `alert_template` — Template string with `{key}`, `{old}`, `{new}`, `{diff}`, `{diff_pct}`, `{direction}`

### `check_delta`
Check if a state key changed and return delta + alert.
- `key` — State key
- `new_value` — The new value to compare

Returns: `changed`, `old_value`, `new_value`, `delta` (with `type`, `diff`, `diff_pct`, `direction`), `alert`, `triggered`

### `get_active_alerts`
Get all active delta alerts, optionally filtered by key or time.
- `limit` — Max alerts to return
- `key_filter` — Only return alerts for this key
- `since_minutes` — Only return alerts from last N minutes

### `reset_state`
Clear stored state for a key or all keys.
- `key` — Specific key to clear, or omit to clear everything

### `bulk_check`
Check multiple keys at once and return only messages for changed ones.
- `readings` — Dict mapping keys to current values

## Example

```python
# Watch Litcoiin balance with 1000 threshold
watch_state(
    key="litcoiin_balance",
    threshold=1000,
    alert_template="💰 Litcoiin {direction} by {diff} → {new}"
)

# Check if balance changed — returns claim alert if change > 1000
check_delta(key="litcoiin_balance", new_value=51000)

# Bulk check multiple systems
bulk_check({
    "litcoiin_balance": 52000,
    "nookplot_credits": 150,
    "marketplace_tasks": ["task1", "task2"]
})
```
