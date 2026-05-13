#!/usr/bin/env python3
"""
Dune Analytics + Alchemy RPC utility for Manteclaw
On-chain intelligence: wallet monitoring, bounty tracking, protocol analysis
"""

import requests
import json
import sys
import os

# ── Dune Analytics ──
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
if not DUNE_API_KEY:
    raise ValueError("DUNE_API_KEY environment variable required")
DUNE_BASE_URL = "https://api.dune.com/api/v1"
DUNE_HEADERS = {"x-dune-api-key": DUNE_API_KEY}

# ── Alchemy RPC (replaces unreliable public RPCs) ──
ALCHEMY_KEY = os.environ.get("ALCHEMY_API_KEY", "")
if not ALCHEMY_KEY:
    raise ValueError("ALCHEMY_API_KEY environment variable required")
ALCHEMY_RPC = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"

WALLETS = {
    "wallet_1_compromised": "0xC4Cf88b691D9b820040d861954d32e0C5f4538b7",
    "wallet_2_active": "0x8b8AAC89E101b77E5A917278120151FC496e5c39",
    "wallet_2_active": "0xD4E4b8e531d8AdAe126F400603361Ccda3931A8D",
    "wallet_3_bankr": "0x550c0cec65c9e585a0e59164f147a350e75a7a56",
    "wallet_4_fresh": "0xFC56950105883F46a3bB96ac9517A110724F2F27",
    "registration_key": "0xE8663112EdaFaCaEf5711D49e42a11D37023FA32",
    "daydreams": "0xBE251af5140A0CEfe629364190e1840D27632aED",
    "zyfai_safe": "0x056f49F6F0De7A7d9154127aD0a419E8632Af239",
    "nookplot_v2": "0xE8663112EdaFaCaEf5711D49e42a11D37023FA32",
    "workprotocol": "0xFC56950105883F46a3bB96ac9517A110724F2F27",
    "litcoiin_claim": "0x550c0cec65c9e585a0e59164f147a350e75a7a56",
    "0xwork": "0x550c0cec65c9e585a0e59164f147a350e75a7a56",
}

# ── Dune Functions ──
def get_query_results(query_id, limit=10):
    """Fetch results from a Dune query"""
    url = f"{DUNE_BASE_URL}/query/{query_id}/results?limit={limit}"
    resp = requests.get(url, headers=DUNE_HEADERS)
    return resp.json()

def get_query_status(query_id):
    """Check execution status of a query"""
    url = f"{DUNE_BASE_URL}/query/{query_id}/execute/status"
    resp = requests.get(url, headers=DUNE_HEADERS)
    return resp.json()

def execute_query(query_id):
    """Trigger fresh execution of a query"""
    url = f"{DUNE_BASE_URL}/query/{query_id}/execute"
    resp = requests.post(url, headers=DUNE_HEADERS)
    return resp.json()

def check_dune_key():
    """Verify Dune API key is valid"""
    url = f"{DUNE_BASE_URL}/query/4249209"
    resp = requests.get(url, headers=DUNE_HEADERS)
    data = resp.json()
    if "error" in data:
        if "unauthorized" in data["error"].lower():
            print("❌ Dune API key INVALID")
            return False
    print("✅ Dune API key VALID")
    return True

# ── Alchemy Functions ──
def get_wallet_balance(address):
    """Get ETH balance via Alchemy (replaces public RPCs)"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1
    }
    resp = requests.post(ALCHEMY_RPC, json=payload, headers={"Content-Type": "application/json"})
    data = resp.json()
    if "result" in data:
        wei = int(data["result"], 16)
        return wei / 1e18
    return 0.0

def get_wallet_tx_count(address):
    """Get transaction count via Alchemy"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [address, "latest"],
        "id": 1
    }
    resp = requests.post(ALCHEMY_RPC, json=payload, headers={"Content-Type": "application/json"})
    data = resp.json()
    if "result" in data:
        return int(data["result"], 16)
    return 0

def check_alchemy_key():
    """Verify Alchemy API key is working"""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }
    resp = requests.post(ALCHEMY_RPC, json=payload, headers={"Content-Type": "application/json"})
    data = resp.json()
    if "result" in data:
        block = int(data["result"], 16)
        print(f"✅ Alchemy API key VALID (block: {block})")
        return True
    print(f"❌ Alchemy API key INVALID: {data.get('error', 'unknown error')}")
    return False

# ── Wallet Monitor ──
def wallet_monitor():
    """Monitor all tracked wallets via Alchemy"""
    print("\n🔍 Wallet Monitor — Base L2 (via Alchemy)")
    print("=" * 60)
    total_eth = 0
    for name, addr in WALLETS.items():
        bal = get_wallet_balance(addr)
        txs = get_wallet_tx_count(addr)
        total_eth += bal
        status = "🔴 COMPROMISED" if "compromised" in name else ""
        print(f"\n{name}: {addr}")
        print(f"  Balance: {bal:.6f} ETH | TXs: {txs} {status}")
    print(f"\n💰 Total tracked: {total_eth:.6f} ETH")
    return total_eth

def list_queries():
    """List useful pre-built queries"""
    queries = {
        "base_wallet_activity": "Query wallet transactions on Base",
        "litcoiin_mining_stats": "Track Litcoiin protocol activity",
        "nookplot_bounties": "Monitor Nookplot bounty payouts",
        "agent_earnings_dashboard": "Aggregate earnings across protocols",
        "0xwork_tasks": "Track completed tasks on 0xWork",
        "zyfai_yield": "Monitor Zyfai yield strategy performance",
    }
    print("\n📊 Recommended Dune Queries to Build:")
    for q, desc in queries.items():
        print(f"  {q}: {desc}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dune_utils.py <command> [args]")
        print("Commands: check-dune, check-alchemy, monitor, queries, results <query_id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "check-dune":
        check_dune_key()
    elif cmd == "check-alchemy":
        check_alchemy_key()
    elif cmd == "check":
        check_dune_key()
        check_alchemy_key()
    elif cmd == "monitor":
        wallet_monitor()
    elif cmd == "queries":
        list_queries()
    elif cmd == "results":
        if len(sys.argv) < 3:
            print("Usage: dune_utils.py results <query_id>")
            sys.exit(1)
        print(json.dumps(get_query_results(sys.argv[2]), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
