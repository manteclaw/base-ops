#!/usr/bin/env python3
"""
Nookplot Auto-Bounty Pipeline
When bounty application is APPROVED, auto-submit deliverable.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime

API_KEY = os.getenv("NOOKPLOT_API_KEY", "nk_IZgHP2Ni-bwc4-0UgVIJmfwCCrvVhoAfccWWHt8RkAV4e2Ko9Mv9mUbve_iQo9eD")
GATEWAY = "https://gateway.nookplot.com"
AGENT_ID = "3fbc58ec-1236-41d8-83a3-557f342adc3b"

# Bounty ID -> Deliverable file mapping
DELIVERABLES = {
    38: "/root/.openclaw/workspace/projects/nookplot/bounty_38_deliverable.md",
    40: "/root/.openclaw/workspace/projects/nookplot/bounty_40_deliverable.md",
    43: "/root/.openclaw/workspace/projects/nookplot/bounty_43_deliverable.md",
    44: "/root/.openclaw/workspace/projects/nookplot/bounty_44_deliverable.md",
    46: "/root/.openclaw/workspace/projects/nookplot/bounty_46_deliverable.md",
    47: "/root/.openclaw/workspace/projects/nookplot/bounty_47_deliverable.md",
    48: "/root/.openclaw/workspace/projects/nookplot/bounty_48_deliverable.md",
    49: "/root/.openclaw/workspace/projects/nookplot/bounty_49_deliverable.md",
    50: "/root/.openclaw/workspace/projects/nookplot/bounty_50_deliverable.md",
}

async def check_and_submit():
    """Check for approved bounties and auto-submit deliverables."""
    async with httpx.AsyncClient() as client:
        for bounty_id, deliverable_path in DELIVERABLES.items():
            # Check application status
            r = await client.get(
                f"{GATEWAY}/v1/bounties/{bounty_id}/applications",
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=15,
            )
            if r.status_code != 200:
                continue
                
            apps = r.json().get("applications", [])
            my_app = [a for a in apps if a.get("agent", {}).get("id") == AGENT_ID]
            
            if not my_app:
                continue
                
            status = my_app[0].get("status")
            app_id = my_app[0].get("id")
            
            if status == "approved":
                print(f"[{datetime.now().isoformat()}] 🔔 Bounty #{bounty_id} APPROVED!")
                
                # Load deliverable
                try:
                    with open(deliverable_path) as f:
                        deliverable = f.read()
                except FileNotFoundError:
                    print(f"  ❌ Deliverable file not found: {deliverable_path}")
                    continue
                
                # Step 1: Claim via gasless meta-transaction
                # This requires EIP-712 signing — we'll document the flow
                print(f"  ⏳ Claim step requires gasless meta-transaction (EIP-712)")
                print(f"  ⏳ Submit step requires deliverable upload")
                
                # For now, alert only — full automation needs private key
                print(f"  ⚠️  FULL AUTO-SUBMIT NEEDS: prepare + sign + relay EIP-712 + submit")
                print(f"     Deliverable ready: {deliverable_path} ({len(deliverable)} chars)")
                
            elif status == "pending":
                print(f"[{datetime.now().isoformat()}] ⏳ Bounty #{bounty_id} still pending")
            elif status == "rejected":
                print(f"[{datetime.now().isoformat()}] ❌ Bounty #{bounty_id} rejected")

if __name__ == "__main__":
    asyncio.run(check_and_submit())
