#!/usr/bin/env python3
"""Botcoin Faucet Claim Automation

Full pipeline: nonce -> captcha -> sign -> verify -> claim
"""

import json
import requests
import time
from eth_account import Account
from eth_account.messages import encode_defunct

# Agent credentials
AGENT_ID = 46833
ADDRESS = "0xe8663112edafacaef5711d49e42a11d37023fa32"
REGISTRY = "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
PRIVATE_KEY = "[REDACTED-private_key_hex]"

# API endpoints
API_BASE = "https://coordinator.agentmoney.net"
DOMAIN = "agentmoney.net"
CHAIN_ID = 8453

def ascii_sum(text):
    return sum(ord(c) for c in text)

def solve_captcha(challenge):
    """Find text that satisfies the captcha constraints."""
    target = challenge["asciiTarget"]
    line_count = challenge["lineCount"]
    topic = challenge["topic"]
    word_count_hint = challenge.get("wordCount", 0)
    
    newline_sum = (line_count - 1) * 10
    content_target = target - newline_sum
    
    print(f"[Captcha] Target: {target}, Lines: {line_count}, Content target: {content_target}")
    print(f"[Captcha] Topic: {topic}, Format: {challenge['format']}, Word hint: {word_count_hint}")
    
    # Try a greedy approach: build lines one by one
    import string
    chars = string.ascii_lowercase + ' '
    
    # Generate a pool of short lines
    lines_pool = []
    for length in range(1, 6):
        for c1 in chars:
            if length == 1:
                line = c1
                s = ord(c1)
                lines_pool.append((line, s))
            elif length == 2:
                for c2 in chars:
                    line = c1 + c2
                    s = ord(c1) + ord(c2)
                    lines_pool.append((line, s))
            elif length == 3:
                for c2 in chars:
                    for c3 in chars:
                        line = c1 + c2 + c3
                        s = ord(c1) + ord(c2) + ord(c3)
                        if s <= content_target:
                            lines_pool.append((line, s))
    
    # Deduplicate by sum for efficiency
    sum_to_lines = {}
    for line, s in lines_pool:
        if s not in sum_to_lines:
            sum_to_lines[s] = []
        sum_to_lines[s].append(line)
    
    sums = sorted(sum_to_lines.keys())
    
    # Find combination of line_count lines that sum to content_target
    if line_count == 3:
        for s1 in sums:
            for s2 in sums:
                s3 = content_target - s1 - s2
                if s3 in sum_to_lines and s3 > 0:
                    for l1 in sum_to_lines[s1]:
                        for l2 in sum_to_lines[s2]:
                            for l3 in sum_to_lines[s3]:
                                text = f"{l1}\n{l2}\n{l3}"
                                if ascii_sum(text) == target:
                                    return text
    elif line_count == 4:
        for s1 in sums:
            for s2 in sums:
                for s3 in sums:
                    s4 = content_target - s1 - s2 - s3
                    if s4 in sum_to_lines and s4 > 0:
                        for l1 in sum_to_lines[s1]:
                            for l2 in sum_to_lines[s2]:
                                for l3 in sum_to_lines[s3]:
                                    for l4 in sum_to_lines[s4]:
                                        text = f"{l1}\n{l2}\n{l3}\n{l4}"
                                        if ascii_sum(text) == target:
                                            return text
    
    return None

def request_nonce():
    """Step 1: Request a nonce from the faucet API."""
    url = f"{API_BASE}/faucet/nonce"
    payload = {
        "address": ADDRESS,
        "agentId": AGENT_ID,
        "agentRegistry": REGISTRY,
    }
    
    print(f"[Step 1] POST {url}")
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"[Step 1] HTTP {resp.status_code}")
        return resp.json()
    except Exception as e:
        print(f"[Step 1] Error: {e}")
        return {"error": str(e)}

def submit_captcha_solution(challenge_token, text):
    """Submit captcha solution and get nonce."""
    url = f"{API_BASE}/faucet/nonce"
    payload = {
        "address": ADDRESS,
        "agentId": AGENT_ID,
        "agentRegistry": REGISTRY,
        "challengeResponse": {
            "text": text,
            "challengeToken": challenge_token,
        },
    }
    
    print(f"[Step 2] POST {url} with captcha solution")
    print(f"[Step 2] Text: {repr(text)}, Sum: {ascii_sum(text)}")
    try:
        resp = requests.post(url, json=payload, timeout=10)
        print(f"[Step 2] HTTP {resp.status_code}")
        return resp.json()
    except Exception as e:
        print(f"[Step 2] Error: {e}")
        return {"error": str(e)}

def sign_siwa_message(nonce_data):
    """Step 3: Build and sign SIWA message."""
    nonce = nonce_data["nonce"]
    issued_at = nonce_data["issuedAt"]
    expiration_time = nonce_data.get("expirationTime")
    
    message_lines = [
        f"{DOMAIN} wants you to sign in with your Agent account:",
        ADDRESS,
        "",
        "Sign in to the BOTCOIN Faucet to claim your drip.",
        "",
        f"URI: https://{DOMAIN}/faucet",
        "Version: 1",
        f"Agent ID: {AGENT_ID}",
        f"Agent Registry: {REGISTRY}",
        f"Chain ID: {CHAIN_ID}",
        f"Nonce: {nonce}",
        f"Issued At: {issued_at}",
    ]
    
    if expiration_time:
        message_lines.append(f"Expiration Time: {expiration_time}")
    
    message = "\n".join(message_lines)
    
    print(f"[Step 3] Signing SIWA message...")
    print(f"[Step 3] Message:\n{message}")
    
    # Sign with EIP-191 personal_sign
    encoded = encode_defunct(text=message)
    account = Account.from_key(PRIVATE_KEY)
    signed = account.sign_message(encoded)
    signature = signed.signature.hex()
    
    print(f"[Step 3] Signature: {signature[:20]}...")
    
    return message, signature

def verify_signature(message, signature, nonce_token):
    """Step 4: Verify signature and get receipt."""
    url = f"{API_BASE}/faucet/verify"
    payload = {
        "message": message,
        "signature": signature,
        "nonceToken": nonce_token,
    }
    
    print(f"[Step 4] POST {url}")
    try:
        resp = requests.post(url, json=payload, timeout=30)
        print(f"[Step 4] HTTP {resp.status_code}")
        return resp.json()
    except Exception as e:
        print(f"[Step 4] Error: {e}")
        return {"error": str(e)}

def claim_drip(receipt):
    """Step 5: Claim BOTCOIN drip."""
    url = f"{API_BASE}/faucet/claim"
    headers = {
        "Authorization": f"Bearer {receipt}",
    }
    
    print(f"[Step 5] POST {url}")
    try:
        resp = requests.post(url, headers=headers, timeout=30)
        print(f"[Step 5] HTTP {resp.status_code}")
        return resp.json()
    except Exception as e:
        print(f"[Step 5] Error: {e}")
        return {"error": str(e)}

def main():
    print("=" * 60)
    print("Botcoin Faucet Claim Automation")
    print("=" * 60)
    
    # Step 1: Request nonce
    nonce_result = request_nonce()
    print(f"[Step 1] Response: {json.dumps(nonce_result, indent=2)[:500]}")
    
    if nonce_result.get("error"):
        print(f"[ERROR] Failed to get nonce: {nonce_result['error']}")
        return
    
    if nonce_result.get("status") == "not_registered":
        print(f"[ERROR] Agent not registered: {nonce_result.get('error', 'Unknown')}")
        return
    
    if nonce_result.get("status") == "rejected":
        print(f"[ERROR] Rejected: {nonce_result.get('error', nonce_result.get('code', 'Unknown'))}")
        return
    
    if nonce_result.get("status") == "nonce_issued":
        print("[INFO] No captcha needed! Proceeding to sign...")
        nonce_data = nonce_result
    elif nonce_result.get("status") == "captcha_required":
        print("[INFO] Captcha required! Solving...")
        challenge = nonce_result["challenge"]
        challenge_token = nonce_result["challengeToken"]
        
        # Solve captcha
        solution_text = solve_captcha(challenge)
        if not solution_text:
            print("[ERROR] Failed to solve captcha!")
            return
        
        print(f"[INFO] Captcha solution: {repr(solution_text)}")
        print(f"[INFO] ASCII sum: {ascii_sum(solution_text)} (target: {challenge['asciiTarget']})")
        
        # Submit captcha solution
        nonce_data = submit_captcha_solution(challenge_token, solution_text)
        print(f"[Step 2] Response: {json.dumps(nonce_data, indent=2)[:500]}")
        
        if nonce_data.get("status") != "nonce_issued":
            print(f"[ERROR] Captcha submission failed: {nonce_data.get('error', nonce_data.get('status', 'Unknown'))}")
            return
    else:
        print(f"[ERROR] Unexpected status: {nonce_result.get('status')}")
        return
    
    # Step 3: Sign SIWA message
    message, signature = sign_siwa_message(nonce_data)
    
    # Step 4: Verify
    verify_result = verify_signature(message, signature, nonce_data["nonceToken"])
    print(f"[Step 4] Response: {json.dumps(verify_result, indent=2)[:500]}")
    
    if verify_result.get("error"):
        print(f"[ERROR] Verification failed: {verify_result['error']}")
        return
    
    if not verify_result.get("receipt"):
        print(f"[ERROR] No receipt received!")
        return
    
    receipt = verify_result["receipt"]
    print(f"[INFO] Got receipt! Authenticated as Agent #{verify_result.get('agentId', 'unknown')}")
    
    # Step 5: Claim
    claim_result = claim_drip(receipt)
    print(f"[Step 5] Response: {json.dumps(claim_result, indent=2)}")
    
    if claim_result.get("status") == "success":
        print("=" * 60)
        print(f"🎉 SUCCESS! Claimed {claim_result.get('amount', '?')} BOTCOIN!")
        print(f"   Tier: {claim_result.get('tierName', '?')}")
        print(f"   TX: {claim_result.get('txHash', '?')}")
        print("=" * 60)
    else:
        print(f"[ERROR] Claim failed: {claim_result.get('error', claim_result.get('message', 'Unknown'))}")

if __name__ == "__main__":
    main()
