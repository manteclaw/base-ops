#!/usr/bin/env python3
"""
Cross-Chain Bridge Optimizer for Base L2 Agents
================================================
Compares bridge fees across Stargate, Across, Hop, and Orbiter
for Base↔Arbitrum↔Optimism routes. Returns cheapest + fastest option.

Price: 3 USDC
Author: Manteclaw
License: MIT
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from decimal import Decimal
import json

# ─── Chain & Token Constants ──────────────────────────────────────────────

CHAIN_IDS = {
    "base": 8453,
    "arbitrum": 42161,
    "optimism": 10,
    "ethereum": 1,
}

USDC_ADDRESSES = {
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base
    42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Arbitrum
    10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",      # Optimism
    1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",      # Ethereum
}

ETH_ADDRESSES = {
    8453: "0x4200000000000000000000000000000000000006",     # Base WETH
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",    # Arbitrum WETH
    10: "0x4200000000000000000000000000000000000006",       # Optimism WETH
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",      # Ethereum WETH
}

# Hop chain slugs
HOP_CHAINS = {
    "base": "base",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "ethereum": "ethereum",
}

# ─── Data Models ──────────────────────────────────────────────────────────

@dataclass
class BridgeQuote:
    bridge: str
    from_chain: str
    to_chain: str
    token: str
    amount: Decimal
    amount_out: Decimal
    total_fee: Decimal
    fee_pct: float
    estimated_time_sec: int
    gas_estimate_usd: float
    details: Dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.error is None and self.amount_out > 0

    @property
    def net_received_usd(self) -> float:
        return float(self.amount_out)

    def to_dict(self) -> dict:
        return {
            "bridge": self.bridge,
            "from_chain": self.from_chain,
            "to_chain": self.to_chain,
            "token": self.token,
            "amount": str(self.amount),
            "amount_out": str(self.amount_out),
            "total_fee_usd": str(self.total_fee),
            "fee_pct": self.fee_pct,
            "estimated_time_sec": self.estimated_time_sec,
            "gas_estimate_usd": self.gas_estimate_usd,
            "net_received_usd": self.net_received_usd,
            "details": self.details,
            "error": self.error,
        }

# ─── Across Protocol ──────────────────────────────────────────────────────

async def get_across_fee(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: Decimal,
    session: aiohttp.ClientSession,
) -> BridgeQuote:
    """
    Query Across Protocol /suggested-fees endpoint.
    No API key needed for quotes (required for production swaps).
    """
    try:
        origin_id = CHAIN_IDS.get(from_chain.lower())
        dest_id = CHAIN_IDS.get(to_chain.lower())
        if not origin_id or not dest_id:
            return BridgeQuote(
                bridge="across",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Unsupported chain pair: {from_chain} → {to_chain}",
            )

        token_lower = token.lower()
        token_addrs = USDC_ADDRESSES if token_lower == "usdc" else ETH_ADDRESSES
        input_token = token_addrs.get(origin_id)
        output_token = token_addrs.get(dest_id)

        if not input_token or not output_token:
            return BridgeQuote(
                bridge="across",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Token {token} not supported on one of the chains",
            )

        # Amount in token decimals (USDC=6, ETH=18)
        decimals = 6 if token_lower == "usdc" else 18
        amount_raw = int(amount * (10 ** decimals))

        url = "https://app.across.to/api/suggested-fees"
        params = {
            "inputToken": input_token,
            "outputToken": output_token,
            "originChainId": str(origin_id),
            "destinationChainId": str(dest_id),
            "amount": str(amount_raw),
        }

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Across API returned {resp.status}: {text[:200]}")
            data = await resp.json()

        # Parse fee breakdown
        total_relay_fee = Decimal(str(data.get("totalRelayFee", {}).get("total", "0"))) / (10 ** decimals)
        lp_fee_pct = float(data.get("lpFee", {}).get("pct", "0")) / 1e18 * 100
        relayer_capital = Decimal(str(data.get("relayerCapitalFee", {}).get("total", "0"))) / (10 ** decimals)
        relayer_gas = Decimal(str(data.get("relayerGasFee", {}).get("total", "0"))) / (10 ** decimals)
        expected_time = int(data.get("expectedFillTimeSec", 120))
        is_amount_too_low = data.get("isAmountTooLow", False)

        # outputAmount is what user receives
        amount_out_raw = data.get("outputAmount", str(amount_raw))
        amount_out = Decimal(str(amount_out_raw)) / (10 ** decimals)

        total_fee = amount - amount_out
        fee_pct = float(total_fee / amount * 100) if amount > 0 else 0.0

        return BridgeQuote(
            bridge="across",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=amount_out,
            total_fee=total_fee,
            fee_pct=fee_pct,
            estimated_time_sec=expected_time,
            gas_estimate_usd=0.0,  # Included in relayerGasFee
            details={
                "lp_fee_pct": lp_fee_pct,
                "relayer_capital_fee": str(relayer_capital),
                "relayer_gas_fee": str(relayer_gas),
                "is_amount_too_low": is_amount_too_low,
                "api_response": data,
            },
        )

    except Exception as e:
        return BridgeQuote(
            bridge="across",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=Decimal("0"),
            total_fee=Decimal("0"),
            fee_pct=0.0,
            estimated_time_sec=0,
            gas_estimate_usd=0.0,
            error=f"Across error: {str(e)[:200]}",
            details={"exception": str(e)},
        )


# ─── Hop Protocol ─────────────────────────────────────────────────────────

async def get_hop_fee(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: Decimal,
    session: aiohttp.ClientSession,
) -> BridgeQuote:
    """
    Query Hop Protocol /v1/quote endpoint.
    Free public API (self-host recommended for production).
    """
    try:
        from_slug = HOP_CHAINS.get(from_chain.lower())
        to_slug = HOP_CHAINS.get(to_chain.lower())
        if not from_slug or not to_slug:
            return BridgeQuote(
                bridge="hop",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Hop unsupported chain pair: {from_chain} → {to_chain}",
            )

        token_upper = token.upper()
        if token_upper not in ("USDC", "ETH", "USDT", "DAI", "MATIC"):
            return BridgeQuote(
                bridge="hop",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Hop does not support token: {token}",
            )

        decimals = 6 if token_upper == "USDC" else 18
        amount_raw = int(amount * (10 ** decimals))

        url = "https://api.hop.exchange/v1/quote"
        params = {
            "amount": str(amount_raw),
            "token": token_upper,
            "fromChain": from_slug,
            "toChain": to_slug,
            "slippage": "0.5",
            "network": "mainnet",
        }

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Hop API returned {resp.status}: {text[:200]}")
            data = await resp.json()

        bonder_fee_raw = data.get("bonderFee", "0")
        estimated_received_raw = data.get("estimatedRecieved", "0")
        amount_out_raw = data.get("amountOutMin", "0")

        bonder_fee = Decimal(str(bonder_fee_raw)) / (10 ** decimals)
        amount_out = Decimal(str(estimated_received_raw)) / (10 ** decimals)

        # Total fee = input - output
        total_fee = amount - amount_out
        fee_pct = float(total_fee / amount * 100) if amount > 0 else 0.0

        # Hop L2→L2 is typically 2-5 minutes
        est_time = 180 if from_chain.lower() != "ethereum" and to_chain.lower() != "ethereum" else 600

        return BridgeQuote(
            bridge="hop",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=amount_out,
            total_fee=total_fee,
            fee_pct=fee_pct,
            estimated_time_sec=est_time,
            gas_estimate_usd=0.0,  # Included in bonderFee
            details={
                "bonder_fee": str(bonder_fee),
                "amount_out_min": str(Decimal(str(amount_out_raw)) / (10 ** decimals)),
                "slippage": "0.5%",
                "api_response": data,
            },
        )

    except Exception as e:
        return BridgeQuote(
            bridge="hop",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=Decimal("0"),
            total_fee=Decimal("0"),
            fee_pct=0.0,
            estimated_time_sec=0,
            gas_estimate_usd=0.0,
            error=f"Hop error: {str(e)[:200]}",
            details={"exception": str(e)},
        )


# ─── Stargate (Estimated) ─────────────────────────────────────────────────

async def get_stargate_fee(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: Decimal,
    session: aiohttp.ClientSession,
) -> BridgeQuote:
    """
    Estimate Stargate fees (no public fee API — uses known fee structure).
    Stargate V2: ~0.06% protocol fee + LP fee ~0.30% + LayerZero messaging fee.
    """
    try:
        # Stargate supports Base, Arbitrum, Optimism, Ethereum
        supported = {"base", "arbitrum", "optimism", "ethereum"}
        if from_chain.lower() not in supported or to_chain.lower() not in supported:
            return BridgeQuote(
                bridge="stargate",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Stargate unsupported chain pair: {from_chain} → {to_chain}",
            )

        token_lower = token.lower()
        if token_lower not in ("usdc", "usdt", "eth"):
            return BridgeQuote(
                bridge="stargate",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Stargate does not support token: {token}",
            )

        # Fee model (from Stargate docs & empirical data)
        protocol_fee_pct = Decimal("0.06")   # 0.06%
        lp_fee_pct = Decimal("0.30")         # 0.30% average
        lz_fee_usd = Decimal("0.50")         # LayerZero messaging fee

        # Add destination gas buffer (varies by chain congestion)
        dest_gas_usd = {
            "base": Decimal("0.10"),
            "arbitrum": Decimal("0.15"),
            "optimism": Decimal("0.08"),
            "ethereum": Decimal("2.00"),
        }.get(to_chain.lower(), Decimal("0.20"))

        protocol_fee = amount * protocol_fee_pct / 100
        lp_fee = amount * lp_fee_pct / 100
        total_fee = protocol_fee + lp_fee + lz_fee_usd + dest_gas_usd
        amount_out = amount - total_fee

        if amount_out < 0:
            amount_out = Decimal("0")
            total_fee = amount

        fee_pct = float(total_fee / amount * 100) if amount > 0 else 0.0

        # Stargate V2 settlement: ~2-5 minutes for L2→L2
        est_time = 180

        return BridgeQuote(
            bridge="stargate",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=amount_out,
            total_fee=total_fee,
            fee_pct=fee_pct,
            estimated_time_sec=est_time,
            gas_estimate_usd=float(dest_gas_usd),
            details={
                "protocol_fee_pct": float(protocol_fee_pct),
                "lp_fee_pct": float(lp_fee_pct),
                "layerzero_fee_usd": str(lz_fee_usd),
                "destination_gas_usd": str(dest_gas_usd),
                "note": "Estimated fees — Stargate has no public fee API",
            },
        )

    except Exception as e:
        return BridgeQuote(
            bridge="stargate",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=Decimal("0"),
            total_fee=Decimal("0"),
            fee_pct=0.0,
            estimated_time_sec=0,
            gas_estimate_usd=0.0,
            error=f"Stargate error: {str(e)[:200]}",
        )


# ─── Orbiter Finance (Estimated) ─────────────────────────────────────────

async def get_orbiter_fee(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: Decimal,
    session: aiohttp.ClientSession,
) -> BridgeQuote:
    """
    Estimate Orbiter Finance fees (no public fee API — uses known fee structure).
    Orbiter: Fixed maker fee (~0.0005-0.001 ETH equiv) + destination gas.
    """
    try:
        supported = {"base", "arbitrum", "optimism", "ethereum", "polygon", "zksync", "linea", "scroll"}
        if from_chain.lower() not in supported or to_chain.lower() not in supported:
            return BridgeQuote(
                bridge="orbiter",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Orbiter unsupported chain pair: {from_chain} → {to_chain}",
            )

        token_lower = token.lower()
        if token_lower not in ("eth", "usdc", "usdt", "dai"):
            return BridgeQuote(
                bridge="orbiter",
                from_chain=from_chain,
                to_chain=to_chain,
                token=token,
                amount=amount,
                amount_out=Decimal("0"),
                total_fee=Decimal("0"),
                fee_pct=0.0,
                estimated_time_sec=0,
                gas_estimate_usd=0.0,
                error=f"Orbiter does not support token: {token}",
            )

        # Orbiter fee model (from docs & empirical data)
        # Maker fee is a small fixed amount in ETH equivalent
        maker_fee_eth = Decimal("0.0003")  # ~$0.60 at $2000 ETH
        eth_price_usd = Decimal("2000")    # Can be made dynamic
        maker_fee_usd = maker_fee_eth * eth_price_usd

        # Destination gas (paid by Orbiter, factored into fee)
        dest_gas_usd = {
            "base": Decimal("0.05"),
            "arbitrum": Decimal("0.08"),
            "optimism": Decimal("0.04"),
            "ethereum": Decimal("1.50"),
            "polygon": Decimal("0.02"),
        }.get(to_chain.lower(), Decimal("0.10"))

        total_fee = maker_fee_usd + dest_gas_usd
        amount_out = amount - total_fee

        if amount_out < 0:
            amount_out = Decimal("0")
            total_fee = amount

        fee_pct = float(total_fee / amount * 100) if amount > 0 else 0.0

        # Orbiter is very fast: ~10-30 seconds for most routes
        est_time = 20

        return BridgeQuote(
            bridge="orbiter",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=amount_out,
            total_fee=total_fee,
            fee_pct=fee_pct,
            estimated_time_sec=est_time,
            gas_estimate_usd=float(dest_gas_usd),
            details={
                "maker_fee_usd": str(maker_fee_usd),
                "destination_gas_usd": str(dest_gas_usd),
                "eth_price_used": str(eth_price_usd),
                "note": "Estimated fees — Orbiter has no public fee API",
            },
        )

    except Exception as e:
        return BridgeQuote(
            bridge="orbiter",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            amount_out=Decimal("0"),
            total_fee=Decimal("0"),
            fee_pct=0.0,
            estimated_time_sec=0,
            gas_estimate_usd=0.0,
            error=f"Orbiter error: {str(e)[:200]}",
        )


# ─── Core Optimizer ───────────────────────────────────────────────────────

async def find_best_bridge(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: Decimal,
    bridges: Optional[List[str]] = None,
    prefer_speed: bool = False,
) -> Dict:
    """
    Query all configured bridges and return the cheapest (or fastest) option.

    Args:
        from_chain: Source chain (base, arbitrum, optimism, ethereum)
        to_chain: Destination chain
        token: Token symbol (usdc, eth, usdt, dai)
        amount: Amount to bridge (in token units)
        bridges: List of bridges to check. Default: ["across", "hop", "stargate", "orbiter"]
        prefer_speed: If True, rank by speed instead of cost

    Returns:
        Dict with "best" quote, "all" quotes, and "recommendation" text.
    """
    if bridges is None:
        bridges = ["across", "hop", "stargate", "orbiter"]

    async with aiohttp.ClientSession() as session:
        tasks = []
        for bridge in bridges:
            bridge = bridge.lower()
            if bridge == "across":
                tasks.append(get_across_fee(from_chain, to_chain, token, amount, session))
            elif bridge == "hop":
                tasks.append(get_hop_fee(from_chain, to_chain, token, amount, session))
            elif bridge == "stargate":
                tasks.append(get_stargate_fee(from_chain, to_chain, token, amount, session))
            elif bridge == "orbiter":
                tasks.append(get_orbiter_fee(from_chain, to_chain, token, amount, session))

        quotes = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and invalid quotes
    valid_quotes = []
    for q in quotes:
        if isinstance(q, Exception):
            continue
        if q.is_valid:
            valid_quotes.append(q)

    if not valid_quotes:
        return {
            "success": False,
            "error": "No valid quotes returned from any bridge",
            "all_quotes": [q.to_dict() for q in quotes if not isinstance(q, Exception)],
            "best": None,
            "recommendation": "No bridges returned valid quotes. Check chain/token support.",
        }

    # Sort by cost (default) or speed
    if prefer_speed:
        valid_quotes.sort(key=lambda q: q.estimated_time_sec)
    else:
        valid_quotes.sort(key=lambda q: q.total_fee)

    best = valid_quotes[0]

    # Build recommendation text
    if prefer_speed:
        rec = (
            f"⚡ Fastest: **{best.bridge.upper()}** — "
            f"{best.estimated_time_sec}s, ${float(best.total_fee):.4f} fee "
            f"({best.fee_pct:.3f}%), receive ${float(best.amount_out):.2f}"
        )
    else:
        rec = (
            f"💰 Cheapest: **{best.bridge.upper()}** — "
            f"${float(best.total_fee):.4f} fee ({best.fee_pct:.3f}%), "
            f"{best.estimated_time_sec}s, receive ${float(best.amount_out):.2f}"
        )

    # If second-best is close in cost but much faster, mention it
    if len(valid_quotes) >= 2 and not prefer_speed:
        second = valid_quotes[1]
        cost_diff = float(second.total_fee - best.total_fee)
        time_diff = second.estimated_time_sec - best.estimated_time_sec
        if cost_diff < 1.0 and time_diff < -60:
            rec += f"\n⚡ Alternative: {second.bridge.upper()} is only ${cost_diff:.2f} more but {abs(time_diff)}s faster."

    return {
        "success": True,
        "best": best.to_dict(),
        "all_quotes": [q.to_dict() for q in valid_quotes],
        "recommendation": rec,
        "from_chain": from_chain,
        "to_chain": to_chain,
        "token": token,
        "amount": str(amount),
        "prefer_speed": prefer_speed,
    }


# ─── CLI / Direct Execution ───────────────────────────────────────────────

async def main():
    import sys
    args = sys.argv[1:]
    if len(args) < 4:
        print("Usage: bridge_optimizer.py <from_chain> <to_chain> <token> <amount> [--speed]")
        print("Example: bridge_optimizer.py base arbitrum usdc 1000")
        print("Chains: base, arbitrum, optimism, ethereum")
        print("Tokens: usdc, eth, usdt, dai")
        sys.exit(1)

    from_chain, to_chain, token, amount_str = args[0], args[1], args[2], args[3]
    prefer_speed = "--speed" in args

    try:
        amount = Decimal(amount_str)
    except Exception:
        print(f"Invalid amount: {amount_str}")
        sys.exit(1)

    print(f"🔍 Comparing bridges for {amount} {token.upper()} from {from_chain} → {to_chain}...\n")

    result = await find_best_bridge(from_chain, to_chain, token, amount, prefer_speed=prefer_speed)

    if not result["success"]:
        print(f"❌ Error: {result['error']}")
        for q in result.get("all_quotes", []):
            if q.get("error"):
                print(f"  • {q['bridge']}: {q['error']}")
        sys.exit(1)

    print(f"{result['recommendation']}\n")
    print("─" * 60)
    print("All quotes:")
    for q in result["all_quotes"]:
        speed = "⚡" if q["estimated_time_sec"] <= 30 else "🐇" if q["estimated_time_sec"] <= 180 else "🐢"
        print(
            f"  {speed} {q['bridge'].upper():10} | "
            f"fee ${float(q['total_fee_usd']):.4f} ({q['fee_pct']:.3f}%) | "
            f"out ${float(q['amount_out']):.2f} | "
            f"time {q['estimated_time_sec']}s"
        )
    print("─" * 60)
    print(f"\n💡 Best route: {result['best']['bridge'].upper()}")
    print(f"   Net received: ${float(result['best']['amount_out']):.2f}")
    print(f"   Total fee:    ${float(result['best']['total_fee_usd']):.4f} ({result['best']['fee_pct']:.3f}%)")
    print(f"   Est. time:    {result['best']['estimated_time_sec']} seconds")

    # JSON dump for piping
    print("\n📦 Full JSON:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
