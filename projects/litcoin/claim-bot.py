#!/usr/bin/env python3
"""
Litcoiin Auto-Claim Bot
Monitors balance and auto-claims when ≥ 50,000 LITCOIN
Uses .keys/.env for credentials — never hardcodes secrets.
"""

import os
import sys
import json
import time
import subprocess

BANKR_KEY = os.environ.get("BANKR_API_KEY", "")
if not BANKR_KEY:
    raise ValueError("BANKR_API_KEY environment variable required")

CLAIM_THRESHOLD = 50000
LOG_FILE = "/root/.openclaw/workspace/projects/litcoin/claim-bot.log"
STATE_FILE = "/root/.openclaw/workspace/projects/litcoin/claim-state.json"

# New wallet (post-compromise)
WALLET_ADDRESS = "0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C"

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d_%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_balance():
    """Check LITCOIN balance via Bankr API"""
    try:
        import requests
        # Try Bankr API balance endpoint
        headers = {"Authorization": f"Bearer {BANKR_KEY}"}
        
        # First try the direct status endpoint
        result = subprocess.run(
            [sys.executable, "-c", f"""
import requests, json
headers = {{"Authorization": "Bearer {BANKR_KEY}"}}
# Try Bankr agent status endpoint
resp = requests.get("https://bankr-bot-production.up.railway.app/v1/agent/status", headers=headers, timeout=15)
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps(data))
else:
    print(json.dumps({{"error": f"HTTP {{resp.status_code}}", "balance": 0}}))
"""],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            balance = data.get("balance", 0)
            if not balance and "litcoiin" in str(data).lower():
                # Extract from nested structure
                pass
            return balance
    except Exception as e:
        log(f"Balance check error: {e}")
    return 0

def claim():
    """Claim LITCOIN rewards via Bankr API"""
    try:
        import requests
        headers = {"Authorization": f"Bearer {BANKR_KEY}"}
        
        # Try claim endpoint
        resp = requests.post(
            "https://bankr-bot-production.up.railway.app/v1/agent/claim",
            headers=headers,
            json={"all": True},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            log(f"CLAIM SUCCESS: {data}")
            return True
        else:
            log(f"CLAIM FAILED: HTTP {resp.status_code} - {resp.text[:200]}")
            
        # Fallback: try alternative endpoints
        for endpoint in [
            "/v1/claim",
            "/v1/rewards/claim",
            "/v1/mining/claim"
        ]:
            try:
                resp = requests.post(
                    f"https://bankr-bot-production.up.railway.app{endpoint}",
                    headers=headers,
                    timeout=10
                )
                if resp.status_code == 200:
                    log(f"Claim via {endpoint}: SUCCESS")
                    return True
            except:
                continue
                
    except Exception as e:
        log(f"Claim error: {e}")
    return False

def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except:
            pass
    
    log("=== Litcoiin Auto-Claim Bot Started ===")
    log(f"Wallet: {WALLET_ADDRESS}")
    log(f"Threshold: {CLAIM_THRESHOLD:,} LITCOIN")
    
    balance = get_balance()
    log(f"Current balance: {balance:,} LITCOIN")
    
    if balance >= CLAIM_THRESHOLD:
        log(f"THRESHOLD REACHED! Claiming {balance:,} LITCOIN...")
        if claim():
            state["last_claim"] = time.time()
            state["last_amount"] = balance
            log("Claim successful!")
        else:
            log("Claim failed - will retry next cycle")
    else:
        remaining = CLAIM_THRESHOLD - balance
        log(f"Need {remaining:,} more LITCOIN to claim")
    
    # Save state
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    log("=== Done ===\n")

if __name__ == "__main__":
    main()
