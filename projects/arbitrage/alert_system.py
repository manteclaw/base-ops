#!/usr/bin/env python3
"""
Arbitrage Alert System for Manteclaw
Enhances arbitrage_bot.py with alert notifications + webhook output.

Supports:
  - Local file logging (alerts.txt, alerts.json)
  - Discord webhook (DISCORD_WEBHOOK_URL env)
  - Telegram bot (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env)
  - Generic HTTP POST (WEBHOOK_URL env)

Usage:
    # Alerts are auto-triggered by arbitrage_bot.py
    # Or run standalone to test:
    python3 projects/arbitrage/alert_system.py test
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ALERTS_FILE = Path("/root/.openclaw/workspace/projects/arbitrage/alerts.txt")
ALERTS_JSON = Path("/root/.openclaw/workspace/projects/arbitrage/alerts.json")
MAX_ALERTS = 1000  # Rotate after this many

# Webhook env vars
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip()

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

# Levels that trigger webhooks (exclude low-noise opportunity)
WEBHOOK_LEVELS = {"profitable", "high_profit", "executed", "failed", "low_balance", "error"}


def rotate_logs():
    """Rotate alert files if they get too large."""
    if ALERTS_FILE.exists() and ALERTS_FILE.stat().st_size > 5 * 1024 * 1024:  # 5MB
        backup = ALERTS_FILE.with_suffix(".txt.bak")
        ALERTS_FILE.rename(backup)
        print(f"Rotated alerts log to {backup}")
    
    if ALERTS_JSON.exists() and ALERTS_JSON.stat().st_size > 5 * 1024 * 1024:
        backup = ALERTS_JSON.with_suffix(".json.bak")
        ALERTS_JSON.rename(backup)


def _send_discord(message: str, data: dict = None):
    """Send alert to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    payload = {"content": message}
    if data:
        embeds = [{
            "title": f"Alert: {data.get('level', 'info')}",
            "description": json.dumps(data, default=str, indent=2)[:2000],
            "color": 0x00ff00 if data.get("level") == "executed" else 0xff0000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
        payload["embeds"] = embeds
    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[webhook] Discord failed: {e}")
        return False


def _send_telegram(message: str, data: dict = None):
    """Send alert to Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    text = message
    if data:
        text += f"\n\n```\n{json.dumps(data, default=str, indent=2)[:1000]}\n```"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[webhook] Telegram failed: {e}")
        return False


def _send_generic_webhook(message: str, data: dict = None):
    """Send alert to generic HTTP POST endpoint."""
    if not WEBHOOK_URL:
        return False
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "level": data.get("level") if data else "info",
        "data": data or {},
        "source": "manteclaw-arbitrage",
    }
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[webhook] Generic POST failed: {e}")
        return False


def _dispatch_webhooks(level: str, message: str, data: dict = None):
    """Dispatch to all configured webhooks if level is significant."""
    if level not in WEBHOOK_LEVELS:
        return
    results = {}
    if DISCORD_WEBHOOK_URL:
        results["discord"] = _send_discord(message, data)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        results["telegram"] = _send_telegram(message, data)
    if WEBHOOK_URL:
        results["generic"] = _send_generic_webhook(message, data)
    if results:
        print(f"[webhook] dispatched: {results}")


def send_alert(level: str, message: str, data: dict = None):
    """Send an alert. Writes to alerts.txt and alerts.json, plus webhooks."""
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
    if len(alerts) > MAX_ALERTS:
        alerts = alerts[-MAX_ALERTS:]
    
    with open(ALERTS_JSON, "w") as f:
        json.dump(alerts, f, indent=2, default=str)
    
    # Webhooks
    _dispatch_webhooks(level, message, {**(data or {}), "level": level, "timestamp": ts})
    
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
    
    # Webhook status
    print("\nWebhook config:")
    print(f"  Discord:    {'✅' if DISCORD_WEBHOOK_URL else '❌'} {DISCORD_WEBHOOK_URL[:40] + '...' if len(DISCORD_WEBHOOK_URL) > 40 else DISCORD_WEBHOOK_URL}")
    print(f"  Telegram:   {'✅' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌'}")
    print(f"  Generic:    {'✅' if WEBHOOK_URL else '❌'} {WEBHOOK_URL[:40] + '...' if len(WEBHOOK_URL) > 40 else WEBHOOK_URL}")


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
