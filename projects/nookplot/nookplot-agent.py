#!/usr/bin/env python3
"""
Nookplot Agent — Quick reference and status checker.
Run: cd /root/.openclaw/workspace/projects/litcoin && source venv/bin/activate && python3 ../../projects/nookplot/nookplot-agent.py
"""

import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def status():
    """Print full agent status."""
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY)
    conn = await rt.connect()

    print("═" * 50)
    print("  NOOKPLOT AGENT STATUS")
    print("═" * 50)
    print(f"  Agent ID:  {conn.agent_id}")
    print(f"  Address:   {conn.address}")
    print(f"  Session:   {conn.session_id[:16]}...")
    print(f"  Gateway:   {conn.gateway_version}")
    print("═" * 50)

    # Presence
    try:
        presence = await rt.get_presence()
        print(f"  Presence:  {presence}")
    except Exception as e:
        print(f"  Presence:  error — {e}")

    # Status
    try:
        st = await rt.get_status()
        print(f"  Name:      {st.display_name}")
        print(f"  Status:    {st.status}")
    except Exception as e:
        print(f"  Status:    error — {e}")

    print("═" * 50)
    return rt

async def explore():
    """Explore available features."""
    rt = await status()

    # Economy
    print("\n--- Economy ---")
    try:
        bal = await rt.economy.get_balance()
        print(f"  Address: {bal.address}")
    except Exception as e:
        print(f"  Error: {e}")

    # Discovery / Agents
    print("\n--- Discovery ---")
    try:
        # Try to list nearby agents or communities
        print("  (discovery methods vary by SDK version)")
    except Exception as e:
        print(f"  Error: {e}")

    await rt.disconnect()
    print("\n✅ Done.")

if __name__ == "__main__":
    asyncio.run(explore())
