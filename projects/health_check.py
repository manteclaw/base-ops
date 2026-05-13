#!/usr/bin/env python3
"""
Manteclaw Health Check — Unified service status reporter
Checks all 4 core services and reports their status.
Usage: python3 projects/health_check.py
"""

import subprocess
import json
import sys
from datetime import datetime

SERVICES = {
    "A: Litcoiin Miner": "litcoiin-miner.service",
    "B: Arbitrage Bot": "arbitrage-bot.service",
    "C: Litcoiin Claim Timer": "litcoiin-claim.timer",
    "D: Storj Node": "storj-node.service",
}

def get_service_status(name):
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout + result.stderr
        
        status = "unknown"
        if "Active: active (running)" in output:
            status = "✅ RUNNING"
        elif "Active: active (waiting)" in output:
            status = "⏳ WAITING"
        elif "Active: inactive" in output:
            status = "❌ INACTIVE"
        elif "Active: failed" in output:
            status = "💥 FAILED"
        elif "could not be found" in output or "does not exist" in output:
            status = "⚠️ NOT FOUND"
        
        # Extract uptime if available
        uptime = ""
        for line in output.splitlines():
            if "Active: active" in line and "since" in line:
                uptime = line.split("since")[-1].strip()
                break
            if "Trigger:" in line:
                uptime = line.strip()
                break
        
        return {"status": status, "uptime": uptime, "raw": output}
    except Exception as e:
        return {"status": f"⚠️ ERROR: {e}", "uptime": "", "raw": str(e)}

def main():
    print("=" * 60)
    print(f"🏦 MANTECLAW HEALTH CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    report = {}
    all_ok = True
    
    for label, service in SERVICES.items():
        info = get_service_status(service)
        report[label] = info
        
        uptime_str = f" | {info['uptime']}" if info['uptime'] else ""
        print(f"{label:<25} {info['status']}{uptime_str}")
        
        if info['status'].startswith("❌") or info['status'].startswith("💥") or info['status'].startswith("⚠️"):
            all_ok = False
    
    print("=" * 60)
    
    # Check unified target
    target_info = get_service_status("manteclaw-services.target")
    target_status = target_info['status']
    print(f"{'Unified Target':<25} {target_status}")
    
    if target_status.startswith("❌") or target_status.startswith("⚠️"):
        all_ok = False
    
    print("=" * 60)
    
    # Summary
    if all_ok:
        print("🚀 ALL SERVICES HEALTHY — Epoch's running.")
        sys.exit(0)
    else:
        print("🔧 SOME SERVICES NEED ATTENTION — Check logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
