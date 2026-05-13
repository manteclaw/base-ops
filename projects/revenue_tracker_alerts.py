#!/usr/bin/env python3
"""
Revenue Tracker with Live Alerts
Adds alert triggers to the existing revenue tracker.
"""
import json, sys, os, time
from datetime import datetime

ALERTS = []

def alert(level, message):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {level}: {message}"
    ALERTS.append(line)
    print(line, file=sys.stderr)

def check_litcoiin(data):
    lit = data.get('litcoiin', {})
    balance = lit.get('balance', 0)
    if balance >= 50000:
        alert("🚨 CLAIM_READY", f"Litcoiin balance {balance:,} >= 50,000 threshold — execute claim now")
    elif balance >= 45000:
        alert("⚠️ CLAIM_SOON", f"Litcoiin balance {balance:,} — approaching claim threshold")

def check_nookplot(data):
    bounties = data.get('nookplot_bounties', {})
    new_matches = bounties.get('new_matches', [])
    if new_matches:
        alert("🎯 NEW_BOUNTY", f"{len(new_matches)} Nookplot bounties match our skills: {new_matches}")

def check_0xwork(data):
    tasks = data.get('marketplace', {}).get('tasks', [])
    high_value = [t for t in tasks if t.get('bounty', 0) >= 50]
    if high_value:
        alert("💼 NEW_TASK", f"{len(high_value)} 0xWork tasks with bounty >= $50")

def run_alerts(snapshot_file="projects/revenue_snapshot.json"):
    if not os.path.exists(snapshot_file):
        print(f"Snapshot not found: {snapshot_file}")
        return
    with open(snapshot_file) as f:
        data = json.load(f)
    check_litcoiin(data)
    check_nookplot(data)
    check_0xwork(data)
    if ALERTS:
        print("\n".join(ALERTS))
    else:
        print("No alerts.")

if __name__ == "__main__":
    run_alerts()
