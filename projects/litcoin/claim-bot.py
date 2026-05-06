#!/usr/bin/env python3
"""
Litcoiin Auto-Claim Bot
Monitors balance and auto-claims when ≥ 50,000 LITCOIN
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

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d_%H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_balance():
    """Check LITCOIN balance via Bankr API or SDK"""
    try:
        # Try using the litcoin SDK
        result = subprocess.run(
            [sys.executable, "-c", f"""
import os
os.environ['BANKR_API_KEY'] = '{BANKR_KEY}'
from litcoin import Agent
agent = Agent(bankr_key='{BANKR_KEY}')
status = agent.status()
print(json.dumps(status))
"""],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            return data.get("balance", 0)
    except Exception as e:
        log(f"Balance check error: {e}")
    return 0

def claim():
    """Claim LITCOIN rewards"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"""
import os
os.environ['BANKR_API_KEY'] = '{BANKR_KEY}'
from litcoin import Agent
agent = Agent(bankr_key='{BANKR_KEY}')
result = agent.claim()
print(json.dumps(result))
"""],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            log(f"CLAIM SUCCESS: {data}")
            return True
        else:
            log(f"CLAIM FAILED: {result.stderr}")
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
            log("Claim failed - will retry")
    else:
        remaining = CLAIM_THRESHOLD - balance
        log(f"Need {remaining:,} more LITCOIN to claim")
    
    # Save state
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    log("=== Done ===\n")

if __name__ == "__main__":
    main()
