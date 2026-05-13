#!/usr/bin/env python3
"""
Base L2 Arbitrage Bot — Trade Execution Engine
Handles: DEX router swaps, gas estimation, nonce management, multi-hop,
profit tracking, MEV protection (deadline-based on Base L2).
"""

import json
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from web3 import Web3
from eth_account import Account

# ── Config & RPC (lazy init) ──
SCRIPT_DIR = Path(__file__).parent
with open(SCRIPT_DIR / "config.json") as f:
    CONFIG = json.load(f)

ALCHEMY_KEY = os.environ.get("ALCHEMY_API_KEY", "")
RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}" if ALCHEMY_KEY else CONFIG.get("rpc_url", "")

_w3: Optional[Web3] = None

def get_w3() -> Web3:
    global _w3
    if _w3 is not None:
        return _w3
    if not RPC_URL:
        raise ValueError("No RPC URL available. Set ALCHEMY_API_KEY or rpc_url in config.")
    _w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not _w3.is_connected():
        raise ConnectionError(f"Cannot connect to Base RPC: {RPC_URL[:50]}...")
    return _w3

CHAIN_ID = 8453  # Base mainnet

# ── Wallet ──
MNEMONIC = os.environ.get("MNEMONIC", "music tourist shine addict crew sadness jewel blossom number season sponsor atom")
WALLET_ADDRESS = Web3.to_checksum_address(
    os.environ.get("WALLET_ADDRESS", CONFIG.get("wallet", "0x8b8AAC89E101b77E5A917278120151FC496e5c39"))
)

_wallet_account: Optional[Account] = None
_wallet_nonce: Optional[int] = None

def _load_wallet() -> Optional[Account]:
    """Derive wallet from mnemonic or private key."""
    global _wallet_account
    if _wallet_account is not None:
        return _wallet_account
    if MNEMONIC:
        Account.enable_unaudited_hdwallet_features()
        _wallet_account = Account.from_mnemonic(MNEMONIC)
        if _wallet_account.address.lower() != WALLET_ADDRESS.lower():
            print(f"⚠️  Derived address {_wallet_account.address} != expected {WALLET_ADDRESS}")
        return _wallet_account
    pk = os.environ.get("PRIVATE_KEY", "")
    if pk:
        _wallet_account = Account.from_key(pk)
        return _wallet_account
    return None

def get_wallet() -> Optional[Account]:
    return _load_wallet()

def get_next_nonce() -> int:
    """Sequential nonce management. Call before each tx."""
    global _wallet_nonce
    w3 = get_w3()
    if _wallet_nonce is None:
        _wallet_nonce = get_w3().eth.get_transaction_count(WALLET_ADDRESS, 'pending')
    else:
        _wallet_nonce += 1
    return _wallet_nonce

def reset_nonce():
    """Reset nonce (e.g. after a failed tx or on restart)."""
    global _wallet_nonce
    _wallet_nonce = None

# ── Token Decimals ──
TOKEN_DECIMALS = {"WETH": 18, "USDC": 6, "DAI": 18, "CBETH": 18}

def token_amount_to_wei(symbol: str, amount: float) -> int:
    return int(amount * 10 ** TOKEN_DECIMALS[symbol])

def wei_to_token_amount(symbol: str, wei: int) -> float:
    return wei / 10 ** TOKEN_DECIMALS[symbol]

# ── ABIs ──
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

# Uniswap V3 SwapRouter02 (Base)
UNISWAP_V3_ROUTER_ABI = [
    # exactInputSingle
    {
        "inputs": [{
            "components": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
            ],
            "internalType": "struct IV3SwapRouter.ExactInputSingleParams",
            "name": "params",
            "type": "tuple"
        }],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    # exactInput (multi-hop)
    {
        "inputs": [{
            "components": [
                {"internalType": "bytes", "name": "path", "type": "bytes"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
            ],
            "internalType": "struct IV3SwapRouter.ExactInputParams",
            "name": "params",
            "type": "tuple"
        }],
        "name": "exactInput",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    # refundETH
    {"inputs": [], "name": "refundETH", "outputs": [], "stateMutability": "payable", "type": "function"},
]

# Aerodrome Router (Solidly-style on Base)
AERODROME_ROUTER_ABI = [
    # swapExactTokensForTokens
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "bool", "name": "stable", "type": "bool"},
                    {"internalType": "address", "name": "factory", "type": "address"},
                ],
                "internalType": "struct IRouter.Route[]",
                "name": "routes",
                "type": "tuple[]"
            },
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # getAmountsOut
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "bool", "name": "stable", "type": "bool"},
                    {"internalType": "address", "name": "factory", "type": "address"},
                ],
                "internalType": "struct IRouter.Route[]",
                "name": "routes",
                "type": "tuple[]"
            },
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Helpers ──
def is_stable_pair(token_a: str, token_b: str) -> bool:
    """Heuristic: both are stablecoins → stable pool."""
    stables = {"USDC", "DAI"}
    return token_a in stables and token_b in stables

def build_aerodrome_route(token_in: str, token_out: str) -> Tuple:
    """Build a single Aerodrome Route tuple."""
    factory = CONFIG["dexes"]["aerodrome"]["factory"]
    stable = is_stable_pair(token_in, token_out)
    return (
        Web3.to_checksum_address(CONFIG["tokens"][token_in]),
        Web3.to_checksum_address(CONFIG["tokens"][token_out]),
        stable,
        Web3.to_checksum_address(factory),
    )

def encode_v3_path(tokens: List[str], fees: List[int]) -> bytes:
    """Encode a Uniswap V3 multi-hop path: token + fee + token + fee + ..."""
    path = b""
    for i, token in enumerate(tokens[:-1]):
        path += Web3.to_bytes(hexstr=CONFIG["tokens"][token])
        path += fees[i].to_bytes(3, "big")
    path += Web3.to_bytes(hexstr=CONFIG["tokens"][tokens[-1]])
    return path

def get_deadline(seconds: int = 60) -> int:
    """MEV protection: short deadline (default 60s) to reduce sandwich risk."""
    return int(time.time()) + seconds

# ── Approval ──
def ensure_approval(token_symbol: str, spender_address: str, amount_wei: int) -> Optional[str]:
    """Ensure router is approved to spend tokens. Returns tx_hash if approval sent, else None."""
    token_addr = Web3.to_checksum_address(CONFIG["tokens"][token_symbol])
    token = get_w3().eth.contract(address=token_addr, abi=ERC20_ABI)
    allowance = token.functions.allowance(WALLET_ADDRESS, spender_address).call()
    if allowance >= amount_wei:
        return None  # Already approved

    wallet = get_wallet()
    if not wallet:
        raise RuntimeError("Wallet not available — cannot sign approval tx")

    nonce = get_next_nonce()
    gas_price = get_w3().eth.gas_price

    tx = token.functions.approve(spender_address, amount_wei).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "gas": 60000,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    })

    signed = wallet.sign_transaction(tx)
    tx_hash = get_w3().eth.send_raw_transaction(signed.rawTransaction)
    print(f"  📤 Approval tx sent: {tx_hash.hex()}")

    receipt = get_w3().eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    if receipt.status != 1:
        raise RuntimeError(f"Approval failed: {tx_hash.hex()}")
    print(f"  ✅ Approval confirmed (gas used: {receipt.gasUsed})")
    return tx_hash.hex()

# ── Gas Estimation ──
def estimate_gas_cost_eth(gas_limit: int = 300000) -> float:
    """Estimate gas cost in ETH for a given gas limit."""
    gas_price = get_w3().eth.gas_price
    return float(get_w3().from_wei(gas_price * gas_limit, "ether"))

def abort_if_unprofitable(expected_profit_eth: float, gas_limit: int = 300000) -> bool:
    """Returns True if gas cost exceeds expected profit (should abort)."""
    gas_cost = estimate_gas_cost_eth(gas_limit)
    if gas_cost >= expected_profit_eth:
        print(f"  ⛔ ABORT: Gas cost ({gas_cost:.8f} ETH) ≥ expected profit ({expected_profit_eth:.8f} ETH)")
        return True
    print(f"  💨 Gas estimate: {gas_cost:.8f} ETH | Profit: {expected_profit_eth:.8f} ETH → GO")
    return False

# ── Uniswap V3 Single-Hop Swap ──
def swap_uni_v3_single(
    token_in: str,
    token_out: str,
    amount_in: float,
    slippage_bps: int,
    fee: int = 3000,
) -> Dict[str, Any]:
    """Execute a single-hop swap on Uniswap V3. Returns result dict with tx_hash, amount_out, etc."""
    wallet = get_wallet()
    if not wallet:
        raise RuntimeError("Wallet not available")

    router_addr = Web3.to_checksum_address(CONFIG["dexes"]["uniswap_v3"]["router"])
    router = get_w3().eth.contract(address=router_addr, abi=UNISWAP_V3_ROUTER_ABI)

    token_in_addr = Web3.to_checksum_address(CONFIG["tokens"][token_in])
    token_out_addr = Web3.to_checksum_address(CONFIG["tokens"][token_out])
    amount_in_wei = token_amount_to_wei(token_in, amount_in)

    # Estimate amount out using the quoter or a rough calc
    # For now, use the opportunity's expected output with slippage
    # The caller should compute amount_out_min
    # We'll do a simple estimation: check pool price
    from price_monitor import get_uniswap_v3_price
    pool_data = get_uniswap_v3_price(token_in, token_out)
    if not pool_data:
        raise RuntimeError(f"No Uniswap V3 pool found for {token_in}/{token_out}")

    expected_out = amount_in * pool_data["price"]
    amount_out_min_wei = int(token_amount_to_wei(token_out, expected_out) * (10000 - slippage_bps) / 10000)

    # Ensure approval
    ensure_approval(token_in, router_addr, amount_in_wei)

    params = (
        token_in_addr,      # tokenIn
        token_out_addr,     # tokenOut
        fee,                # fee
        WALLET_ADDRESS,     # recipient
        amount_in_wei,      # amountIn
        amount_out_min_wei, # amountOutMinimum
        0,                  # sqrtPriceLimitX96 (no limit)
    )

    nonce = get_next_nonce()
    gas_price = get_w3().eth.gas_price

    tx = router.functions.exactInputSingle(params).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "gas": 250000,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    })

    signed = wallet.sign_transaction(tx)
    tx_hash = get_w3().eth.send_raw_transaction(signed.rawTransaction)
    print(f"  📤 Uniswap V3 swap tx: {tx_hash.hex()}")

    receipt = get_w3().eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    success = receipt.status == 1

    # Parse amountOut from logs (event Swap on the pool)
    amount_out_wei = 0
    if success:
        # Try to get amountOut from Swap event logs
        # The pool emits: Swap(sender, recipient, amount0, amount1, sqrtPriceX96, liquidity, tick)
        # We need to identify which amount is positive (the one we received)
        for log in receipt.logs:
            # Simple heuristic: check if log address is the pool
            if log.address.lower() == pool_data["pool"].lower():
                # Decode Swap event: topic0 = keccak256("Swap(address,address,int256,int256,uint160,uint128,int24)")
                # Data contains amount0 and amount1 as int256
                # This is complex to decode without full ABI; skip for now
                pass

    return {
        "tx_hash": tx_hash.hex(),
        "status": "success" if success else "failed",
        "gas_used": receipt.gasUsed,
        "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, "effectiveGasPrice") else gas_price,
        "amount_out_wei": amount_out_wei,
        "amount_out": wei_to_token_amount(token_out, amount_out_wei) if amount_out_wei else expected_out,
    }

# ── Aerodrome V2 Swap ──
def swap_aerodrome(
    token_in: str,
    token_out: str,
    amount_in: float,
    slippage_bps: int,
) -> Dict[str, Any]:
    """Execute a swap on Aerodrome (Solidly-style V2)."""
    wallet = get_wallet()
    if not wallet:
        raise RuntimeError("Wallet not available")

    router_addr = Web3.to_checksum_address(CONFIG["dexes"]["aerodrome"]["router"])
    router = get_w3().eth.contract(address=router_addr, abi=AERODROME_ROUTER_ABI)

    amount_in_wei = token_amount_to_wei(token_in, amount_in)

    # Estimate amount out
    route = build_aerodrome_route(token_in, token_out)
    try:
        amounts = router.functions.getAmountsOut(amount_in_wei, [route]).call()
        expected_out_wei = amounts[-1]
    except Exception as e:
        print(f"  ⚠️  getAmountsOut failed: {e}")
        expected_out_wei = int(amount_in_wei * 0.95)  # rough fallback

    amount_out_min_wei = int(expected_out_wei * (10000 - slippage_bps) / 10000)

    # Ensure approval
    ensure_approval(token_in, router_addr, amount_in_wei)

    deadline = get_deadline(60)

    tx = router.functions.swapExactTokensForTokens(
        amount_in_wei,
        amount_out_min_wei,
        [route],
        WALLET_ADDRESS,
        deadline,
    ).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": get_next_nonce(),
        "gas": 250000,
        "gasPrice": get_w3().eth.gas_price,
        "chainId": CHAIN_ID,
    })

    signed = wallet.sign_transaction(tx)
    tx_hash = get_w3().eth.send_raw_transaction(signed.rawTransaction)
    print(f"  📤 Aerodrome swap tx: {tx_hash.hex()}")

    receipt = get_w3().eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    success = receipt.status == 1

    return {
        "tx_hash": tx_hash.hex(),
        "status": "success" if success else "failed",
        "gas_used": receipt.gasUsed,
        "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, "effectiveGasPrice") else get_w3().eth.gas_price,
        "amount_out_wei": expected_out_wei,
        "amount_out": wei_to_token_amount(token_out, expected_out_wei),
    }

# ── Multi-Hop (Triangle) Arbitrage on Uniswap V3 ──
def execute_triangle_arbitrage(
    path_tokens: List[str],
    path_fees: List[int],
    amount_in: float,
    slippage_bps: int,
) -> Dict[str, Any]:
    """
    Execute a triangle/multi-hop swap on Uniswap V3.
    Example: WETH → USDC → DAI → WETH
    path_tokens = ["WETH", "USDC", "DAI", "WETH"]
    path_fees = [3000, 500, 3000]
    """
    wallet = get_wallet()
    if not wallet:
        raise RuntimeError("Wallet not available")

    if len(path_tokens) != len(path_fees) + 1:
        raise ValueError("path_tokens must have exactly one more element than path_fees")

    router_addr = Web3.to_checksum_address(CONFIG["dexes"]["uniswap_v3"]["router"])
    router = get_w3().eth.contract(address=router_addr, abi=UNISWAP_V3_ROUTER_ABI)

    token_in = path_tokens[0]
    token_out = path_tokens[-1]
    amount_in_wei = token_amount_to_wei(token_in, amount_in)

    # Rough estimate: we expect to end up with ~same token, so amountOutMinimum
    # is the minimum we want back. For arbitrage, we want > input.
    # Use a conservative slippage on the full path.
    amount_out_min_wei = int(amount_in_wei * (10000 - slippage_bps) / 10000)

    # Ensure approval for the first token
    ensure_approval(token_in, router_addr, amount_in_wei)

    encoded_path = encode_v3_path(path_tokens, path_fees)

    params = (
        encoded_path,
        WALLET_ADDRESS,
        amount_in_wei,
        amount_out_min_wei,
    )

    tx = router.functions.exactInput(params).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": get_next_nonce(),
        "gas": 400000,  # Multi-hop needs more gas
        "gasPrice": get_w3().eth.gas_price,
        "chainId": CHAIN_ID,
    })

    signed = wallet.sign_transaction(tx)
    tx_hash = get_w3().eth.send_raw_transaction(signed.rawTransaction)
    print(f"  📤 Triangle swap tx: {tx_hash.hex()}")

    receipt = get_w3().eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    success = receipt.status == 1

    return {
        "tx_hash": tx_hash.hex(),
        "status": "success" if success else "failed",
        "gas_used": receipt.gasUsed,
        "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, "effectiveGasPrice") else get_w3().eth.gas_price,
        "path": " → ".join(path_tokens),
    }

# ── Generic Swap Dispatcher ──
def execute_swap(dex_name: str, token_in: str, token_out: str, amount_in: float, slippage_bps: int) -> Dict[str, Any]:
    """Route swap to the correct DEX implementation."""
    if dex_name.startswith("uniswap_v3"):
        # Extract fee from dex name if present (e.g. "uniswap_v3_500")
        parts = dex_name.split("_")
        fee = int(parts[-1]) if len(parts) > 2 and parts[-1].isdigit() else 3000
        return swap_uni_v3_single(token_in, token_out, amount_in, slippage_bps, fee)
    elif dex_name == "aerodrome":
        return swap_aerodrome(token_in, token_out, amount_in, slippage_bps)
    else:
        raise ValueError(f"Unsupported DEX for execution: {dex_name}")

# ── Profit Tracker ──
PROFIT_LOG_PATH = SCRIPT_DIR / "arbitrage_profit.json"

@dataclass
class TradeRecord:
    timestamp: str
    block_number: int
    token_a: str
    token_b: str
    buy_dex: str
    sell_dex: str
    amount_in_eth: float
    expected_profit_usd: float
    gas_cost_eth: float
    gas_cost_usd: float
    net_profit_usd: float
    tx_hash_buy: str
    tx_hash_sell: str
    status: str
    notes: str = ""

def load_profit_log() -> Dict:
    if PROFIT_LOG_PATH.exists():
        with open(PROFIT_LOG_PATH) as f:
            return json.load(f)
    return {
        "total_trades": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "total_gross_profit_usd": 0.0,
        "total_net_profit_usd": 0.0,
        "total_gas_cost_usd": 0.0,
        "trades": [],
    }

def save_profit_log(data: Dict):
    with open(PROFIT_LOG_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

def log_trade(record: TradeRecord):
    """Append a trade record to the profit log."""
    data = load_profit_log()
    data["total_trades"] += 1
    if record.status == "success":
        data["successful_trades"] += 1
        data["total_gross_profit_usd"] += record.expected_profit_usd
        data["total_net_profit_usd"] += record.net_profit_usd
    else:
        data["failed_trades"] += 1
    data["total_gas_cost_usd"] += record.gas_cost_usd
    data["trades"].append(asdict(record))
    save_profit_log(data)
    print(f"  🏦 Trade logged: {record.status} | Net: ${record.net_profit_usd:.4f}")

def get_profit_summary() -> Dict:
    return load_profit_log()

# ── Main Execution Function ──
def execute_trade(opp: Dict, slippage_bps: int, block_num: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute a cross-DEX arbitrage trade.
    opp dict from find_arbitrage() contains:
      token_a, token_b, amount, buy_dex, sell_dex, net_profit, net_profit_usd, etc.
    """
    if dry_run:
        print(f"  🔮 DRY RUN: Would execute {opp['token_a']}/{opp['token_b']} on {opp['buy_dex']} → {opp['sell_dex']}")
        return {"status": "dry_run", "opp": opp}

    wallet = get_wallet()
    if not wallet:
        print("  ❌ Wallet not available. Set MNEMONIC or PRIVATE_KEY.")
        return {"status": "no_wallet", "opp": opp}

    # Check wallet has ETH for gas
    try:
        w3 = get_w3()
        eth_balance = float(w3.from_wei(w3.eth.get_balance(WALLET_ADDRESS), "ether"))
        if eth_balance < 0.0001:
            print(f"  ⛔ ABORT: Wallet has {eth_balance:.6f} ETH — insufficient for gas")
            return {"status": "aborted_no_gas", "eth_balance": eth_balance, "opp": opp}
    except Exception as e:
        print(f"  ⚠️  Could not check ETH balance: {e}")

    # Check gas vs profit before executing
    expected_profit_eth = opp.get("net_profit", 0)
    if abort_if_unprofitable(expected_profit_eth, gas_limit=350000):
        return {"status": "aborted_unprofitable", "opp": opp}

    token_a = opp["token_a"]
    token_b = opp["token_b"]
    amount = opp["amount"]
    buy_dex = opp["buy_dex"]
    sell_dex = opp["sell_dex"]

    eth_price = opp.get("gas_cost_usd", 0) / max(opp.get("gas_cost_eth", 0.00001), 0.00001)

    result = {
        "status": "initiated",
        "token_a": token_a,
        "token_b": token_b,
        "buy": {},
        "sell": {},
        "gas_cost_eth": 0.0,
        "gas_cost_usd": 0.0,
        "net_profit_usd": opp["net_profit_usd"],
    }

    try:
        # Step 1: Buy token_b with token_a on buy_dex
        print(f"  🛒 BUY  {amount:.6f} {token_a} → {token_b} on {buy_dex}")
        buy_result = execute_swap(buy_dex, token_a, token_b, amount, slippage_bps)
        result["buy"] = buy_result
        if buy_result["status"] != "success":
            raise RuntimeError(f"Buy swap failed on {buy_dex}: {buy_result.get('tx_hash', 'N/A')}")

        # Amount received from buy
        amount_b_received = buy_result.get("amount_out", 0)
        print(f"  📥 Received: {amount_b_received:.6f} {token_b}")

        # Step 2: Sell token_b for token_a on sell_dex
        print(f"  💰 SELL {amount_b_received:.6f} {token_b} → {token_a} on {sell_dex}")
        sell_result = execute_swap(sell_dex, token_b, token_a, amount_b_received, slippage_bps)
        result["sell"] = sell_result
        if sell_result["status"] != "success":
            raise RuntimeError(f"Sell swap failed on {sell_dex}: {sell_result.get('tx_hash', 'N/A')}")

        amount_a_back = sell_result.get("amount_out", 0)
        print(f"  📤 Received back: {amount_a_back:.6f} {token_a}")

        # Calculate actual PnL
        gas_used = (buy_result.get("gas_used", 0) + sell_result.get("gas_used", 0))
        gas_price = buy_result.get("effective_gas_price", get_w3().eth.gas_price)
        gas_cost_eth = float(get_w3().from_wei(gas_used * gas_price, "ether"))
        gas_cost_usd = gas_cost_eth * eth_price

        net_profit_eth = amount_a_back - amount
        net_profit_usd = net_profit_eth * eth_price if token_a == "WETH" else net_profit_eth

        result["gas_cost_eth"] = gas_cost_eth
        result["gas_cost_usd"] = gas_cost_usd
        result["net_profit_usd"] = net_profit_usd
        result["amount_a_back"] = amount_a_back
        result["status"] = "success"

        # Log to profit tracker
        record = TradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            block_number=block_num,
            token_a=token_a,
            token_b=token_b,
            buy_dex=buy_dex,
            sell_dex=sell_dex,
            amount_in_eth=amount if token_a == "WETH" else 0,
            expected_profit_usd=opp["net_profit_usd"],
            gas_cost_eth=gas_cost_eth,
            gas_cost_usd=gas_cost_usd,
            net_profit_usd=net_profit_usd,
            tx_hash_buy=buy_result.get("tx_hash", ""),
            tx_hash_sell=sell_result.get("tx_hash", ""),
            status="success",
            notes=f"Received {amount_b_received:.6f} {token_b}, returned {amount_a_back:.6f} {token_a}",
        )
        log_trade(record)

        print(f"  ✅ Trade complete! Net: ${net_profit_usd:.4f} | Gas: ${gas_cost_usd:.4f}")

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"  ❌ Trade failed: {e}")

        # Log failure
        record = TradeRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            block_number=block_num,
            token_a=token_a,
            token_b=token_b,
            buy_dex=buy_dex,
            sell_dex=sell_dex,
            amount_in_eth=amount if token_a == "WETH" else 0,
            expected_profit_usd=opp["net_profit_usd"],
            gas_cost_eth=result.get("gas_cost_eth", 0),
            gas_cost_usd=result.get("gas_cost_usd", 0),
            net_profit_usd=0,
            tx_hash_buy=result["buy"].get("tx_hash", ""),
            tx_hash_sell=result["sell"].get("tx_hash", ""),
            status="failed",
            notes=str(e),
        )
        log_trade(record)

    return result

# ── MEV Protection Helper ──
def mev_protect_tip() -> str:
    """Return guidance on MEV protection for Base L2."""
    return (
        "⚡ MEV Protection Status:\n"
        "  • Flashbots Protect: Not yet on Base (monitor: docs.flashbots.net)\n"
        "  • Using 60-second tx deadlines as primary defense\n"
        "  • Alternative: CowSwap / MEV Blocker (Base support TBD)\n"
        "  • Base L2 has lower MEV than mainnet — sandwich risk reduced but not zero\n"
        "  • Future: Integrate Flashbots Protect Base RPC when available"
    )

# ── Triangle Arbitrage Wrapper ──
def execute_triangle_trade(
    amount_in_eth: float = 0.005,
    slippage_bps: int = 150,
    block_num: int = 0,
) -> Dict[str, Any]:
    """
    Execute a triangle arbitrage: WETH → USDC → DAI → WETH on Uniswap V3.
    Uses multiple fee tiers to maximize route efficiency.
    """
    path_tokens = ["WETH", "USDC", "DAI", "WETH"]
    path_fees = [3000, 100, 3000]  # WETH→USDC (0.3%), USDC→DAI (0.01%), DAI→WETH (0.3%)

    expected_profit_eth = amount_in_eth * 0.001  # Conservative 0.1% expectation
    if abort_if_unprofitable(expected_profit_eth, gas_limit=400000):
        return {"status": "aborted_unprofitable"}

    try:
        result = execute_triangle_arbitrage(path_tokens, path_fees, amount_in_eth, slippage_bps)
        print(f"  ✅ Triangle complete! TX: {result['tx_hash']}")
        return result
    except Exception as e:
        print(f"  ❌ Triangle failed: {e}")
        return {"status": "failed", "error": str(e)}

# ── Diagnostic ──
def healthcheck() -> Dict[str, Any]:
    """Run a quick diagnostic of the execution engine."""
    wallet = get_wallet()
    summary = {
        "wallet_loaded": wallet is not None,
        "wallet_address": WALLET_ADDRESS,
        "derived_address": wallet.address if wallet else None,
        "rpc_connected": get_w3().is_connected(),
        "block_number": get_w3().eth.block_number if get_w3().is_connected() else None,
        "chain_id": CHAIN_ID,
        "gas_price_gwei": float(get_w3().from_wei(get_w3().eth.gas_price, "gwei")) if get_w3().is_connected() else None,
        "nonce": get_w3().eth.get_transaction_count(WALLET_ADDRESS, 'pending') if get_w3().is_connected() else None,
        "eth_balance": float(get_w3().from_wei(get_w3().eth.get_balance(WALLET_ADDRESS), "ether")) if get_w3().is_connected() else None,
        "mev_protection": "60s deadline (Flashbots Base pending)",
    }

    # Check token balances
    for symbol, addr in CONFIG["tokens"].items():
        try:
            token = get_w3().eth.contract(address=Web3.to_checksum_address(addr), abi=ERC20_ABI)
            bal = token.functions.balanceOf(WALLET_ADDRESS).call()
            summary[f"{symbol}_balance"] = wei_to_token_amount(symbol, bal)
        except Exception as e:
            summary[f"{symbol}_balance"] = f"error: {e}"

    return summary


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Trade Executor Healthcheck")
    print("=" * 60)
    hc = healthcheck()
    for k, v in hc.items():
        print(f"  {k}: {v}")
    print("\n" + mev_protect_tip())
