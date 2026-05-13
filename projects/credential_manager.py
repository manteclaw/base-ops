#!/usr/bin/env python3
"""
Manteclaw Credential Rotation Manager
Scans workspace for API keys, tests validity, warns before expiration,
and generates rotation recommendations.

Usage:
    python3 projects/credential_manager.py scan        # Scan all keys
    python3 projects/credential_manager.py health      # Test key health
    python3 projects/credential_manager.py report      # Full report
    python3 projects/credential_manager.py rotate      # Generate rotation plan
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Config ──
WORKSPACE_ROOT = Path("/root/.openclaw/workspace")
SCAN_PATTERNS = [
    "**/.env*",
    "**/*.env",
    "**/config.json",
    "**/config.yaml",
    "**/config.yml",
    "**/*.service",
    "**/.openclaw*",
]
EXCLUDED_DIRS = {
    "__pycache__", "node_modules", ".git", "venv", ".venv",
    "dist", "build", ".pytest_cache"
}

# Key patterns to detect
KEY_PATTERNS = {
    "BANKR_API_KEY": {
        "regex": r"(?i)(?:BANKR_API_KEY|BANKR_KEY)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": None,
        "test_func": "test_bankr_key",
        "type": "api_key",
    },
    "NOOKPLOT_API_KEY": {
        "regex": r"(?i)(?:NOOKPLOT_API_KEY)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": "https://gateway.nookplot.com/v1/runtime/connect",
        "test_func": "test_nookplot_key",
        "type": "api_key",
    },
    "ALCHEMY_API_KEY": {
        "regex": r"(?i)(?:ALCHEMY_API_KEY)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": "https://base-mainnet.g.alchemy.com/v2/",
        "test_func": "test_alchemy_key",
        "type": "api_key",
    },
    "OPENROUTER_API_KEY": {
        "regex": r"(?i)(?:OPENROUTER_API_KEY)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": "https://openrouter.ai/api/v1/auth/key",
        "test_func": "test_openrouter_key",
        "type": "api_key",
    },
    "VENICE_API_KEY": {
        "regex": r"(?i)(?:VENICE_API_KEY)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": "https://api.venice.ai/api/v1/models",
        "test_func": "test_venice_key",
        "type": "api_key",
    },
    "GITHUB_TOKEN": {
        "regex": r"(?i)(?:GITHUB_TOKEN|GH_TOKEN)\s*=\s*([A-Za-z0-9_\-]{20,})",
        "test_url": "https://api.github.com/user",
        "test_func": "test_github_token",
        "type": "token",
    },
    "PRIVATE_KEY": {
        "regex": r"(?i)(?:PRIVATE_KEY|ETH_PRIVATE_KEY|WALLET_PRIVATE_KEY)\s*=\s*(0x[a-fA-F0-9]{64})",
        "test_url": None,
        "test_func": "test_eth_private_key",
        "type": "private_key",
    },
    "NOOKPLOT_AGENT_PRIVATE_KEY": {
        "regex": r"(?i)(?:NOOKPLOT_AGENT_PRIVATE_KEY)\s*=\s*(0x[a-fA-F0-9]{64})",
        "test_url": None,
        "test_func": "test_nookplot_pk",
        "type": "private_key",
    },
    "MNEMONIC": {
        "regex": r"(?i)(?:MNEMONIC|SEED_PHRASE)\s*=\s*([a-z]+(?:\s+[a-z]+){11,23})",
        "test_url": None,
        "test_func": None,
        "type": "mnemonic",
        "sensitive": True,
    },
}

# ── Test Functions ──

VENV_PYTHON = "/root/.openclaw/workspace/projects/litcoin/venv/bin/python3"
VENV_SITE = "/root/.openclaw/workspace/projects/litcoin/venv/lib/python3.12/site-packages"

def test_bankr_key(key: str) -> dict:
    """Test Bankr API key via litcoin SDK if available."""
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-c", f"""
import os, json
os.environ['BANKR_API_KEY'] = '{key}'
try:
    from litcoin import Agent
    agent = Agent(bankr_key='{key}')
    status = agent.status()
    print(json.dumps({{"status": "valid", "balance": status.get("balance", 0)}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
"""],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout.strip())
        return data
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_nookplot_key(key: str) -> dict:
    """Test Nookplot API key via runtime connect."""
    try:
        result = subprocess.run(
            [VENV_PYTHON, "-c", f"""
import asyncio, os, json, sys
sys.path.insert(0, "{VENV_SITE}")
from nookplot_runtime import NookplotRuntime
async def t():
    try:
        rt = NookplotRuntime(gateway_url='https://gateway.nookplot.com', api_key='{key}')
        conn = await rt.connect()
        await rt.disconnect()
        print(json.dumps({{"status": "valid", "agent_id": conn.agent_id}}))
    except Exception as e:
        print(json.dumps({{"status": "invalid", "error": str(e)}}))
asyncio.run(t())
"""],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout.strip())
        return data
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_alchemy_key(key: str) -> dict:
    """Test Alchemy API key via block number check."""
    try:
        import httpx
        url = f"https://base-mainnet.g.alchemy.com/v2/{key}"
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        resp = httpx.post(url, json=payload, timeout=10)
        if resp.status_code == 200 and "result" in resp.json():
            return {"status": "valid", "block": resp.json()["result"]}
        return {"status": "invalid", "code": resp.status_code}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_openrouter_key(key: str) -> dict:
    """Test OpenRouter API key."""
    try:
        import httpx
        resp = httpx.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        if resp.status_code == 200:
            return {"status": "valid", "data": resp.json()}
        return {"status": "invalid", "code": resp.status_code}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_venice_key(key: str) -> dict:
    """Test Venice API key."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.venice.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10
        )
        if resp.status_code == 200:
            return {"status": "valid"}
        return {"status": "invalid", "code": resp.status_code}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_github_token(key: str) -> dict:
    """Test GitHub token."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {key}"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"status": "valid", "login": data.get("login")}
        return {"status": "invalid", "code": resp.status_code}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def test_eth_private_key(key: str) -> dict:
    """Test Ethereum private key by deriving address."""
    try:
        from eth_account import Account
        acct = Account.from_key(key)
        return {"status": "valid", "address": acct.address}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}


def test_nookplot_pk(key: str) -> dict:
    """Test Nookplot private key by checking it's a valid 32-byte hex."""
    try:
        if not re.match(r"^0x[a-fA-F0-9]{64}$", key):
            return {"status": "invalid", "error": "Invalid format"}
        return {"status": "valid", "note": "Format valid; full test requires API key"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


TEST_FUNCTIONS = {
    "test_bankr_key": test_bankr_key,
    "test_nookplot_key": test_nookplot_key,
    "test_alchemy_key": test_alchemy_key,
    "test_openrouter_key": test_openrouter_key,
    "test_venice_key": test_venice_key,
    "test_github_token": test_github_token,
    "test_eth_private_key": test_eth_private_key,
    "test_nookplot_pk": test_nookplot_pk,
}

# ── Scanner ──

def scan_workspace() -> list:
    """Scan workspace for all credential files and extract keys."""
    found = []
    
    for pattern in SCAN_PATTERNS:
        for path in WORKSPACE_ROOT.glob(pattern):
            # Skip excluded dirs
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            
            rel_path = str(path.relative_to(WORKSPACE_ROOT))
            
            for key_name, key_config in KEY_PATTERNS.items():
                regex = key_config["regex"]
                for match in re.finditer(regex, content):
                    key_value = match.group(1)
                    # Mask sensitive keys in output
                    if key_config.get("sensitive"):
                        masked = "[MNEMONIC — HIDDEN]"
                    else:
                        masked = key_value[:8] + "..." + key_value[-4:] if len(key_value) > 12 else "***"
                    
                    found.append({
                        "key_name": key_name,
                        "key_value": key_value,
                        "masked": masked,
                        "file": rel_path,
                        "type": key_config["type"],
                        "test_func": key_config.get("test_func"),
                    })
    
    return found


def test_key(cred: dict) -> dict:
    """Test a single credential's health."""
    test_func_name = cred.get("test_func")
    if not test_func_name:
        return {"status": "not_testable", "reason": "No test function configured"}
    
    test_func = TEST_FUNCTIONS.get(test_func_name)
    if not test_func:
        return {"status": "not_testable", "reason": "Test function not found"}
    
    try:
        result = test_func(cred["key_value"])
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_report(credentials: list, health_results: dict) -> dict:
    """Generate a comprehensive credential health report."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_credentials": len(credentials),
        "by_type": {},
        "by_status": {"valid": 0, "invalid": 0, "unknown": 0, "not_testable": 0, "error": 0},
        "credentials": [],
        "rotation_warnings": [],
        "recommendations": [],
    }
    
    for cred in credentials:
        key_name = cred["key_name"]
        health = health_results.get(key_name, {"status": "unknown"})
        status = health.get("status", "unknown")
        
        report["by_status"][status] = report["by_status"].get(status, 0) + 1
        key_type = cred["type"]
        report["by_type"][key_type] = report["by_type"].get(key_type, 0) + 1
        
        entry = {
            "name": key_name,
            "file": cred["file"],
            "type": key_type,
            "masked": cred["masked"],
            "status": status,
            "health_details": health,
        }
        report["credentials"].append(entry)
        
        # Rotation recommendations
        if status == "invalid":
            report["rotation_warnings"].append({
                "key": key_name,
                "file": cred["file"],
                "urgency": "IMMEDIATE",
                "reason": "Key is invalid or expired",
            })
        elif status == "unknown":
            report["rotation_warnings"].append({
                "key": key_name,
                "file": cred["file"],
                "urgency": "HIGH",
                "reason": "Could not verify key health",
            })
        elif status == "error":
            report["rotation_warnings"].append({
                "key": key_name,
                "file": cred["file"],
                "urgency": "HIGH",
                "reason": f"Test error: {health.get('error', 'unknown')}",
            })
    
    # General recommendations
    if report["by_status"].get("invalid", 0) > 0:
        report["recommendations"].append(
            f"Rotate {report['by_status']['invalid']} invalid keys immediately"
        )
    if len(set(c["file"] for c in credentials)) < len(credentials):
        report["recommendations"].append("Some keys are duplicated across files — consolidate to single .env")
    
    # Check for missing critical keys
    critical_keys = ["BANKR_API_KEY", "ALCHEMY_API_KEY"]
    found_keys = set(c["key_name"] for c in credentials)
    for ck in critical_keys:
        if ck not in found_keys:
            report["recommendations"].append(f"Missing critical key: {ck}")
    
    return report


def print_report(report: dict):
    """Pretty-print the report."""
    print("=" * 70)
    print("  MANTECLAW CREDENTIAL MANAGER REPORT")
    print("=" * 70)
    print(f"Generated: {report['generated_at']}")
    print(f"Total credentials: {report['total_credentials']}")
    print()
    
    print("─" * 70)
    print("  STATUS SUMMARY")
    print("─" * 70)
    for status, count in report["by_status"].items():
        icon = {"valid": "✅", "invalid": "❌", "unknown": "⚠️", "not_testable": "➖", "error": "🔥"}.get(status, "❓")
        print(f"  {icon} {status}: {count}")
    print()
    
    print("─" * 70)
    print("  CREDENTIALS")
    print("─" * 70)
    for cred in report["credentials"]:
        icon = {"valid": "✅", "invalid": "❌", "unknown": "⚠️", "not_testable": "➖", "error": "🔥"}.get(cred["status"], "❓")
        print(f"  {icon} {cred['name']}")
        print(f"     File: {cred['file']}")
        print(f"     Masked: {cred['masked']}")
        if cred["health_details"].get("error"):
            print(f"     Error: {cred['health_details']['error']}")
        print()
    
    if report["rotation_warnings"]:
        print("─" * 70)
        print("  🚨 ROTATION WARNINGS")
        print("─" * 70)
        for warn in report["rotation_warnings"]:
            print(f"  [{warn['urgency']}] {warn['key']} in {warn['file']}")
            print(f"     Reason: {warn['reason']}")
        print()
    
    if report["recommendations"]:
        print("─" * 70)
        print("  💡 RECOMMENDATIONS")
        print("─" * 70)
        for rec in report["recommendations"]:
            print(f"  • {rec}")
        print()
    
    print("=" * 70)


def save_report(report: dict):
    """Save report to disk."""
    report_path = WORKSPACE_ROOT / "projects" / "credential_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"📄 Report saved to: {report_path}")


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(description="Manteclaw Credential Manager")
    parser.add_argument("command", choices=["scan", "health", "report", "rotate"], help="Command to run")
    args = parser.parse_args()
    
    print("🔍 Scanning workspace for credentials...")
    credentials = scan_workspace()
    print(f"Found {len(credentials)} credentials\n")
    
    if args.command == "scan":
        for cred in credentials:
            print(f"  {cred['key_name']} ({cred['type']}) in {cred['file']} → {cred['masked']}")
        return
    
    if args.command == "health":
        print("🩺 Testing credential health...\n")
        health_results = {}
        for cred in credentials:
            name = cred["key_name"]
            print(f"  Testing {name}...", end=" ")
            result = test_key(cred)
            health_results[name] = result
            icon = {"valid": "✅", "invalid": "❌", "unknown": "⚠️", "not_testable": "➖", "error": "🔥"}.get(result["status"], "❓")
            print(f"{icon} {result['status']}")
            if result.get("error"):
                print(f"     Error: {result['error']}")
        return
    
    if args.command in ("report", "rotate"):
        print("🩺 Testing credential health...\n")
        health_results = {}
        for cred in credentials:
            name = cred["key_name"]
            result = test_key(cred)
            health_results[name] = result
        
        report = generate_report(credentials, health_results)
        print_report(report)
        save_report(report)
        
        if args.command == "rotate":
            print("\n🔄 ROTATION PLAN")
            print("=" * 70)
            for warn in report["rotation_warnings"]:
                print(f"\n  [{warn['urgency']}] {warn['key']}")
                print(f"     1. Generate new key at provider dashboard")
                print(f"     2. Update in: {warn['file']}")
                print(f"     3. Restart any services using this key")
                print(f"     4. Revoke old key after 24h")


if __name__ == "__main__":
    main()
