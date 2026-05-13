#!/usr/bin/env python3
"""Retry verify + claim with existing nonce"""

import json
import requests
import time
from eth_account import Account
from eth_account.messages import encode_defunct

API_BASE = "https://coordinator.agentmoney.net"
DOMAIN = "agentmoney.net"
CHAIN_ID = 8453
AGENT_ID = 46833
ADDRESS = "0xe8663112edafacaef5711d49e42a11d37023fa32"
REGISTRY = "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
PRIVATE_KEY = "0xa3b064d1104984e489a824b20971c5ee1b1a8eceabd8465d61900353c5d772ab"

# Valid nonce from Attempt 4
NONCE_DATA = {
    "nonce": "jZzbq8eQ09H5u_Ls",
    "issuedAt": "2026-05-13T22:56:56.557Z",
    "expirationTime": "2026-05-13T23:01:56.557Z",
    "nonceToken": "eyJub25jZSI6ImpaemJxOGVRMDlINXVfTHMiLCJhZGRyZXNzIjoiMHhlODY2MzExMmVkYWZhY2FlZjU3MTFkNDllNDJhMTFkMzcwMjNmYTMyIiwiYWdlbnRJZCI6NDY4MzMsImlhdCI6MTc3ODcxMzQxNjU1NywiZXhwIjoxNzc4NzEzNjE2NTU3fQ.YflGIiKU7eKuwNnV1YJIEJNtXLnD5yOluUOpmB5FTeE"
}

def sign_and_verify(nonce_data):
    message_lines = [
        f"{DOMAIN} wants you to sign in with your Agent account:",
        ADDRESS, "",
        "Sign in to the BOTCOIN Faucet to claim your drip.", "",
        f"URI: https://{DOMAIN}/faucet",
        "Version: 1",
        f"Agent ID: {AGENT_ID}",
        f"Agent Registry: {REGISTRY}",
        f"Chain ID: {CHAIN_ID}",
        f"Nonce: {nonce_data['nonce']}",
        f"Issued At: {nonce_data['issuedAt']}",
    ]
    if nonce_data.get("expirationTime"):
        message_lines.append(f"Expiration Time: {nonce_data['expirationTime']}")
    message = "\n".join(message_lines)
    
    encoded = encode_defunct(text=message)
    account = Account.from_key(PRIVATE_KEY)
    signed = account.sign_message(encoded)
    signature = signed.signature.hex()
    
    url = f"{API_BASE}/faucet/verify"
    payload = {"message": message, "signature": signature, "nonceToken": nonce_data["nonceToken"]}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0

def claim_drip(receipt):
    url = f"{API_BASE}/faucet/claim"
    headers = {"Authorization": f"Bearer {receipt}"}
    try:
        resp = requests.post(url, headers=headers, timeout=30)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0

if __name__ == "__main__":
    print("=" * 60)
    print("Retrying verify + claim with valid nonce")
    print(f"Nonce: {NONCE_DATA['nonce']}")
    print(f"Expires: {NONCE_DATA['expirationTime']}")
    print("=" * 60)
    
    for attempt in range(1, 21):
        print(f"\n[Verify attempt {attempt}/20]")
        verify_result, status = sign_and_verify(NONCE_DATA)
        print(f"HTTP {status}: {str(verify_result)[:300]}")
        
        if status == 200 and verify_result.get("receipt"):
            receipt = verify_result["receipt"]
            print(f"✅ Verified! Receipt: {receipt[:30]}...")
            
            # Claim
            for claim_attempt in range(1, 11):
                print(f"\n[Claim attempt {claim_attempt}/10]")
                claim_result, status = claim_drip(receipt)
                print(f"HTTP {status}: {json.dumps(claim_result)[:500]}")
                
                if claim_result.get("status") == "success":
                    print("=" * 60)
                    print(f"🎉 SUCCESS! Claimed {claim_result.get('amount', '?')} BOTCOIN!")
                    print(f"   Tier: {claim_result.get('tierName', '?')}")
                    print(f"   TX: {claim_result.get('txHash', '?')}")
                    print("=" * 60)
                    exit(0)
                elif status == 429 or status == 503:
                    print(f"Server busy, retrying claim in 5s...")
                    time.sleep(5)
                else:
                    print(f"Claim failed: {claim_result.get('error', 'Unknown')}")
                    break
            break
        elif status == 429:
            print("Rate limited, waiting 5s...")
            time.sleep(5)
        elif status == 503:
            print("Server unavailable, waiting 3s...")
            time.sleep(3)
        else:
            print(f"Verify error: {verify_result.get('error', 'Unknown')}")
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("All retry attempts exhausted.")
    print("=" * 60)
