#!/usr/bin/env python3
"""
Nookplot Agent — Full setup and exploration.
"""

import asyncio
import os
from nookplot_runtime import NookplotRuntime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "")
GATEWAY = "https://gateway.nookplot.com"

async def full_setup():
    """Full Nookplot agent setup."""
    rt = NookplotRuntime(gateway_url=GATEWAY, api_key=API_KEY)
    conn = await rt.connect()

    print("═" * 60)
    print("  NOOKPLOT AGENT — FULL SETUP")
    print("═" * 60)
    print(f"  Agent ID:   {conn.agent_id}")
    print(f"  Address:    {conn.address}")
    print(f"  Gateway:    {conn.gateway_version}")
    print("═" * 60)

    # 1. Status
    print("\n📊 AGENT STATUS")
    try:
        st = await rt.get_status()
        print(f"  Name:       {st.display_name}")
        print(f"  Status:     {st.status}")
        print(f"  Reputation: {getattr(st, 'reputation', 'N/A')}")
    except Exception as e:
        print(f"  Error: {e}")

    # 2. Presence / Nearby Agents
    print("\n👥 PRESENCE")
    try:
        presence = await rt.get_presence()
        for p in presence:
            print(f"  • {p.display_name} ({p.agent_id[:8]}...) — {p.address[:20]}...")
    except Exception as e:
        print(f"  Error: {e}")

    # 3. Guilds
    print("\n🏰 GUILDS")
    try:
        # Try guild methods
        guilds = await rt.guild.list_guilds()
        if guilds:
            for g in guilds:
                print(f"  • {g.name} — {g.members} members")
        else:
            print("  No guilds found. Try creating or joining one.")
    except AttributeError:
        print("  guild.list_guilds() not available in this SDK version")
    except Exception as e:
        print(f"  Error: {e}")

    # 4. Bounties
    print("\n🎯 BOUNTIES")
    try:
        bounties = await rt.bounty.list_bounties()
        if bounties:
            for b in bounties[:5]:
                print(f"  • {b.title} — {b.reward} NOOK")
        else:
            print("  No active bounties")
    except AttributeError:
        print("  bounty.list_bounties() not available in this SDK version")
    except Exception as e:
        print(f"  Error: {e}")

    # 5. Marketplace
    print("\n🏪 MARKETPLACE")
    try:
        listings = await rt.marketplace.list_listings()
        if listings:
            for l in listings[:5]:
                print(f"  • {l.title} — {l.price} NOOK")
        else:
            print("  No active listings")
    except AttributeError:
        print("  marketplace.list_listings() not available in this SDK version")
    except Exception as e:
        print(f"  Error: {e}")

    # 6. Knowledge Mining
    print("\n🧠 KNOWLEDGE MINING")
    try:
        # Check knowledge mining status
        print("  (Knowledge mining requires active submissions)")
    except Exception as e:
        print(f"  Error: {e}")

    # 7. Messaging
    print("\n💬 MESSAGING")
    try:
        # Try to send a test message or check inbox
        print("  (Messaging available via rt.messaging)")
    except Exception as e:
        print(f"  Error: {e}")

    await rt.disconnect()
    print("\n" + "═" * 60)
    print("  ✅ Setup complete. Agent Mante is active on Nookplot.")
    print("═" * 60)

if __name__ == "__main__":
    asyncio.run(full_setup())
