#!/usr/bin/env python3
"""
Base L2 Arbitrage Bot — Cross-DEX Price Monitor (web3.py version)
Queries prices from Uniswap V3, Aerodrome, BaseSwap via Alchemy RPC
"""

import json
import os
import sys
from typing import Dict, Optional

from web3 import Web3

# ── Config ──
with open(os.path.join(os.path.dirname(__file__), "config.json")) as f:
    CONFIG = json.load(f)

ALCHEMY_KEY = os.environ.get("ALCHEMY_API_KEY", "")
if not ALCHEMY_KEY:
    raise ValueError("ALCHEMY_API_KEY environment variable required")

RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise ConnectionError(f"Cannot connect to Alchemy RPC: {RPC_URL[:40]}...")

print(f"✅ Connected to Base mainnet (block: {w3.eth.block_number})")

TOKEN_DECIMALS = {"WETH": 18, "USDC": 6, "DAI": 18, "CBETH": 18}

# ── ABIs ──
UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

UNISWAP_V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function",
    },
]

V2_PAIR_ABI = [
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "reserve0", "type": "uint112"},
            {"internalType": "uint112", "name": "reserve1", "type": "uint112"},
            {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint32"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def sqrt_price_x96_to_price(sqrt_price_x96: int, token0_decimals: int, token1_decimals: int) -> float:
    """Convert Uniswap V3 sqrtPriceX96 to human-readable price (token1 per token0)"""
    price = (sqrt_price_x96 ** 2) / (2 ** 192)
    decimal_adjustment = 10 ** (token0_decimals - token1_decimals)
    return price * decimal_adjustment


def get_uniswap_v3_price(token_a: str, token_b: str) -> Optional[Dict]:
    """Get Uniswap V3 pool price and liquidity for a token pair"""
    token0_addr = Web3.to_checksum_address(CONFIG["tokens"][token_a])
    token1_addr = Web3.to_checksum_address(CONFIG["tokens"][token_b])

    factory = w3.eth.contract(
        address=Web3.to_checksum_address(CONFIG["dexes"]["uniswap_v3"]["factory"]),
        abi=UNISWAP_V3_FACTORY_ABI,
    )

    for fee in CONFIG["dexes"]["uniswap_v3"]["fee_tiers"]:
        try:
            pool_addr = factory.functions.getPool(token0_addr, token1_addr, fee).call()
            if pool_addr == "0x0000000000000000000000000000000000000000":
                continue

            pool = w3.eth.contract(address=pool_addr, abi=UNISWAP_V3_POOL_ABI)
            slot0 = pool.functions.slot0().call()
            liquidity = pool.functions.liquidity().call()
            sqrt_price_x96 = slot0[0]

            price = sqrt_price_x96_to_price(
                sqrt_price_x96,
                TOKEN_DECIMALS[token_a],
                TOKEN_DECIMALS[token_b],
            )

            return {
                "dex": f"uniswap_v3_{fee}",
                "pool": pool_addr,
                "price": price,
                "liquidity": liquidity,
                "tick": slot0[1],
            }
        except Exception as e:
            continue

    return None


def get_v2_price(token_a: str, token_b: str, router_name: str) -> Optional[Dict]:
    """Get price from a V2-style DEX (Aerodrome, BaseSwap) using pair reserves"""
    dex_config = CONFIG["dexes"][router_name]
    token0_addr = Web3.to_checksum_address(CONFIG["tokens"][token_a])
    token1_addr = Web3.to_checksum_address(CONFIG["tokens"][token_b])

    # For V2 DEXes, we need to find the pair address
    # Aerodrome uses a different factory than standard Uniswap V2
    # BaseSwap uses standard V2 getPair

    # Use factory to get pair address
    # Standard V2 getPair: function getPair(address tokenA, address tokenB) external view returns (address pair)
    factory_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
            ],
            "name": "getPair",
            "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]

    try:
        factory = w3.eth.contract(
            address=Web3.to_checksum_address(dex_config["factory"]),
            abi=factory_abi,
        )
        pair_addr = factory.functions.getPair(token0_addr, token1_addr).call()

        if pair_addr == "0x0000000000000000000000000000000000000000":
            return None

        pair = w3.eth.contract(address=pair_addr, abi=V2_PAIR_ABI)
        reserves = pair.functions.getReserves().call()
        pair_token0 = pair.functions.token0().call()

        reserve0 = reserves[0]
        reserve1 = reserves[1]

        # Determine which reserve is token_a and which is token_b
        if pair_token0.lower() == token0_addr.lower():
            # reserve0 = token_a, reserve1 = token_b
            price = (reserve1 / 10 ** TOKEN_DECIMALS[token_b]) / (reserve0 / 10 ** TOKEN_DECIMALS[token_a])
        else:
            # reserve0 = token_b, reserve1 = token_a
            price = (reserve0 / 10 ** TOKEN_DECIMALS[token_b]) / (reserve1 / 10 ** TOKEN_DECIMALS[token_a])

        return {
            "dex": router_name,
            "pool": pair_addr,
            "price": price,
            "liquidity": min(reserve0, reserve1),
        }
    except Exception as e:
        return None


def get_all_prices(token_a: str, token_b: str) -> Dict[str, Optional[Dict]]:
    """Fetch prices from all DEXes for a token pair"""
    results = {}

    # Uniswap V3
    uni = get_uniswap_v3_price(token_a, token_b)
    if uni:
        results["uniswap_v3"] = uni

    # Aerodrome
    aero = get_v2_price(token_a, token_b, "aerodrome")
    if aero:
        results["aerodrome"] = aero

    # BaseSwap
    base = get_v2_price(token_a, token_b, "baseswap")
    if base:
        results["baseswap"] = base

    return results


def find_arbitrage(token_a: str, token_b: str, trade_amount_eth: float) -> Optional[Dict]:
    """Check for profitable arbitrage across DEXes"""
    prices = get_all_prices(token_a, token_b)
    if len(prices) < 2:
        return None

    # Find best buy (lowest price) and best sell (highest price)
    valid_prices = {k: v for k, v in prices.items() if v}
    if len(valid_prices) < 2:
        return None

    buy_dex = min(valid_prices, key=lambda k: valid_prices[k]["price"])
    sell_dex = max(valid_prices, key=lambda k: valid_prices[k]["price"])

    buy_price = valid_prices[buy_dex]["price"]
    sell_price = valid_prices[sell_dex]["price"]

    # Price difference as percentage
    price_diff_pct = ((sell_price - buy_price) / buy_price) * 100

    # Estimate output
    amount_in = trade_amount_eth
    amount_out_buy = amount_in * buy_price
    amount_out_sell = amount_in * sell_price

    # Account for swap fees (0.05% for 500 bps, 0.3% for 3000 bps, 1% for 10000 bps)
    # Rough estimate: 0.3% fee per swap
    fee_pct = 0.006  # 0.6% round-trip (0.3% buy + 0.3% sell)
    gross_profit = amount_out_sell - amount_out_buy
    fee_cost = (amount_out_buy + amount_out_sell) * fee_pct

    # Gas cost on Base: ~150k gas per swap, ~0.1 gwei = ~$0.01-0.02 per swap
    # Round-trip = 2 swaps + maybe 1 approve = ~300k gas
    eth_price = get_eth_price_usd()
    gas_cost_eth = (CONFIG["gas_price_gwei"] * 300000) / 1e9
    gas_cost_usd = gas_cost_eth * eth_price

    net_profit = gross_profit - fee_cost - gas_cost_eth
    net_profit_usd = net_profit * eth_price if token_a == "WETH" else net_profit

    if net_profit_usd >= CONFIG["min_profit_usd"]:
        return {
            "token_a": token_a,
            "token_b": token_b,
            "amount": trade_amount_eth,
            "buy_dex": buy_dex,
            "buy_price": buy_price,
            "sell_dex": sell_dex,
            "sell_price": sell_price,
            "price_diff_pct": price_diff_pct,
            "gross_profit": gross_profit,
            "fee_cost": fee_cost,
            "gas_cost_eth": gas_cost_eth,
            "gas_cost_usd": gas_cost_usd,
            "net_profit": net_profit,
            "net_profit_usd": net_profit_usd,
        }
    return None


def get_eth_price_usd() -> float:
    """Get ETH price in USD from Uniswap V3 WETH/USDC pool"""
    try:
        result = get_uniswap_v3_price("WETH", "USDC")
        if result:
            # price = USDC per WETH (e.g., 2350)
            return result["price"]
    except Exception:
        pass
    return 3500.0


if __name__ == "__main__":
    print("\n🔍 Base L2 Arbitrage Bot — Price Scanner")
    print("=" * 60)

    for pair in CONFIG["arbitrage_pairs"]:
        token_a, token_b = pair
        print(f"\n📊 {token_a}/{token_b}")

        prices = get_all_prices(token_a, token_b)
        for dex, data in prices.items():
            if data:
                print(f"  {dex:12s}: {data['price']:.6f} (liquidity: {data['liquidity']:.0f})")
            else:
                print(f"  {dex:12s}: N/A")

        opp = find_arbitrage(token_a, token_b, CONFIG["max_trade_size_eth"])
        if opp:
            print(f"  🚨 ARBITRAGE: ${opp['net_profit_usd']:.2f} net | "
                  f"buy {opp['buy_dex']} @ {opp['buy_price']:.6f} → "
                  f"sell {opp['sell_dex']} @ {opp['sell_price']:.6f} "
                  f"(+{opp['price_diff_pct']:.3f}%)")
        else:
            print(f"  ✅ No profitable arbitrage")
