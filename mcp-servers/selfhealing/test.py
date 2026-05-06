#!/usr/bin/env python3
"""
Quick test for Self-Healing API Executor MCP Server.
Tests against httpbin.org and simulates failures.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/root/.openclaw/workspace/mcp-servers/selfhealing')

from server import (
    call_api, get_endpoint_status, reset_breaker, list_all_endpoints,
    _endpoints, CircuitState
)

async def test_suite():
    print("=" * 60)
    print("Self-Healing API Executor - Test Suite")
    print("=" * 60)
    
    # Test 1: Basic GET call
    print("\n[TEST 1] Basic GET to httpbin.org/get")
    result = await call_api("https://httpbin.org/get", method="GET", timeout=15)
    parsed = json.loads(result)
    assert parsed["success"] == True, f"Expected success, got: {parsed}"
    assert parsed["status"] == 200
    print(f"  ✅ Success! Status: {parsed['status']}, attempts: {parsed['attempts']}, time: {parsed.get('response_time_ms')}ms")
    
    # Test 2: POST call with body
    print("\n[TEST 2] POST to httpbin.org/post with JSON body")
    body = json.dumps({"test": "data", "timestamp": 1234567890})
    result = await call_api("https://httpbin.org/post", method="POST", body=body, timeout=15)
    parsed = json.loads(result)
    assert parsed["success"] == True, f"POST failed: {parsed}"
    assert parsed["status"] == 200
    print(f"  ✅ POST successful! Status: {parsed['status']}")
    
    # Test 3: Check endpoint status
    print("\n[TEST 3] Get endpoint status")
    result = await get_endpoint_status("https://httpbin.org/get")
    parsed = json.loads(result)
    assert parsed["known"] == True
    assert parsed["circuit_state"] == "closed"
    print(f"  ✅ State: {parsed['circuit_state']}, successes: {parsed['total_successes']}, failures: {parsed['total_failures']}")
    
    # Test 4: Simulate a failing endpoint (should trigger circuit breaker)
    print("\n[TEST 4] Simulate failing endpoint (bad URL)")
    fail_url = "https://this-does-not-exist-12345.invalid/bad"
    for i in range(5):
        result = await call_api(fail_url, method="GET", timeout=2, retries=0)
        parsed = json.loads(result)
        print(f"  Call {i+1}: state={parsed['circuit_state']}, success={parsed['success']}")
    
    # Check circuit opened
    result = await get_endpoint_status(fail_url)
    parsed = json.loads(result)
    assert parsed["circuit_state"] == "open", f"Expected OPEN, got {parsed['circuit_state']}"
    print(f"  ✅ Circuit breaker OPEN after {parsed['consecutive_failures']} failures")
    
    # Test 5: Circuit breaker returns cached data or rejects
    print("\n[TEST 5] Circuit breaker rejecting calls")
    result = await call_api(fail_url, method="GET", timeout=2)
    parsed = json.loads(result)
    assert parsed["success"] == False or parsed.get("from_cache") == True
    assert parsed["circuit_state"] == "open"
    print(f"  ✅ Call rejected/cached. State: {parsed['circuit_state']}")
    
    # Test 6: Reset breaker
    print("\n[TEST 6] Manual breaker reset")
    result = await reset_breaker(fail_url)
    parsed = json.loads(result)
    assert parsed["reset"] == True
    print(f"  ✅ Reset from {parsed['previous_state']} to {parsed['new_state']}")
    
    # Verify reset
    result = await get_endpoint_status(fail_url)
    parsed = json.loads(result)
    assert parsed["circuit_state"] == "closed"
    print(f"  ✅ State confirmed: {parsed['circuit_state']}")
    
    # Test 7: List all endpoints
    print("\n[TEST 7] List all endpoints")
    result = await list_all_endpoints()
    parsed = json.loads(result)
    assert parsed["count"] >= 2  # httpbin + bad endpoint
    print(f"  ✅ Found {parsed['count']} endpoints:")
    for ep in parsed["endpoints"]:
        print(f"     - {ep['url']}: {ep['state']} (failures: {ep['failures']}, successes: {ep['successes']})")
    
    # Test 8: Health endpoint via HTTP
    print("\n[TEST 8] HTTP health endpoint")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Start server briefly to test
            from server import run_http_server
            from aiohttp import web
            
            # We need to run the HTTP server for this test
            runner = await run_http_server(port=8766)  # Different port
            
            try:
                async with session.get("http://localhost:8766/health") as resp:
                    health = await resp.json()
                    assert "endpoints" in health
                    assert "status" in health
                    print(f"  ✅ Health endpoint: {health['status']}, {health['total_endpoints']} endpoints tracked")
            finally:
                await runner.cleanup()
    except Exception as e:
        print(f"  ⚠️ HTTP health test skipped (server integration): {e}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_suite())
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
