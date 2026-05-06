#!/usr/bin/env python3
"""
Manteclaw Credential Manager — Lifecycle tracking for API keys.

Scans all .env files in workspace for API keys.
Tracks key age and warns at 30/60/90 days.
Exports metadata (service, type, last_rotated, status) — NO values exposed.
Integrates with checkpoint.py before rotation.

Usage:
    python3 credential_manager.py scan          # scan workspace
    python3 credential_manager.py manifest      # write credentials_manifest.json
    python3 credential_manager.py check         # check ages + warn
    python3 credential_manager.py rotate <file> # pre-rotate checkpoint
"""

import os
import sys
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

WORKSPACE = Path("/root/.openclaw/workspace")
MANIFEST_FILE = WORKSPACE / "credentials_manifest.json"
STATE_FILE = WORKSPACE / ".credential_state.json"

# Patterns that indicate an API key / secret
KEY_PATTERNS = [
    re.compile(r"^(\w*[A-Z_]*(?:API_KEY|APIKEY|TOKEN|SECRET|PRIVATE_KEY|MNEMONIC|PASSWORD|SEED|AUTH))\s*=")
]

# Service name inference from key name or file path
SERVICE_MAP = {
    "GITHUB": "GitHub",
    "GH": "GitHub",
    "OPENROUTER": "OpenRouter",
    "OR_": "OpenRouter",
    "VENICE": "Venice AI",
    "BANKR": "Bankr",
    "LITCOIN": "Bankr/Litcoiin",
    "ALCHEMY": "Alchemy",
    "DUNE": "Dune Analytics",
    "MISTRAL": "Mistral AI",
    "SAMBANOVA": "SambaNova",
    "GROQ": "Groq",
    "WORK": "0xWork",
    "ZYFAI": "Zyfai",
    "NOOKPLOT": "Nookplot",
    "NEYNAR": "Neynar",
    "MESHLEDGER": "MeshLedger",
    "MOLT": "MoltLaunch",
    "DAYDREAMS": "Daydreams",
    "LOBE": "LobeHub",
    "SMITHERY": "Smithery",
    "HELI_XA": "Helixa",
    "HELI": "Helixa",
    "PINATA": "Pinata",
    "REGISTRATION": "ERC-8004",
    "X402": "x402",
    "LUCID": "Daydreams/Lucid",
    "SNAPSHOT": "Snapshot",
    "SAFE": "Safe",
    "BASE": "Base",
    "ETHERSCAN": "Etherscan",
    "INFURA": "Infura",
    "TENDERLY": "Tenderly",
    "COINGECKO": "CoinGecko",
    "COINMARKET": "CoinMarketCap",
    "DEFILLAMA": "DeFiLlama",
    "TWITTER": "Twitter/X",
    "DISCORD": "Discord",
    "TELEGRAM": "Telegram",
    "SLACK": "Slack",
    "POSTGRES": "PostgreSQL",
    "REDIS": "Redis",
    "AWS": "AWS",
    "GCP": "Google Cloud",
    "AZURE": "Azure",
}


def _infer_service(key_name: str, file_path: Path) -> str:
    """Infer the service name from key name or file path."""
    upper = key_name.upper()
    for prefix, svc in SERVICE_MAP.items():
        if prefix in upper:
            return svc
    # Fallback: directory name
    parts = [p.name.upper() for p in file_path.parents if p.name != WORKSPACE.name]
    for part in parts:
        for prefix, svc in SERVICE_MAP.items():
            if prefix in part:
                return svc
    return "Unknown"


def _is_secret_key(key_name: str) -> bool:
    """Check if a key name looks like a secret."""
    upper = key_name.upper()
    return any(
        pat in upper
        for pat in ["KEY", "TOKEN", "SECRET", "PRIVATE", "MNEMONIC", "PASSWORD", "SEED", "AUTH"]
    )


def _looks_like_key(value: str) -> bool:
    """Heuristic: does the value look like a real key?"""
    if not value or value.startswith("$"):
        return False
    # Common key formats
    if value.startswith("ghp_"): return True
    if value.startswith("gsk_"): return True
    if value.startswith("sk-"): return True
    if value.startswith("nk_"): return True
    if value.startswith("bk_"): return True
    if value.startswith("0x") and len(value) > 20: return True
    if len(value) >= 32: return True
    return False


def scan_workspace() -> List[Dict[str, Any]]:
    """Recursively scan workspace for .env files and extract key metadata."""
    found: List[Dict[str, Any]] = []
    env_files = list(WORKSPACE.rglob(".env")) + list(WORKSPACE.rglob(".env.*"))

    for env_file in env_files:
        if env_file.name.endswith(".example") or env_file.name.endswith(".template"):
            continue
        try:
            lines = env_file.read_text().splitlines()
        except Exception:
            continue

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            for pattern in KEY_PATTERNS:
                match = pattern.match(line)
                if match:
                    key_name = match.group(1)
                    # Split on first =
                    if "=" not in line:
                        continue
                    _, value = line.split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    if not _looks_like_key(value):
                        continue

                    rel_path = str(env_file.relative_to(WORKSPACE))
                    found.append({
                        "file": rel_path,
                        "key_name": key_name,
                        "service": _infer_service(key_name, env_file),
                        "type": "private_key" if "PRIVATE" in key_name.upper() or "MNEMONIC" in key_name.upper() else "api_key",
                        "key_hash": hash(value) % (2**32),  # opaque fingerprint, not reversible
                        "value_preview": value[:4] + "..." if len(value) > 8 else "***",
                    })
                    break  # only first match per pattern
    return found


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"first_seen": {}, "last_rotated": {}}


def _save_state(state: Dict[str, Any]):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def build_manifest(keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build credentials_manifest.json from scanned keys + rotation tracking."""
    state = _load_state()
    now = datetime.utcnow()
    manifest: Dict[str, Any] = {
        "generated_at": now.isoformat() + "Z",
        "total_keys": len(keys),
        "keys": [],
        "warnings": [],
        "stats": {"active": 0, "stale_30d": 0, "stale_60d": 0, "stale_90d": 0, "expired": 0},
    }

    for k in keys:
        entry = dict(k)
        key_id = f"{k['file']}:{k['key_name']}"

        # Track first_seen
        if key_id not in state["first_seen"]:
            state["first_seen"][key_id] = now.isoformat()

        first_seen = datetime.fromisoformat(state["first_seen"][key_id].replace("Z", "+00:00")).replace(tzinfo=None)
        age_days = (now - first_seen).days

        last_rotated_str = state["last_rotated"].get(key_id)
        last_rotated = datetime.fromisoformat(last_rotated_str.replace("Z", "+00:00")).replace(tzinfo=None) if last_rotated_str else first_seen
        rotated_days_ago = (now - last_rotated).days

        entry["first_seen"] = state["first_seen"][key_id]
        entry["last_rotated"] = last_rotated_str or state["first_seen"][key_id]
        entry["age_days"] = age_days
        entry["rotated_days_ago"] = rotated_days_ago

        # Status
        if rotated_days_ago >= 90:
            entry["status"] = "CRITICAL — rotate immediately"
            manifest["stats"]["stale_90d"] += 1
            manifest["warnings"].append(f"🔴 {k['key_name']} ({k['service']}): {rotated_days_ago} days since rotation")
        elif rotated_days_ago >= 60:
            entry["status"] = "WARNING — rotate soon"
            manifest["stats"]["stale_60d"] += 1
            manifest["warnings"].append(f"🟠 {k['key_name']} ({k['service']}): {rotated_days_ago} days since rotation")
        elif rotated_days_ago >= 30:
            entry["status"] = "AGING — plan rotation"
            manifest["stats"]["stale_30d"] += 1
            manifest["warnings"].append(f"🟡 {k['key_name']} ({k['service']}): {rotated_days_ago} days since rotation")
        else:
            entry["status"] = "HEALTHY"
            manifest["stats"]["active"] += 1

        manifest["keys"].append(entry)

    _save_state(state)
    return manifest


def write_manifest(manifest: Dict[str, Any]):
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    print(f"✅ Manifest written: {MANIFEST_FILE} ({manifest['total_keys']} keys)")


def check_ages() -> Tuple[int, List[str]]:
    """Return (warning_count, messages)."""
    keys = scan_workspace()
    manifest = build_manifest(keys)
    warnings = manifest["warnings"]
    return len(warnings), warnings


def pre_rotate_checkpoint(env_file: str) -> str:
    """Save checkpoint before rotating keys in a file. Returns checkpoint ID."""
    try:
        from checkpoint import save
    except ImportError:
        print("ERROR: checkpoint.py not found. Cannot auto-backup before rotation.")
        sys.exit(1)
    cp_id = save(reason=f"pre-rotation-{Path(env_file).name}", extra_files=[env_file])
    return cp_id


def mark_rotated(key_name: str, file_path: str):
    """Mark a key as freshly rotated in state tracking."""
    state = _load_state()
    key_id = f"{file_path}:{key_name}"
    state["last_rotated"][key_id] = datetime.utcnow().isoformat() + "Z"
    _save_state(state)
    print(f"✅ Marked {key_name} as rotated")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def cli():
    if len(sys.argv) < 2:
        print("Usage: python3 credential_manager.py [scan|manifest|check|rotate <env_file>|mark <key> <file>]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "scan":
        keys = scan_workspace()
        print(f"Found {len(keys)} keys across workspace:")
        for k in keys:
            print(f"  [{k['service']:<16}] {k['key_name']:<30} in {k['file']}")

    elif cmd == "manifest":
        keys = scan_workspace()
        manifest = build_manifest(keys)
        write_manifest(manifest)
        if manifest["warnings"]:
            print("\nWarnings:")
            for w in manifest["warnings"]:
                print(f"  {w}")

    elif cmd == "check":
        count, warnings = check_ages()
        if count == 0:
            print("✅ All keys healthy (no rotation warnings)")
        else:
            print(f"⚠️  {count} key(s) need attention:")
            for w in warnings:
                print(f"  {w}")

    elif cmd == "rotate":
        if len(sys.argv) < 3:
            print("Usage: python3 credential_manager.py rotate <env_file_path>")
            sys.exit(1)
        env_file = sys.argv[2]
        cp_id = pre_rotate_checkpoint(env_file)
        print(f"✅ Pre-rotation checkpoint saved: {cp_id}")
        print("Now rotate the key in the file, then run:")
        print(f"  python3 credential_manager.py mark <KEY_NAME> {env_file}")

    elif cmd == "mark":
        if len(sys.argv) < 4:
            print("Usage: python3 credential_manager.py mark <KEY_NAME> <file_path>")
            sys.exit(1)
        mark_rotated(sys.argv[2], sys.argv[3])

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 credential_manager.py [scan|manifest|check|rotate <env_file>|mark <key> <file>]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
