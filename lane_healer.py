#!/usr/bin/env python3
"""
Self-Healing Integration for Active Earning Lanes
Wraps all flaky external calls with auto-retry + circuit breaker.
Import this in any lane script to get resilience for free.
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')
from selfheal import (
    heal_litcoiin_call,
    heal_bankr_call,
    heal_nookplot_call,
    heal_0xwork_call,
    get_executor,
    retry,
    heal,
)

# ── Lane A: Litcoiin Mining ──

def safe_litcoiin_mine(agent, *args, **kwargs):
    """Mining step with retry on model rate limits / API flakes."""
    return heal_litcoiin_call(lambda: agent.mine(*args, **kwargs))

def safe_litcoiin_claim(agent, *args, **kwargs):
    """Claim with retry — don't lose rewards because of a 504."""
    return heal_bankr_call(lambda: agent.claim(*args, **kwargs))

# ── Lane B: Nookplot ──

def safe_nookplot_publish(runtime, content: str, *args, **kwargs):
    """Publish insight — 504s are Nookplot's favorite error."""
    return heal_nookplot_call(lambda: runtime.publish_insight(content, *args, **kwargs))

def safe_nookplot_apply_bounty(runtime, bounty_id: str, *args, **kwargs):
    """Bounty application — don't let a timeout cost you 5000 NOOK."""
    return heal_nookplot_call(lambda: runtime.apply_to_bounty(bounty_id, *args, **kwargs))

# ── Lane C: 0xWork ──

def safe_0xwork_discover(*args, **kwargs):
    """Task discovery with backoff."""
    return heal_0xwork_call(lambda: _discover(*args, **kwargs))

def safe_0xwork_submit(task_id: str, result, *args, **kwargs):
    """Task submission — retry if gateway times out."""
    return heal_0xwork_call(lambda: _submit(task_id, result, *args, **kwargs))

# ── Lane F: Zyfai / Bankr Treasury ──

def safe_zyfai_deposit(safe, amount, *args, **kwargs):
    """Yield deposit — only move money when the chain is responsive."""
    return heal_bankr_call(lambda: safe.deposit(amount, *args, **kwargs))

# ── Utility ──

def circuit_status() -> dict:
    """Health dashboard for all services."""
    return get_executor().status()

def reset_circuits(service: str = None):
    """Manual reset after known outages."""
    get_executor().reset(service)

if __name__ == "__main__":
    print("Self-healing integration loaded.")
    print("Circuit status:", circuit_status())
