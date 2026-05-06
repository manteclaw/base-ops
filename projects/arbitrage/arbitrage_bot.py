#!/usr/bin/env python3
"""
Base L2 Arbitrage Bot — Reactive Mode
Listens for new blocks via WebSocket, scans DEX prices on each block.
Respects $5 ETH reserve + medium risk slippage (1.5%).
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware

from price_monitor import (
    CONFIG,
    find_arbitrage,
    get_all_prices,
    get_eth_price_usd,
)

# ── Wallet ──
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")
MNEMONIC = os.environ.get("MNEMONIC", "")
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS", CONFIG.get("wallet", ""))

# ── Reserve Config ──
RESERVE_ETH = CONFIG.get("reserve_eth", 0.0025)  # $5-ish reserve
MIN_BALANCE_ETH = CONFIG.get("min_wallet_balance_eth", 0.0025)
MAX_TRADE_ETH = CONFIG.get("max_trade_size_eth", 0.005)
SLIPPAGE_BPS = CONFIG.get("slippage_bps", 150)  # 1.5% medium risk

def log_opportunity(opp: dict, block_num: int):
    ts = datetime.utcnow().isoformat()
    line = (
        f"[{ts}] Block #{block_num} | ARBITRAGE: {opp['token_a']}/{opp['token_b']} | "
        f"${opp['net_profit_usd']:.2f} net | buy {opp['buy_dex']} → sell {opp['sell_dex']} | "
        f"diff: +{opp['price_diff_pct']:.3f}% | slippage: {SLIPPAGE_BPS/100:.1f}%"
    )
    print(line)
    log_path = os.path.join(os.path.dirname(__file__), "arbitrage_log.txt")
    with open(log_path, "a") as f:
        f.write(line + "\n")
        f.write(json.dumps({"block": block_num, **opp}, default=str) + "\n")


async def check_wallet_balance(w3: Web3):
    """Check if wallet has enough ETH above reserve"""
    if not WALLET_ADDRESS:
        return 0.0
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(WALLET_ADDRESS))
    balance_eth = w3.from_wei(balance_wei, "ether")
    return float(balance_eth)


async def scan_block(w3: Web3, block_num: int, dry_run: bool = True):
    """Scan all pairs for arbitrage on a given block"""
    balance_eth = await check_wallet_balance(w3)
    tradeable_eth = max(0, balance_eth - RESERVE_ETH)
    max_trade = min(MAX_TRADE_ETH, tradeable_eth)

    if max_trade <= 0:
        return 0

    opportunities = 0
    for pair in CONFIG["arbitrage_pairs"]:
        token_a, token_b = pair
        opp = find_arbitrage(token_a, token_b, max_trade)

        if opp:
            opportunities += 1
            log_opportunity(opp, block_num)

            if not dry_run:
                print(f"🚀 Block #{block_num} | EXECUTING trade...")
                # TODO: execute_trade(opp, SLIPPAGE_BPS)

    return opportunities


async def reactive_loop(ws_url: str, dry_run: bool = True):
    """WebSocket block subscription loop"""
    print("=" * 60)
    print("🤖 BASE L2 ARBITRAGE BOT — REACTIVE MODE")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print(f"Wallet: {WALLET_ADDRESS or 'NOT SET'}")
    print(f"Reserve: {RESERVE_ETH} ETH (~$5)")
    print(f"Max trade: {MAX_TRADE_ETH} ETH")
    print(f"Slippage: {SLIPPAGE_BPS/100:.1f}% (medium risk)")
    print(f"WebSocket: {ws_url[:40]}...")
    print("=" * 60)

    # Initial HTTP check for balance
    rpc_http = ws_url.replace("wss://", "https://").replace("ws://", "http://")
    w3_http = Web3(Web3.HTTPProvider(rpc_http))
    if not w3_http.is_connected():
        print("❌ Cannot connect to HTTP RPC")
        sys.exit(1)

    balance = await check_wallet_balance(w3_http)
    print(f"💰 Wallet balance: {balance:.6f} ETH")
    print(f"   Reserve: {RESERVE_ETH} ETH | Tradeable: {max(0, balance - RESERVE_ETH):.6f} ETH")

    if balance < MIN_BALANCE_ETH:
        print(f"⚠️  Balance below minimum ({MIN_BALANCE_ETH} ETH). Waiting for funding...")
        print(f"   User said: '$10 ETH tomorrow morning'")

    print("\n🔌 Connecting WebSocket for block subscription...")

    w3_ws = Web3(Web3.WebsocketProvider(ws_url))
    if not w3_ws.is_connected():
        print("❌ WebSocket connection failed. Falling back to HTTP polling...")
        await poll_loop(w3_http, dry_run)
        return

    print("✅ WebSocket connected. Listening for new blocks...\n")

    block_filter = w3_ws.eth.filter("latest")
    opportunities_found = 0
    last_block = 0

    try:
        while True:
            for event in block_filter.get_new_entries():
                block_num = event
                if block_num == last_block:
                    continue
                last_block = block_num

                count = await scan_block(w3_http, block_num, dry_run)
                opportunities_found += count

                if count > 0:
                    print(f"  → {count} opportunities on block #{block_num}")

            await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped. Total opportunities: {opportunities_found}")


async def poll_loop(w3: Web3, dry_run: bool = True):
    """Fallback HTTP polling loop"""
    print("📡 Fallback polling mode (10s intervals)\n")
    opportunities_found = 0

    try:
        while True:
            block_num = w3.eth.block_number
            count = await scan_block(w3, block_num, dry_run)
            opportunities_found += count

            if count > 0:
                print(f"  → {count} opportunities on block #{block_num}")

            await asyncio.sleep(CONFIG["poll_interval_sec"])

    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped. Total opportunities: {opportunities_found}")


async def main():
    parser = argparse.ArgumentParser(description="Base L2 Reactive Arbitrage Bot")
    parser.add_argument("--execute", action="store_true", help="Enable live trade execution")
    parser.add_argument("--ws-url", default=None, help="WebSocket RPC URL (default: Alchemy wss)")
    args = parser.parse_args()

    dry_run = not args.execute

    # Get Alchemy WebSocket URL
    alchemy_key = os.environ.get("ALCHEMY_API_KEY", "")
    if args.ws_url:
        ws_url = args.ws_url
    elif alchemy_key:
        ws_url = f"wss://base-mainnet.g.alchemy.com/v2/{alchemy_key}"
    else:
        print("❌ No WebSocket URL or ALCHEMY_API_KEY provided")
        sys.exit(1)

    await reactive_loop(ws_url, dry_run)


if __name__ == "__main__":
    asyncio.run(main())
