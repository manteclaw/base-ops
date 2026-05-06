import os
import sys
import json
import time
import random
import requests
from datetime import datetime

# ─── CONFIG ───
BANKR_API_KEY = os.environ.get("BANKR_API_KEY", "")
if not BANKR_API_KEY:
    raise ValueError("BANKR_API_KEY environment variable required")
COORDINATOR_URL = os.environ.get("COORDINATOR_URL", "https://coordinator.agentmoney.net")
MINER_ADDRESS = "0x550c0cec65c9e585a0e59164f147a350e75a7a56"
TOKEN_ADDRESS = "0xA601877977340862Ca67f816eb079958E5bd0BA3"
STAKE_CONTRACT = "0xB2fbe0DB5A99B4E2Dd294dE64cEd82740b53A2Ea"
MIN_STAKE = 5_000_000  # whole tokens

# ─── STATE ───
auth_token = None
token_expiry = 0

def bankr_get(path, headers=None):
    url = f"https://api.bankr.bot{path}"
    h = {"X-API-Key": BANKR_API_KEY}
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, timeout=30)
    r.raise_for_status()
    return r.json()

def bankr_post(path, data, headers=None):
    url = f"https://api.bankr.bot{path}"
    h = {"Content-Type": "application/json", "X-API-Key": BANKR_API_KEY}
    if headers:
        h.update(headers)
    r = requests.post(url, json=data, headers=h, timeout=60)
    r.raise_for_status()
    return r.json()

def coordinator_get(path, params=None, auth=True):
    url = f"{COORDINATOR_URL}{path}"
    h = {}
    if auth and auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    r = requests.get(url, params=params, headers=h, timeout=30)
    if r.status_code == 401:
        print("[AUTH] Token expired, re-authenticating...")
        do_auth()
        return coordinator_get(path, params, auth)
    r.raise_for_status()
    return r.json()

def coordinator_post(path, data, auth=True):
    url = f"{COORDINATOR_URL}{path}"
    h = {"Content-Type": "application/json"}
    if auth and auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    r = requests.post(url, json=data, headers=h, timeout=60)
    if r.status_code == 401:
        print("[AUTH] Token expired, re-authenticating...")
        do_auth()
        return coordinator_post(path, data, auth)
    r.raise_for_status()
    return r.json()

def do_auth():
    global auth_token, token_expiry
    print("[AUTH] Starting auth handshake...")
    nonce_resp = coordinator_post("/v1/auth/nonce", {"miner": MINER_ADDRESS}, auth=False)
    message = nonce_resp.get("message")
    if not message:
        raise RuntimeError(f"Auth nonce failed: {nonce_resp}")
    
    sign_resp = bankr_post("/agent/sign", {
        "signatureType": "personal_sign",
        "message": message
    })
    signature = sign_resp.get("signature")
    if not signature:
        raise RuntimeError(f"Bankr sign failed: {sign_resp}")
    
    verify_resp = coordinator_post("/v1/auth/verify", {
        "miner": MINER_ADDRESS,
        "message": message,
        "signature": signature
    }, auth=False)
    token = verify_resp.get("token")
    if not token:
        raise RuntimeError(f"Auth verify failed: {verify_resp}")
    
    auth_token = token
    token_expiry = time.time() + 3600  # assume 1h validity
    print(f"[AUTH] Token acquired, expires ~{datetime.fromtimestamp(token_expiry)}")
    return token

def check_stake():
    """Check staked BOTCOIN on mining contract."""
    # We can query the stake contract directly via eth_call
    # stakeOf(address) selector = 0x5fe9be8d
    padded = MINER_ADDRESS.replace("0x", "").zfill(64)
    data = "0x5fe9be8d" + padded
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": STAKE_CONTRACT, "data": data}, "latest"],
        "id": 1
    }
    r = requests.post("https://mainnet.base.org", json=payload, timeout=10)
    result = r.json().get("result", "0x0")
    staked = int(result, 16) / 1e18
    return staked

def check_botcoin_balance():
    padded = MINER_ADDRESS.replace("0x", "").zfill(64)
    data = "0x70a08231" + padded
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": TOKEN_ADDRESS, "data": data}, "latest"],
        "id": 1
    }
    r = requests.post("https://mainnet.base.org", json=payload, timeout=10)
    result = r.json().get("result", "0x0")
    return int(result, 16) / 1e18

def stake_botcoin(amount_tokens):
    """Stake BOTCOIN. amount in whole tokens."""
    amount_wei = int(amount_tokens * 1e18)
    # Step 1: approve
    approve_resp = coordinator_get(f"/v1/stake-approve-calldata?amount={amount_wei}", auth=False)
    tx1 = approve_resp["transaction"]
    print("[STAKE] Submitting approve tx...")
    bankr_post("/agent/submit", {
        "transaction": tx1,
        "description": "Approve BOTCOIN for staking",
        "waitForConfirmation": True
    })
    
    # Step 2: stake
    stake_resp = coordinator_get(f"/v1/stake-calldata?amount={amount_wei}", auth=False)
    tx2 = stake_resp["transaction"]
    print("[STAKE] Submitting stake tx...")
    bankr_post("/agent/submit", {
        "transaction": tx2,
        "description": "Stake BOTCOIN for mining",
        "waitForConfirmation": True
    })
    print(f"[STAKE] {amount_tokens:,.0f} BOTCOIN staked.")

def mine_one():
    """Request, solve, and submit one challenge."""
    nonce = "%032x" % random.getrandbits(128)
    print(f"[MINE] Requesting challenge with nonce {nonce[:16]}...")
    
    challenge = coordinator_get("/v1/challenge", params={
        "miner": MINER_ADDRESS,
        "nonce": nonce
    })
    
    challenge_id = challenge["challengeId"]
    epoch_id = challenge["epochId"]
    credits = challenge.get("creditsPerSolve", 0)
    print(f"[MINE] Challenge {challenge_id} | Epoch {epoch_id} | Credits: {credits}")
    
    # TODO: implement LLM solve logic here
    # For now, placeholder
    artifact = "placeholder_artifact"
    reasoning_trace = []
    
    submit_payload = {
        "miner": MINER_ADDRESS,
        "challengeId": challenge_id,
        "artifact": artifact,
        "nonce": nonce,
        "challengeManifestHash": challenge.get("challengeManifestHash", ""),
        "modelVersion": "botcoin-miner-v1",
        "reasoningTrace": reasoning_trace
    }
    
    result = coordinator_post("/v1/submit", submit_payload)
    print(f"[MINE] Submit result: pass={result.get('pass')}")
    
    if result.get("pass"):
        receipt_tx = result["transaction"]
        vouch_tx = result.get("vouchTransaction")
        print("[MINE] Posting receipt on-chain...")
        bankr_post("/agent/submit", {
            "transaction": receipt_tx,
            "description": "Post BOTCOIN mining receipt",
            "waitForConfirmation": True
        })
        if vouch_tx:
            bankr_post("/agent/submit", {
                "transaction": vouch_tx,
                "description": "BOTCOIN 8004 vouch",
                "waitForConfirmation": False
            })
    return result

def main():
    print("=" * 60)
    print("BOTCOIN Miner v1 — Parallel Lane")
    print(f"Wallet: {MINER_ADDRESS}")
    print("=" * 60)
    
    # Check balances
    botcoin_bal = check_botcoin_balance()
    staked = check_stake()
    print(f"[BAL] BOTCOIN balance: {botcoin_bal:,.2f}")
    print(f"[BAL] BOTCOIN staked:  {staked:,.2f}")
    
    if staked < MIN_STAKE:
        print(f"[BLOCKED] Need {MIN_STAKE:,.0f} BOTCOIN staked. Current: {staked:,.2f}")
        print(f"[BLOCKED] Buy ~{MIN_STAKE - botcoin_bal:,.0f} BOTCOIN and stake.")
        return 1
    
    # Auth
    do_auth()
    
    # Mining loop
    while True:
        try:
            mine_one()
        except Exception as e:
            print(f"[ERR] {e}")
            time.sleep(30)
        time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    sys.exit(main())
