#!/usr/bin/env python3
"""
Quick health check — one command to see all system status.
Run: python3 scripts/quick_status.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except:
        return "ERROR"

def service_status(name):
    out = run(f"systemctl --user is-active {name}")
    return "🟢" if out == "active" else "🔴" if out == "failed" else "⚪"

print(f"\n🏦 MANTECLAW QUICK STATUS — {datetime.now().isoformat()[:19]}")
print("=" * 50)

# Services
print("\n📡 Services:")
for svc in ["litcoiin-miner.service", "litcoiin-claim.timer", "storj-node.service"]:
    print(f"  {service_status(svc)} {svc}")

# Arbitrage (paused)
print(f"  ⚫ arbitrage-bot.service (PAUSED)")

# Git
uncommitted = run("cd /root/.openclaw/workspace && git status --short | wc -l")
last_commit = run("cd /root/.openclaw/workspace && git log -1 --format='%h %ar'")
print(f"\n📦 Git: {uncommitted} uncommitted files | Last: {last_commit}")

# Security
secret_scan = run("python3 /root/.openclaw/workspace/scripts/secret_scanner.py")
print(f"\n🔒 Security: {'✅ Clean' if 'No secrets' in secret_scan else '🚨 Secrets found!'}")

# Wallet
new_wallet = "0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C"
print(f"\n💰 Wallet: {new_wallet}")
print(f"  Status: New (needs funding)")

# Keys
print(f"\n🔑 .keys/ directory: {'✅ Exists' if os.path.exists('/root/.openclaw/workspace/.keys/wallet.seed') else '❌ Missing'}")

# Pre-commit hook
hook = "/root/.openclaw/workspace/.git/hooks/pre-commit"
print(f"  Pre-commit hook: {'✅ Active' if os.path.exists(hook) else '❌ Missing'}")

print("\n" + "=" * 50)
print("Run: python3 projects/health_check.py for full check")
