# Self-Healing API Executor MCP Server

**Price:** 3 USDC | **Skills:** Resilient API calling with circuit breaker, retry logic, health monitoring

## What It Does

Makes API calls bulletproof. If an endpoint goes down, the circuit breaker opens and returns cached data. When the endpoint recovers, the circuit closes automatically.

## Tools

- `call_api(url, method, body, timeout, retries, force)` — makes request with automatic retry and circuit breaker
- `get_endpoint_status(url)` — returns circuit breaker state, failure count, response times
- `reset_breaker(url)` — manually reset circuit breaker
- `list_all_endpoints()` — list all monitored endpoints

## Features

| Feature | Default | Description |
|---------|---------|-------------|
| Circuit breaker threshold | 3 failures | Opens after 3 consecutive failures |
| Recovery interval | 30s | Tries recovery every 30s when open |
| Default timeout | 10s | Per-request timeout |
| Default retries | 3 | Exponential backoff between retries |
| Cache | last-known-good | Returns cached data when circuit is open |

## HTTP Endpoints

- `GET /health` — health check with all endpoint statuses
- `GET /` — server info

## Install

```bash
cd mcp-servers/selfhealing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

## Example

```python
# Call API with protection
result = await call_api(
    "https://api.example.com/data",
    method="POST",
    body='{"key": "value"}',
    timeout=15,
    retries=2
)

# Check if endpoint is healthy
status = await get_endpoint_status("https://api.example.com/data")

# Reset after incident
await reset_breaker("https://api.example.com/data")
```

## Test

```bash
python test.py
```

All 8 tests pass including real httpbin.org calls and simulated failure scenarios.
