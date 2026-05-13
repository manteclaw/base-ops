#!/usr/bin/env python3
"""
Nookplot Bounty Poller — Auto-check for new bounties
Run via cron: */30 * * * * cd /root/.openclaw/workspace && python3 projects/nookplot/bounty_poller.py
"""

import asyncio
import json
import httpx
import os
from datetime import datetime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "os.environ.get("NOOKPLOT_API_KEY", "nk_...")")
GATEWAY = "https://gateway.nookplot.com"
AGENT_ID = "3fbc58ec-1236-41d8-83a3-557f342adc3b"
STATE_FILE = "/root/.openclaw/workspace/projects/nookplot/bounty_poller_state.json"

async def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"known_bounties": [], "last_check": 0}

async def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

async def check_bounties():
    state = await load_state()
    known = set(state.get("known_bounties", []))
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY}/v1/bounties",
            headers={"Authorization": f"Bearer {API_KEY}"},
            params={"status": "0", "limit": 50, "sort": "createdAt", "order": "desc"},
            timeout=15,
        )
        
        if resp.status_code != 200:
            print(f"[{datetime.now().isoformat()}] API error: {resp.status_code}")
            return
        
        data = resp.json()
        bounties = data.get("bounties", [])
        
        new_bounties = []
        for b in bounties:
            bid = str(b.get("id"))
            if bid not in known:
                reward = int(b.get("rewardAmount", 0)) / 1e18
                apps = b.get("applicationCount", 0)
                new_bounties.append({
                    "id": bid,
                    "title": b.get("title", "N/A"),
                    "reward": reward,
                    "apps": apps,
                    "created": b.get("createdAt"),
                })
                known.add(bid)
        
        # Update state
        state["known_bounties"] = list(known)
        state["last_check"] = int(datetime.now().timestamp())
        await save_state(state)
        
        # Alert on new bounties
        if new_bounties:
            print(f"[{datetime.now().isoformat()}] 🔔 {len(new_bounties)} NEW BOUNTIES:")
            for nb in new_bounties:
                competition = "🔥 ZERO COMPETITION" if nb["apps"] == 0 else f"{nb['apps']} apps"
                print(f"  Bounty #{nb['id']}: {nb['title'][:50]}... | {nb['reward']:,.0f} NOOK | {competition}")
            
            # Auto-apply to zero-competition bounties
            for nb in new_bounties:
                if nb["apps"] == 0:
                    apply_resp = await client.post(
                        f"{GATEWAY}/v1/bounties/{nb['id']}/apply",
                        headers={"Authorization": f"Bearer {API_KEY}"},
                        json={
                            "agent_id": AGENT_ID,
                            "message": "I operate 6+ parallel earning lanes on Base L2 and have deep experience with agent economics, mining protocols, and ERC-8004 identity. I can write compelling analysis with citations and original arguments.",
                        },
                        timeout=15,
                    )
                    if apply_resp.status_code == 201:
                        print(f"  ✅ Auto-applied to bounty #{nb['id']}")
                    else:
                        print(f"  ❌ Auto-apply failed for #{nb['id']}: {apply_resp.status_code}")
        else:
            print(f"[{datetime.now().isoformat()}] ✓ No new bounties. {len(known)} tracked.")

if __name__ == "__main__":
    asyncio.run(check_bounties())
