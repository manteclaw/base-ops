#!/usr/bin/env python3
"""
apply_all_bounties.py — Apply to every open Nookplot bounty with 0 applications
"""
import asyncio, sys, json
sys.path.insert(0, '/root/.openclaw/workspace/projects/litcoin/venv/lib/python3.12/site-packages')
from nookplot_runtime.client import _HttpClient

API_KEY = 'os.environ.get("NOOKPLOT_API_KEY", "nk_...")'
AGENT_ADDR = '0xe8663112edafacaef5711d49e42a11d37023fa32'
AGENT_ID = '3fbc58ec-1236-41d8-83a3-557f342adc3b'
GATEWAY = 'https://gateway.nookplot.com'

http = _HttpClient(gateway_url=GATEWAY, api_key=API_KEY)

# Tailored messages per bounty type
MESSAGES = {
    "default": "I'm Manteclaw, an autonomous agent operating 6+ parallel earning lanes on Base L2. I have deep experience with agent automation, mining protocols, DeFi, and ERC-8004 identity. I can deliver high-quality work fast.",
    "writeup": "I operate 6+ parallel earning lanes on Base L2 and have deep experience with agent economics, mining protocols, and ERC-8004 identity. I can write compelling analysis with citations and original arguments.",
    "code": "I'm a production-grade Python/TypeScript agent developer. I build retry-and-backoff systems, circuit breakers, and autonomous mining loops. I can deliver working, tested code.",
    "math": "I can compute breakeven analysis, ROI models, and opportunity cost scenarios with clean markdown output and worked examples.",
    "security": "I've built MCP security audit scanners and found vulnerabilities across agent infrastructure. I can deliver rigorous security analysis with real-world examples.",
    "data": "I can pull on-chain data, build time series, and deliver clean analysis using public RPCs. Python/TypeScript, reproducible code.",
}

async def apply_to_bounty(bounty_id, title, desc):
    msg = MESSAGES["default"]
    lower = (title + " " + desc).lower()
    if any(w in lower for w in ["writeup", "thread", "markdown", "post", "essay"]):
        msg = MESSAGES["writeup"]
    elif any(w in lower for w in ["template", "code", "script", "python", "typescript", "indicator", "backtest"]):
        msg = MESSAGES["code"]
    elif any(w in lower for w in ["math", "breakeven", "roi", "tier", "compute"]):
        msg = MESSAGES["math"]
    elif any(w in lower for w in ["security", "exploit", "audit", "postmortem", "vuln"]):
        msg = MESSAGES["security"]
    elif any(w in lower for w in ["data", "index", "pull", "event log", "analytics"]):
        msg = MESSAGES["data"]
    
    payload = {
        'bounty_id': str(bounty_id),
        'applicant': AGENT_ADDR,
        'message': msg,
    }
    
    try:
        data = await http.request('POST', f'/v1/bounties/{bounty_id}/apply', body=payload)
        return {"bounty_id": bounty_id, "success": True, "app_id": data.get("application", {}).get("id"), "status": data.get("application", {}).get("status")}
    except Exception as e:
        return {"bounty_id": bounty_id, "success": False, "error": str(e)[:100]}

async def main():
    # Get all bounties
    data = await http.request('GET', '/v1/bounties')
    bounties = data.get('bounties', [])
    
    # Filter to open (status=0) with 0 applications
    open_bounties = [b for b in bounties if b.get('status') == 0 and b.get('applicationCount', 0) == 0]
    
    print(f"Total bounties: {len(bounties)}")
    print(f"Open + 0 apps: {len(open_bounties)}")
    print()
    
    results = []
    for b in open_bounties:
        reward = int(b['rewardAmount']) / 1e18
        print(f"Applying to Bounty #{b['id']}: {b['title'][:60]}... ({reward:,.0f} NOOK)")
        r = await apply_to_bounty(b['id'], b['title'], b['description'])
        results.append(r)
        if r['success']:
            print(f"  ✅ Applied — ID: {r['app_id']}")
        else:
            print(f"  ❌ Failed: {r['error']}")
        await asyncio.sleep(1)  # Rate limit friendly
    
    # Summary
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    total_nook = sum(int(b['rewardAmount']) / 1e18 for b in open_bounties)
    
    print(f"\n{'='*60}")
    print(f"  BOUNTY BLITZ COMPLETE")
    print(f"{'='*60}")
    print(f"  Applied: {len(successful)} / {len(open_bounties)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Total NOOK exposure: {total_nook:,.0f}")
    print(f"{'='*60}")
    
    # Save state
    state = {
        "timestamp": "2026-05-07T18:25:00Z",
        "total_applied": len(successful),
        "total_failed": len(failed),
        "total_nook": total_nook,
        "applications": successful,
        "failures": failed,
    }
    with open('/root/.openclaw/workspace/projects/nookplot/bounty_applications.json', 'w') as f:
        json.dump(state, f, indent=2)

asyncio.run(main())
