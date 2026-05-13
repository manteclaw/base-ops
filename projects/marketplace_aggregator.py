#!/usr/bin/env python3
"""
Cross-Marketplace Task Aggregator
Polls all active marketplaces for tasks/bounties/opportunities
Run: python3 projects/marketplace_aggregator.py
Cron: */30 * * * * cd /root/.openclaw/workspace && python3 projects/marketplace_aggregator.py >> /tmp/marketplace_aggregator.log 2>&1
"""

import asyncio
import json
import httpx
import os
from datetime import datetime

NOOKPLOT_API = os.getenv("NOOKPLOT_API_KEY", "os.environ.get("NOOKPLOT_API_KEY", "nk_...")")
NOOKPLOT_GATEWAY = "https://gateway.nookplot.com"
AGENT_ID = "3fbc58ec-1236-41d8-83a3-557f342adc3b"
STATE_FILE = "/root/.openclaw/workspace/projects/marketplace_aggregator_state.json"

async def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"tasks": {}, "last_run": 0}

async def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

async def poll_nookplot(client):
    """Poll Nookplot for open bounties"""
    try:
        r = await client.get(
            f"{NOOKPLOT_GATEWAY}/v1/bounties",
            headers={"Authorization": f"Bearer {NOOKPLOT_API}"},
            params={"status": "0", "limit": 50, "sort": "createdAt", "order": "desc"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            tasks = []
            for b in data.get("bounties", []):
                tasks.append({
                    "platform": "nookplot",
                    "id": f"nookplot-{b.get('id')}",
                    "title": b.get("title", "N/A"),
                    "reward": int(b.get("rewardAmount", 0)) / 1e18,
                    "reward_unit": "NOOK",
                    "deadline": None,
                    "competition": b.get("applicationCount", 0),
                    "url": f"https://nookplot.com/bounties/{b.get('id')}",
                    "match_score": 95 if b.get("applicationCount", 0) == 0 else 80,
                })
            return tasks
    except Exception as e:
        print(f"Nookplot error: {e}")
    return []

async def poll_0xwork(client):
    """Poll 0xWork for tasks"""
    try:
        # Check if there's an API or if we need to scrape
        # For now, placeholder based on known structure
        r = await client.get("https://api.0xwork.com/v1/tasks", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return [{
                "platform": "0xwork",
                "id": f"0xwork-{t.get('id')}",
                "title": t.get("title"),
                "reward": t.get("reward", 0),
                "reward_unit": t.get("currency", "ETH"),
                "deadline": t.get("deadline"),
                "competition": t.get("applicants", 0),
                "url": t.get("url"),
                "match_score": 70,
            } for t in data.get("tasks", [])]
    except:
        pass
    return []

async def poll_daydreams(client):
    """Poll Daydreams Taskmarket"""
    try:
        r = await client.get("https://market.daydreams.systems/api/v1/tasks", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return [{
                "platform": "daydreams",
                "id": f"daydreams-{t.get('id')}",
                "title": t.get("title"),
                "reward": t.get("reward", 0),
                "reward_unit": t.get("currency", "ETH"),
                "deadline": t.get("deadline"),
                "competition": t.get("applicants", 0),
                "url": t.get("url"),
                "match_score": 75,
            } for t in data.get("tasks", [])]
    except:
        pass
    return []

async def main():
    state = await load_state()
    new_tasks = []
    
    async with httpx.AsyncClient() as client:
        # Poll all marketplaces concurrently
        results = await asyncio.gather(
            poll_nookplot(client),
            poll_0xwork(client),
            poll_daydreams(client),
            return_exceptions=True,
        )
        
        for result in results:
            if isinstance(result, list):
                for task in result:
                    tid = task["id"]
                    if tid not in state["tasks"]:
                        state["tasks"][tid] = task
                        state["tasks"][tid]["discovered"] = datetime.now().isoformat()
                        new_tasks.append(task)
    
    state["last_run"] = int(datetime.now().timestamp())
    await save_state(state)
    
    # Output
    print(f"[{datetime.now().isoformat()}] Marketplace Scan Complete")
    print(f"  Total tracked: {len(state['tasks'])}")
    print(f"  New today: {len(new_tasks)}")
    
    if new_tasks:
        print("\n  🔥 NEW OPPORTUNITIES:")
        # Sort by match score
        for t in sorted(new_tasks, key=lambda x: x["match_score"], reverse=True)[:10]:
            print(f"    [{t['platform'].upper()}] {t['title'][:50]}... | {t['reward']:,.0f} {t['reward_unit']} | competition={t['competition']} | match={t['match_score']}")
    
    # Summary table
    print("\n  📊 ALL ACTIVE TASKS:")
    active = [t for t in state["tasks"].values()]
    for t in sorted(active, key=lambda x: x.get("match_score", 0), reverse=True)[:15]:
        print(f"    {t['platform']:12} | {t['title'][:40]:40} | {t['reward']:>8.0f} {t['reward_unit']:6} | apps={t['competition']:>3} | match={t['match_score']:>3}")

if __name__ == "__main__":
    asyncio.run(main())
