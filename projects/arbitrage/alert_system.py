#!/usr/bin/env python3
"""
Arbitrage Alert System for Manteclaw
Enhances arbitrage_bot.py with alert notifications.

Alerts are written to projects/arbitrage/alerts.txt and can be
extended to send Discord/Slack/telegram notifications.

Usage:
    # Alerts are auto-triggered by arbitrage_bot.py when opportunities are found
    # Or run standalone to test:
    python3 projects/arbitrage/alert_system.py test
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ALERTS_FILE = Path("/root/.openclaw/workspace/projects/arbitrage/alerts.txt")
ALERTS_JSON = Path("/root/.openclaw/workspace/projects/arbitrage/alerts.json")
MAX_ALERTS = 1000  # Rotate after this many

# Alert severity levels
SEVERITY = {
    "opportunity": "ℹ️",      # Basic arbitrage found
    "profitable": "💰",       # Net profit > $1
    "high_profit": "🚀",      # Net profit > $5
    "executed": "✅",         # Trade executed
    "failed": "❌",           # Trade failed
    "low_balance": "⚠️",      # Wallet balance low
    "error": "🔥",            # System error
}


def rotate_logs():
    """Rotate alert files if they get too large."""
    if ALERTS_FILE.exists() and ALERTS_FILE.stat().st_size > 5 * 1024 * 1024:  # 5MB
        backup = ALERTS_FILE.with_suffix(".txt.bak")
        ALERTS_FILE.rename(backup)
        print(f"Rotated alerts log to {backup}")
    
    if ALERTS_JSON.exists() and ALERTS_JSON.stat().st_size > 5 * 1024 * 1024:
        backup = ALERTS_JSON.with_suffix(".json.bak")
        ALERTS_JSON.rename(backup)


def send_alert(level: str, message: str, data: dict = None):
    """Send an alert. Writes to alerts.txt and alerts.json."""
    rotate_logs()
    
    ts = datetime.now(timezone.utc).isoformat()
    icon = SEVERITY.get(level, "📢")
    
    # Text log
    line = f"[{ts}] {icon} [{level.upper()}] {message}"
    with open(ALERTS_FILE, "a") as f:
        f.write(line + "\n")
        if data:
            f.write(json.dumps({"timestamp": ts, "level": level, **data}, default=str) + "\n")
    
    # Structured JSON log
    entry = {
        "timestamp": ts,
        "level": level,
        "message": message,
        "data": data or {},
    }
    
    alerts = []
    if ALERTS_JSON.exists():
        try:
            with open(ALERTS_JSON, "r") as f:
                alerts = json.load(f)
        except:
            alerts = []
    
    alerts.append(entry)
    # Trim if too large
    if len(alerts) > MAX_ALERTS:
        alerts = alerts[-MAX_ALERTS:]
    
    with open(ALERTS_JSON, "w") as f:
        json.dump(alerts, f, indent=2, default=str)
    
    # Also print to stdout
    print(line)
    return entry


def alert_opportunity(opp: dict, block_num: int):
    """Alert when arbitrage opportunity is found."""
    profit = opp.get("net_profit_usd", 0)
    
    if profit >= 5:
        level = "high_profit"
    elif profit >= 1:
        level = "profitable"
    else:
        level = "opportunity"
    
    msg = (
        f"Arbitrage: {opp['token_a']}/{opp['token_b']} | "
        f"${profit:.2f} net | buy {opp['buy_dex']} → sell {opp['sell_dex']} | "
        f"diff: +{opp['price_diff_pct']:.3f}%"
    )
    
    return send_alert(level, msg, {
        "block": block_num,
        **opp
    })


def alert_executed(opp: dict, tx_hash: str = None, gas_cost: float = None):
    """Alert when trade is executed."""
    msg = f"Trade EXECUTED: {opp['token_a']}/{opp['token_b']} | net ${opp['net_profit_usd']:.2f}"
    data = {
        "tx_hash": tx_hash,
        "gas_cost_usd": gas_cost,
        **opp
    }
    return send_alert("executed", msg, data)


def alert_failed(opp: dict, reason: str):
    """Alert when trade fails."""
    msg = f"Trade FAILED: {opp['token_a']}/{opp['token_b']} | reason: {reason}"
    return send_alert("failed", msg, opp)


def alert_low_balance(balance_eth: float, min_eth: float):
    """Alert when wallet balance is low."""
    msg = f"Low balance: {balance_eth:.6f} ETH (min: {min_eth:.6f} ETH)"
    return send_alert("low_balance", msg, {"balance_eth": balance_eth, "min_eth": min_eth})


def alert_error(error: str, context: dict = None):
    """Alert on system error."""
    return send_alert("error", error, context)


def get_recent_alerts(n: int = 10, level: str = None) -> list:
    """Get recent alerts, optionally filtered by level."""
    if not ALERTS_JSON.exists():
        return []
    
    try:
        with open(ALERTS_JSON) as f:
            alerts = json.load(f)
    except:
        return []
    
    if level:
        alerts = [a for a in alerts if a["level"] == level]
    
    return alerts[-n:]


def print_summary():
    """Print alert summary."""
    if not ALERTS_JSON.exists():
        print("No alerts yet.")
        return
    
    try:
        with open(ALERTS_JSON) as f:
            alerts = json.load(f)
    except:
        print("Could not read alerts.")
        return
    
    print(f"Total alerts: {len(alerts)}")
    
    by_level = {}
    for a in alerts:
        by_level[a["level"]] = by_level.get(a["level"], 0) + 1
    
    print("\nBy level:")
    for level, count in sorted(by_level.items(), key=lambda x: -x[1]):
        icon = SEVERITY.get(level, "📢")
        print(f"  {icon} {level}: {count}")
    
    # Last 5 alerts
    print("\nLast 5 alerts:")
    for a in alerts[-5:]:
        ts = a["timestamp"].split("T")[1][:8] if "T" in a["timestamp"] else a["timestamp"][11:19]
        icon = SEVERITY.get(a["level"], "📢")
        print(f"  [{ts}] {icon} {a['message'][:80]}")


# ── Integration with arbitrage_bot.py ──
# To use in arbitrage_bot.py, replace log_opportunity() calls with:
#   from alert_system import alert_opportunity
#   alert_opportunity(opp, block_num)
# And add alert_low_balance(), alert_error(), alert_executed() calls as needed.

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 Testing alert system...")
        send_alert("opportunity", "Test alert: WETH/USDC opportunity found", {"profit": 2.5})
        send_alert("profitable", "Test alert: $3.20 profit on WETH/DAI", {"profit": 3.2})
        send_alert("high_profit", "Test alert: $7.50 profit on USDC/DAI", {"profit": 7.5})
        send_alert("low_balance", "Test alert: Balance 0.001 ETH, need 0.0025", {"balance": 0.001})
        print("\nAlert summary:")
        print_summary()
    else:
        print_summary()
