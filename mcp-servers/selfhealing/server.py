"""
Self-Healing API Executor MCP Server

Provides resilient API calling with circuit breaker, retry logic, and health monitoring.
"""

import asyncio
import json
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict, List
from urllib.parse import urljoin

import aiohttp
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("selfhealing")

# Initialize MCP server
mcp = FastMCP("selfhealing-api")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing if recovered


@dataclass
class EndpointStats:
    """Track endpoint health statistics."""
    url: str
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    recovery_timer: Optional[float] = None
    cached_response: Optional[Any] = None
    cached_status: int = 200
    response_times: List[float] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


# Global endpoint registry
_endpoints: Dict[str, EndpointStats] = {}

# Circuit breaker settings
CIRCUIT_FAILURE_THRESHOLD = 3       # Failures before opening
CIRCUIT_RECOVERY_INTERVAL = 30      # Seconds between recovery attempts
DEFAULT_TIMEOUT = 10                # Default request timeout
MAX_RETRIES = 3                     # Default retries


async def _make_request(
    url: str,
    method: str = "GET",
    body: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> tuple[int, Any, Optional[str]]:
    """Make a single HTTP request. Returns (status_code, data, error)."""
    
    default_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        default_headers.update(headers)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method.upper(),
                url=url,
                headers=default_headers,
                json=body if body else None,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                status = response.status
                
                # Try to parse JSON, fallback to text
                try:
                    data = await response.json()
                except:
                    data = {"text": await response.text()}
                
                return status, data, None
                
    except asyncio.TimeoutError:
        return 0, None, f"Request timeout after {timeout}s"
    except aiohttp.ClientError as e:
        return 0, None, f"Client error: {str(e)}"
    except Exception as e:
        return 0, None, f"Error: {str(e)}"


async def _try_endpoint(
    stats: EndpointStats,
    method: str,
    body: Optional[Dict],
    timeout: float,
    retries: int
) -> Dict[str, Any]:
    """Attempt request with retries, tracking circuit breaker state."""
    
    url = stats.url
    last_error = None
    start_time = time.time()
    
    for attempt in range(retries + 1):
        status, data, error = await _make_request(url, method, body, timeout=timeout)
        
        if error is None and status < 500:
            # Success!
            response_time = time.time() - start_time
            stats.response_times.append(response_time)
            stats.response_times = stats.response_times[-10:]  # Keep last 10
            
            stats.consecutive_failures = 0
            stats.successes += 1
            stats.last_success_time = time.time()
            stats.error_message = None
            
            # If was half-open, close the circuit
            if stats.state == CircuitState.HALF_OPEN:
                stats.state = CircuitState.CLOSED
                logger.info(f"Circuit closed for {url} - recovery confirmed")
            
            # Cache successful response
            stats.cached_response = {
                "status": status,
                "data": data,
                "cached": False
            }
            stats.cached_status = status
            
            return {
                "success": True,
                "status": status,
                "data": data,
                "url": url,
                "attempts": attempt + 1,
                "circuit_state": stats.state.value,
                "response_time_ms": round(response_time * 1000, 2),
                "from_cache": False
            }
        else:
            # Failure
            last_error = error or f"HTTP {status}"
            stats.consecutive_failures += 1
            stats.failures += 1
            stats.last_failure_time = time.time()
            stats.error_message = last_error
            
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {last_error}")
            
            # Check if circuit should open
            if stats.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD and stats.state != CircuitState.OPEN:
                stats.state = CircuitState.OPEN
                stats.recovery_timer = time.time()
                logger.warning(f"Circuit opened for {url} after {stats.consecutive_failures} failures")
            
            if attempt < retries:
                # Exponential backoff: 1s, 2s, 4s
                backoff = 2 ** attempt
                logger.info(f"Retrying {url} in {backoff}s...")
                await asyncio.sleep(backoff)
    
    # All retries exhausted
    return {
        "success": False,
        "status": 0,
        "data": None,
        "url": url,
        "attempts": retries + 1,
        "circuit_state": stats.state.value,
        "error": last_error,
        "from_cache": False
    }


def _check_recovery(stats: EndpointStats) -> bool:
    """Check if enough time has passed to try recovery (half-open)."""
    if stats.state != CircuitState.OPEN:
        return True
    
    if stats.recovery_timer and (time.time() - stats.recovery_timer) >= CIRCUIT_RECOVERY_INTERVAL:
        stats.state = CircuitState.HALF_OPEN
        stats.recovery_timer = time.time()
        logger.info(f"Circuit half-open for {stats.url} - testing recovery")
        return True
    
    return False


# ===================== MCP TOOLS =====================

@mcp.tool()
async def call_api(
    url: str,
    method: str = "GET",
    body: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES,
    force: bool = False
) -> str:
    """
    Make an API call with automatic retry and circuit breaker protection.
    
    Args:
        url: The endpoint URL to call
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        body: JSON body string for POST/PUT requests
        timeout: Request timeout in seconds (default: 10)
        retries: Number of retries on failure (default: 3)
        force: Bypass circuit breaker and force the request
    
    Returns:
        JSON string with result including success status, data, and circuit state
    """
    
    # Get or create endpoint stats
    if url not in _endpoints:
        _endpoints[url] = EndpointStats(url=url)
    
    stats = _endpoints[url]
    
    # Check circuit breaker
    if not force and stats.state == CircuitState.OPEN:
        if not _check_recovery(stats):
            # Circuit is open, return cached data if available
            if stats.cached_response:
                cached = stats.cached_response.copy()
                cached["cached"] = True
                return json.dumps({
                    "success": True,
                    "status": stats.cached_status,
                    "data": cached.get("data"),
                    "url": url,
                    "circuit_state": stats.state.value,
                    "from_cache": True,
                    "note": "Circuit breaker OPEN - returning cached data"
                }, indent=2)
            
            return json.dumps({
                "success": False,
                "status": 503,
                "url": url,
                "circuit_state": stats.state.value,
                "error": f"Circuit breaker OPEN. Waiting {CIRCUIT_RECOVERY_INTERVAL}s before retry.",
                "last_error": stats.error_message
            }, indent=2)
    
    # Parse body if provided
    parsed_body = None
    if body:
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "Invalid JSON body provided"
            }, indent=2)
    
    # Make the request
    result = await _try_endpoint(stats, method, parsed_body, timeout, retries)
    
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_endpoint_status(url: str) -> str:
    """
    Get the current circuit breaker status for an endpoint.
    
    Args:
        url: The endpoint URL to check
    
    Returns:
        JSON string with circuit state, failure count, and health metrics
    """
    
    if url not in _endpoints:
        return json.dumps({
            "url": url,
            "known": False,
            "message": "Endpoint has not been called yet"
        }, indent=2)
    
    stats = _endpoints[url]
    
    now = time.time()
    time_since_failure = round(now - stats.last_failure_time, 1) if stats.last_failure_time else None
    time_since_success = round(now - stats.last_success_time, 1) if stats.last_success_time else None
    
    return json.dumps({
        "url": url,
        "known": True,
        "circuit_state": stats.state.value,
        "consecutive_failures": stats.consecutive_failures,
        "total_failures": stats.failures,
        "total_successes": stats.successes,
        "last_failure_ago_sec": time_since_failure,
        "last_success_ago_sec": time_since_success,
        "avg_response_time_ms": round(stats.avg_response_time * 1000, 2),
        "has_cached_data": stats.cached_response is not None,
        "error_message": stats.error_message,
        "recovery_interval_sec": CIRCUIT_RECOVERY_INTERVAL,
        "failure_threshold": CIRCUIT_FAILURE_THRESHOLD
    }, indent=2, default=str)


@mcp.tool()
async def reset_breaker(url: str) -> str:
    """
    Manually reset the circuit breaker for an endpoint.
    
    Args:
        url: The endpoint URL to reset
    
    Returns:
        JSON string confirming the reset
    """
    
    if url not in _endpoints:
        return json.dumps({
            "url": url,
            "reset": False,
            "message": "Endpoint not found in registry"
        }, indent=2)
    
    stats = _endpoints[url]
    old_state = stats.state.value
    
    stats.state = CircuitState.CLOSED
    stats.consecutive_failures = 0
    stats.recovery_timer = None
    stats.error_message = None
    
    logger.info(f"Circuit breaker manually reset for {url} (was {old_state})")
    
    return json.dumps({
        "url": url,
        "reset": True,
        "previous_state": old_state,
        "new_state": "closed",
        "message": "Circuit breaker reset successfully"
    }, indent=2)


@mcp.tool()
async def list_all_endpoints() -> str:
    """
    List all monitored endpoints and their circuit breaker states.
    
    Returns:
        JSON string with all endpoint statuses
    """
    
    results = []
    for url, stats in _endpoints.items():
        results.append({
            "url": url,
            "state": stats.state.value,
            "failures": stats.failures,
            "successes": stats.successes,
            "consecutive_failures": stats.consecutive_failures,
            "avg_response_time_ms": round(stats.avg_response_time * 1000, 2),
            "has_cache": stats.cached_response is not None
        })
    
    return json.dumps({
        "endpoints": results,
        "count": len(results)
    }, indent=2)


# ===================== HTTP HEALTH ENDPOINT =====================

async def health_handler(request):
    """HTTP handler for /health endpoint."""
    
    now = time.time()
    endpoints_health = []
    
    for url, stats in _endpoints.items():
        endpoints_health.append({
            "url": url,
            "state": stats.state.value,
            "healthy": stats.state == CircuitState.CLOSED,
            "consecutive_failures": stats.consecutive_failures,
            "total_failures": stats.failures,
            "total_successes": stats.successes,
            "avg_response_time_ms": round(stats.avg_response_time * 1000, 2),
            "has_cached_data": stats.cached_response is not None,
            "time_since_last_failure": round(now - stats.last_failure_time, 1) if stats.last_failure_time else None,
            "time_since_last_success": round(now - stats.last_success_time, 1) if stats.last_success_time else None
        })
    
    overall_healthy = all(e["healthy"] for e in endpoints_health) if endpoints_health else True
    
    return aiohttp.web.json_response({
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": time.time(),
        "total_endpoints": len(_endpoints),
        "healthy_endpoints": sum(1 for e in endpoints_health if e["healthy"]),
        "degraded_endpoints": sum(1 for e in endpoints_health if not e["healthy"]),
        "endpoints": endpoints_health
    })


async def index_handler(request):
    """Root endpoint with server info."""
    return aiohttp.web.json_response({
        "name": "Self-Healing API Executor MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "/": "This info",
            "/health": "Health check - returns status of all monitored endpoints",
            "/mcp/sse": "MCP SSE endpoint",
            "/mcp/messages": "MCP message endpoint"
        },
        "tools": [
            "call_api(url, method, body, timeout, retries, force)",
            "get_endpoint_status(url)",
            "reset_breaker(url)",
            "list_all_endpoints()"
        ]
    })


async def run_http_server(host="0.0.0.0", port=8765):
    """Run the HTTP server with health endpoint alongside MCP."""
    
    from aiohttp import web
    
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Health server running at http://{host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    
    return runner


# ===================== MAIN =====================

if __name__ == "__main__":
    import sys
    
    # Check dependencies
    try:
        import aiohttp
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install aiohttp mcp")
        sys.exit(1)
    
    # Run both HTTP server and MCP
    async def main():
        # Start health endpoint
        http_runner = await run_http_server(port=8765)
        
        logger.info("Self-Healing API Executor MCP Server starting...")
        logger.info("MCP server running via stdio transport")
        logger.info("Tools: call_api, get_endpoint_status, reset_breaker, list_all_endpoints")
        
        # Run MCP server (stdio transport)
        await mcp.run_stdio_async()
    
    asyncio.run(main())
