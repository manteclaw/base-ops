#!/usr/bin/env python3
"""Botcoin Faucet Claim Automation with retries"""

import json
import requests
import time
from eth_account import Account
from eth_account.messages import encode_defunct

AGENT_ID = 46833
ADDRESS = "0xe8663112edafacaef5711d49e42a11d37023fa32"
REGISTRY = "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
PRIVATE_KEY = "0xa3b064d1104984e489a824b20971c5ee1b1a8eceabd8465d61900353c5d772ab"
API_BASE = "https://coordinator.agentmoney.net"
DOMAIN = "agentmoney.net"
CHAIN_ID = 8453

def ascii_sum(text):
    return sum(ord(c) for c in text)

def solve_captcha(challenge):
    target = challenge["asciiTarget"]
    line_count = challenge["lineCount"]
    newline_sum = (line_count - 1) * 10
    content_target = target - newline_sum
    
    import string
    chars = string.ascii_lowercase + ' '
    lines_pool = []
    for length in range(1, 5):
        for c1 in chars:
            if length == 1:
                lines_pool.append((c1, ord(c1)))
            elif length == 2:
                for c2 in chars:
                    lines_pool.append((c1+c2, ord(c1)+ord(c2)))
            elif length == 3:
                for c2 in chars:
                    for c3 in chars:
                        s = ord(c1)+ord(c2)+ord(c3)
                        if s <= content_target:
                            lines_pool.append((c1+c2+c3, s))
            elif length == 4:
                for c2 in chars:
                    for c3 in chars:
                        for c4 in chars:
                            s = ord(c1)+ord(c2)+ord(c3)+ord(c4)
                            if s <= content_target:
                                lines_pool.append((c1+c2+c3+c4, s))
    
    sum_to_lines = {}
    for line, s in lines_pool:
        sum_to_lines.setdefault(s, []).append(line)
    sums = sorted(sum_to_lines.keys())
    
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
    elif line_count == 5:
        for s1 in sums:
            for s2 in sums:
                for s3 in sums:
                    for s4 in sums:
                        s5 = content_target - s1 - s2 - s3 - s4
                        if s5 in sum_to_lines and s5 > 0:
                            for l1 in sum_to_lines[s1][:3]:
                                for l2 in sum_to_lines[s2][:3]:
                                    for l3 in sum_to_lines[s3][:3]:
                                        for l4 in sum_to_lines[s4][:3]:
                                            for l5 in sum_to_lines[s5][:3]:
                                                text = f"{l1}\n{l2}\n{l3}\n{l4}\n{l5}"
                                                if ascii_sum(text) == target:
                                                    return text

def request_nonce():
    url = f"{API_BASE}/faucet/nonce"
    payload = {"address": ADDRESS, "agentId": AGENT_ID, "agentRegistry": REGISTRY}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0

def submit_captcha_solution(challenge_token, text):
    url = f"{API_BASE}/faucet/nonce"
    payload = {
        "address": ADDRESS, "agentId": AGENT_ID, "agentRegistry": REGISTRY,
        "challengeResponse": {"text": text, "challengeToken": challenge_token},
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 0

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

def run_once():
    print("\n" + "="*60)
    print("Starting faucet claim attempt...")
    
    # Step 1: Get nonce
    nonce_result, status = request_nonce()
    print(f"[Nonce] HTTP {status}: {str(nonce_result)[:200]}")
    
    if nonce_result.get("error") or status != 200:
        return False, f"Nonce failed: {nonce_result.get('error', status)}"
    
    if nonce_result.get("status") == "captcha_required":
        challenge = nonce_result["challenge"]
        challenge_token = nonce_result["challengeToken"]
        solution = solve_captcha(challenge)
        if not solution:
            return False, "Captcha solve failed"
        print(f"[Captcha] Solved: {repr(solution)}, sum={ascii_sum(solution)}")
        time.sleep(3)  # Avoid rate limit between nonce request and captcha submit
        
        nonce_data, status = submit_captcha_solution(challenge_token, solution)
        print(f"[Captcha] HTTP {status}: {str(nonce_data)[:200]}")
        if nonce_data.get("status") != "nonce_issued":
            return False, f"Captcha submit failed: {nonce_data.get('error', nonce_data.get('status'))}"
    elif nonce_result.get("status") == "nonce_issued":
        nonce_data = nonce_result
    else:
        return False, f"Unexpected nonce status: {nonce_result.get('status')}"
    
    # Step 2: Sign and verify
    verify_result, status = sign_and_verify(nonce_data)
    print(f"[Verify] HTTP {status}: {str(verify_result)[:300]}")
    
    if verify_result.get("error"):
        return False, f"Verify failed: {verify_result['error']}"
    
    receipt = verify_result.get("receipt")
    if not receipt:
        return False, "No receipt from verify"
    
    # Step 3: Claim
    claim_result, status = claim_drip(receipt)
    print(f"[Claim] HTTP {status}: {json.dumps(claim_result)[:500]}")
    
    if claim_result.get("status") == "success":
        return True, f"Claimed {claim_result.get('amount', '?')} BOTCOIN! TX: {claim_result.get('txHash', '?')}"
    else:
        return False, f"Claim failed: {claim_result.get('error', claim_result.get('message', 'Unknown'))}"

if __name__ == "__main__":
    for attempt in range(1, 6):
        success, msg = run_once()
        if success:
            print(f"\n{'='*60}")
            print(f"SUCCESS on attempt {attempt}: {msg}")
            print(f"{'='*60}")
            break
        else:
            print(f"\nAttempt {attempt} failed: {msg}")
            if attempt < 5:
                sleep_time = 2 ** attempt
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    else:
        print(f"\n{'='*60}")
        print("All attempts failed.")
        print(f"{'='*60}")
