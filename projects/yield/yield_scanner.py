#!/usr/bin/env python3
"""
yield_scanner.py — Lane F Enhancement
Real-time DeFi yield aggregator for Base L2.
Queries DefiLlama Yields API for top protocols, returns best APY for USDC.
Uses selfheal.py retry wrappers for all HTTP calls.

Protocols monitored:
- Aave V3
- Morpho Blue
- Compound V3
- Fluid (Instadapp)
- Euler
- Curve
- Aerodrome

Usage:
    python3 yield_scanner.py                    # Full scan + best pick
    python3 yield_scanner.py --protocol aave    # Filter by protocol
    python3 yield_scanner.py --min-tvl 1000000  # Minimum TVL filter
    python3 yield_scanner.py --output json      # JSON output
"""

import sys
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Import selfheal retry wrappers
sys.path.insert(0, "/root/.openclaw/workspace")
from selfheal import retry, heal

# ── Config ──────────────────────────────────────────────────────────

DEFILLAMA_POOLS_URL = "https://yields.llama.fi/pools"

target_protocols = {
    "aave-v3": "Aave V3",
    "compound-v3": "Compound V3",
    "morpho-blue": "Morpho Blue",
    "fluid": "Fluid (Instadapp)",
    "euler": "Euler",
    "curve-dex": "Curve",
    "aerodrome": "Aerodrome",
    "uniswap-v3": "Uniswap V3",
}

# ── Core Functions ─────────────────────────────────────────────────

@heal(service="defillama", max_retries=5, base_delay=2.0)
def fetch_pools() -> List[Dict[str, Any]]:
    """Fetch all yield pools from DefiLlama."""
    import urllib.request
    import urllib.error
    
    req = urllib.request.Request(
        DEFILLAMA_POOLS_URL,
        headers={"Accept": "application/json", "User-Agent": "Manteclaw-YieldScanner/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        # DefiLlama returns {data: [...]} or just [...]
        pools = data.get("data", data) if isinstance(data, dict) else data
        return pools if isinstance(pools, list) else []


def filter_base_usdc(pools: List[Dict[str, Any]], min_tvl: float = 0) -> List[Dict[str, Any]]:
    """Filter pools to Base chain + USDC + target protocols."""
    results = []
    for p in pools:
        if p.get("chain") != "Base":
            continue
        if p.get("project") not in target_protocols:
            continue
        symbol = str(p.get("symbol", ""))
        if "USDC" not in symbol and "USDC" not in str(p.get("poolMeta", "")):
            continue
        tvl = p.get("tvlUsd", 0) or 0
        if tvl < min_tvl:
            continue
        results.append(p)
    return results


def score_pool(pool: Dict[str, Any]) -> float:
    """Risk-adjusted score: higher APY + higher TVL = better."""
    apy = pool.get("apy", 0) or 0
    tvl = pool.get("tvlUsd", 0) or 0
    # Log-scaled TVL bonus — prevents tiny pools with insane APY from ranking
    tvl_bonus = min(2.0, max(0, (tvl / 1_000_000) ** 0.3))
    # Penalize extreme APY outliers (>50%) — likely IL or temporary incentives
    if apy > 50:
        apy = 50 + (apy - 50) * 0.1
    return apy + tvl_bonus


def format_pool(pool: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize pool data for output."""
    project = pool.get("project", "")
    return {
        "protocol": target_protocols.get(project, project),
        "project_slug": project,
        "symbol": pool.get("symbol", "N/A"),
        "pool": pool.get("pool", "N/A"),
        "apy": round(pool.get("apy", 0) or 0, 2),
        "apy_base": round(pool.get("apyBase", 0) or 0, 2),
        "apy_reward": round(pool.get("apyReward", 0) or 0, 2) if pool.get("apyReward") else None,
        "tvl_usd": round(pool.get("tvlUsd", 0) or 0, 2),
        "stablecoin": pool.get("stablecoin", False),
        "il_risk": pool.get("ilRisk", "N/A"),
        "exposure": pool.get("exposure", "N/A"),
        "apy_pct_1d": round(pool.get("apyPct1D", 0) or 0, 3),
        "apy_pct_7d": round(pool.get("apyPct7D", 0) or 0, 3),
        "score": round(score_pool(pool), 2),
    }


def scan(min_tvl: float = 0, protocol_filter: Optional[str] = None) -> Dict[str, Any]:
    """Run full scan and return structured report."""
    raw_pools = fetch_pools()
    base_pools = filter_base_usdc(raw_pools, min_tvl=min_tvl)
    
    if protocol_filter:
        slug = protocol_filter.lower().replace(" ", "-")
        base_pools = [p for p in base_pools if slug in p.get("project", "")]
    
    formatted = [format_pool(p) for p in base_pools]
    formatted.sort(key=lambda x: x["score"], reverse=True)
    
    # Best pick by score
    best = formatted[0] if formatted else None
    
    # Summary by protocol
    by_protocol = {}
    for p in formatted:
        proto = p["protocol"]
        if proto not in by_protocol:
            by_protocol[proto] = {"best_apy": 0, "best_pool": None, "count": 0, "total_tvl": 0}
        by_protocol[proto]["count"] += 1
        by_protocol[proto]["total_tvl"] += p["tvl_usd"]
        if p["apy"] > by_protocol[proto]["best_apy"]:
            by_protocol[proto]["best_apy"] = p["apy"]
            by_protocol[proto]["best_pool"] = p
    
    return {
        "scan_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
        "chain": "Base",
        "token": "USDC",
        "pools_found": len(formatted),
        "best_pool": best,
        "top_pools": formatted[:10],
        "by_protocol": {k: {
            "best_apy": v["best_apy"],
            "pool_count": v["count"],
            "total_tvl_usd": round(v["total_tvl"], 2),
            "best_pool_symbol": v["best_pool"]["symbol"] if v["best_pool"] else None,
        } for k, v in by_protocol.items()},
    }


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Base L2 USDC Yield Scanner")
    parser.add_argument("--min-tvl", type=float, default=0, help="Minimum TVL in USD")
    parser.add_argument("--protocol", type=str, default=None, help="Filter by protocol name")
    parser.add_argument("--output", choices=["json", "table"], default="table", help="Output format")
    parser.add_argument("--save", type=str, default=None, help="Save JSON report to file")
    args = parser.parse_args()
    
    report = scan(min_tvl=args.min_tvl, protocol_filter=args.protocol)
    
    if args.output == "json":
        print(json.dumps(report, indent=2))
    else:
        print(f"\n{'='*70}")
        print(f"  YIELD SCANNER — Base L2 | USDC | {report['scan_time']}")
        print(f"{'='*70}")
        print(f"  Pools found: {report['pools_found']}")
        
        if report["best_pool"]:
            best = report["best_pool"]
            print(f"\n  🏆 BEST PICK: {best['protocol']} — {best['symbol']}")
            print(f"     APY: {best['apy']}% | TVL: ${best['tvl_usd']:,.0f} | Score: {best['score']}")
        
        print(f"\n  ── Top 10 Pools ──")
        for i, p in enumerate(report["top_pools"][:10], 1):
            reward_str = f" (+{p['apy_reward']}% rewards)" if p.get("apy_reward") else ""
            print(f"  {i:2}. {p['protocol']:18} | {p['symbol']:25} | {p['apy']:6.2f}% APY{reward_str} | TVL ${p['tvl_usd']:>14,.0f}")
        
        print(f"\n  ── Protocol Summary ──")
        for proto, stats in report["by_protocol"].items():
            print(f"  • {proto:18} — Best: {stats['best_apy']:.2f}% | Pools: {stats['pool_count']} | TVL: ${stats['total_tvl_usd']:,.0f}")
        print(f"{'='*70}\n")
    
    if args.save:
        with open(args.save, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[saved] Report written to {args.save}")
    
    return report


if __name__ == "__main__":
    main()
