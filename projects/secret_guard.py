#!/usr/bin/env python3
"""
Secret Guard — Auto-sanitizer for API keys in the workspace.
Scans files for leaked secrets, redacts in-place, and optionally moves
credentials to a centralized .keys/ directory.

Usage:
    python3 projects/secret_guard.py              # full scan + redact
    python3 projects/secret_guard.py --dry-run      # preview only
    python3 projects/secret_guard.py --move-to-keys  # move secrets to .keys/
    python3 projects/secret_guard.py --paths FILE.. # scan specific files
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# --- Configuration -----------------------------------------------------------

WORKSPACE_ROOT = Path("/root/.openclaw/workspace")
KEYS_DIR = WORKSPACE_ROOT / ".keys"

# Regex patterns for known secret prefixes
SECRET_PATTERNS = {
    # High-confidence patterns with known prefixes
    "groq": re.compile(r"gsk_[A-Za-z0-9_-]{32,64}"),
    "nvidia": re.compile(r"nvapi-[A-Za-z0-9_-]{20,80}"),
    "openrouter": re.compile(r"sk-or-v1-[A-Za-z0-9_-]{40,120}"),
    "kimi": re.compile(r"sk-kimi-[A-Za-z0-9_-]{20,80}"),
    "bankr": re.compile(r"bk_usr_[A-Za-z0-9_-]{10,50}"),
    "0xwork": re.compile(r"wp_agent_[A-Za-z0-9_-]{20,80}"),
    "clank": re.compile(r"csk-[A-Za-z0-9_-]{20,60}"),
    "zyfai": re.compile(r"zyfai_[A-Za-z0-9_-]{20,60}"),
    "sambanova": re.compile(r"sam_[a-f0-9_-]{20,80}"),
    # Generic sk- pattern: must look like an API key (long, mixed case)
    "generic_sk": re.compile(r"sk-[A-Za-z0-9_-]{20,120}"),
    # Private key hex (0x + 64 hex chars, standalone word)
    "private_key_hex": re.compile(r"(?<![A-Fa-f0-9])0x[a-fA-F0-9]{64}(?![A-Fa-f0-9])"),
    # Context-aware: key=value patterns for common key names
    "api_key_assignment": re.compile(
        r"(?i)(?:api[_-]?key|apikey|secret|token|password)\s*[:=]\s*['\"]?([A-Za-z0-9_/-]{20,120})['\"]?"
    ),
}

# File patterns to skip (logs, binaries, node_modules, etc.)
SKIP_PATTERNS = [
    r"\.git/",
    r"node_modules/",
    r"\.keys/",
    r"secret_guard\.py$",
    r"pre-commit$",
    r"\.pyc$",
    r"__pycache__/",
    r"\.png$", r"\.jpg$", r"\.gif$", r"\.webp$",
    r"\.mp4$", r"\.mp3$", r"\.wav$",
    r"\.log$",
    r"revenue_history\.jsonl$",
    r"\.cache",
    r"\.openclaw/extensions",
]
SKIP_RE = re.compile("|".join(SKIP_PATTERNS))

# Max file size to scan (bytes)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# How many chars of context to preserve around a redacted secret
REDACT_PREFIX_LEN = 4
REDACT_SUFFIX_LEN = 4


# --- Core Functions ----------------------------------------------------------

def find_secrets_in_text(text: str, filename: str = "") -> List[Tuple[str, str, int, int]]:
    """
    Return list of (secret_type, secret_value, start, end) for each match.
    """
    findings = []
    for secret_type, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            # For patterns with capture groups, use group(1) if available
            if match.lastindex and match.lastindex >= 1:
                val = match.group(1)
                start = match.start(1)
                end = match.end(1)
            else:
                val = match.group(0)
                start = match.start(0)
                end = match.end(0)
            # Skip if it's just a word like "isEmpty" that happens to match generic
            if secret_type == "generic_sk" and not val.startswith("sk-"):
                continue
            if secret_type == "generic_sk" and len(val) < 10:
                continue
            findings.append((secret_type, val, start, end))
    return findings


def redact_text(text: str, findings: List[Tuple[str, str, int, int]]) -> str:
    """Redact all found secrets in text, replacing with [REDACTED-type]."""
    # Sort by position, reverse so we can slice without index drift
    findings_sorted = sorted(findings, key=lambda x: x[2], reverse=True)
    result = text
    for secret_type, val, start, end in findings_sorted:
        replacement = f"[{REDACT_PREFIX_LEN*'*'}REDACTED-{secret_type}{REDACT_SUFFIX_LEN*'*'}]"
        # Preserve some prefix/suffix context for debugging
        prefix = text[max(0, start-REDACT_PREFIX_LEN):start]
        suffix = text[end:min(len(text), end+REDACT_SUFFIX_LEN)]
        replacement = f"{prefix}[REDACTED-{secret_type}]{suffix}"
        result = result[:start] + replacement + result[end:]
    return result


def scan_file(path: Path) -> Tuple[List[Tuple[str, str, int, int]], bool]:
    """
    Scan a single file. Returns (findings, is_binary).
    """
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_FILE_SIZE)
    except Exception:
        return [], False

    # Simple binary check: look for null bytes in first 8KB
    if b"\x00" in raw[:8192]:
        return [], True

    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return [], True

    findings = find_secrets_in_text(text, str(path))
    return findings, False


def scan_workspace(root: Path, explicit_paths: List[Path] = None) -> dict:
    """
    Scan workspace (or explicit paths) and return report dict.
    """
    report = {
        "scanned": 0,
        "skipped": 0,
        "binary_skipped": 0,
        "secrets_found": 0,
        "files_with_secrets": 0,
        "findings": [],  # list of dicts
    }

    if explicit_paths:
        files_to_scan = explicit_paths
    else:
        files_to_scan = []
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                fp = Path(dirpath) / fn
                rel = str(fp.relative_to(root))
                if SKIP_RE.search(rel):
                    report["skipped"] += 1
                    continue
                files_to_scan.append(fp)

    for fp in files_to_scan:
        rel = str(fp.relative_to(root)) if fp.is_relative_to(root) else str(fp)
        if SKIP_RE.search(rel):
            report["skipped"] += 1
            continue

        findings, is_binary = scan_file(fp)
        report["scanned"] += 1
        if is_binary:
            report["binary_skipped"] += 1
            continue

        if findings:
            report["files_with_secrets"] += 1
            report["secrets_found"] += len(findings)
            for secret_type, val, start, end in findings:
                report["findings"].append({
                    "file": rel,
                    "type": secret_type,
                    "value": val,
                    "start": start,
                    "end": end,
                })

    return report


def redact_file(path: Path, findings: List[Tuple[str, str, int, int]], dry_run: bool = False) -> bool:
    """
    Redact secrets in a single file. Returns True if changes were (would be) made.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        print(f"  ⚠️ Could not read {path}: {e}")
        return False

    new_text = redact_text(text, findings)
    if new_text == text:
        return False

    if dry_run:
        print(f"  [DRY-RUN] Would redact {len(findings)} secret(s) in {path}")
        return True

    # Backup original to .keys/backup/
    backup_dir = KEYS_DIR / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{path.name}.{os.urandom(4).hex()}.bak"
    try:
        import shutil
        shutil.copy2(path, backup_path)
    except Exception:
        pass

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"  ✅ Redacted {len(findings)} secret(s) in {path}")
    return True


def generate_env_file(findings: List[dict]) -> str:
    """Generate .env-style content from findings for moving to .keys/"""
    lines = ["# Auto-extracted by secret_guard.py", ""]
    seen = set()
    for f in findings:
        key = f"{f['type'].upper()}_KEY"
        if f["value"] in seen:
            continue
        seen.add(f["value"])
        lines.append(f'{key}="{f["value"]}"')
    return "\n".join(lines) + "\n"


# --- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scan workspace for leaked secrets and redact them.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--move-to-keys", action="store_true", help="Move extracted secrets to .keys/")
    parser.add_argument("--paths", nargs="+", type=Path, help="Scan specific files instead of full workspace")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()

    root = WORKSPACE_ROOT
    if args.paths:
        explicit = [p.resolve() for p in args.paths]
    else:
        explicit = None

    report = scan_workspace(root, explicit_paths=explicit)

    # Deduplicate: if a file has multiple findings, group them
    files_to_redact = {}
    for finding in report["findings"]:
        fp = root / finding["file"]
        if fp not in files_to_redact:
            files_to_redact[fp] = []
        files_to_redact[fp].append((finding["type"], finding["value"], finding["start"], finding["end"]))

    changed_any = False
    if report["findings"]:
        print(f"\n🔍 Found {report['secrets_found']} secret(s) in {report['files_with_secrets']} file(s):\n")
        for fp, findings in files_to_redact.items():
            types = set(f[0] for f in findings)
            print(f"  📄 {fp.relative_to(root)}  ({', '.join(types)})")
            changed = redact_file(fp, findings, dry_run=args.dry_run)
            if changed:
                changed_any = True

        if args.move_to_keys and not args.dry_run:
            KEYS_DIR.mkdir(parents=True, exist_ok=True)
            env_content = generate_env_file(report["findings"])
            env_path = KEYS_DIR / "extracted.env"
            with open(env_path, "w") as f:
                f.write(env_content)
            print(f"\n📦 Extracted secrets written to {env_path}")
            print("   ⚠️  Review and rename to .env, then delete extracted.env")
    else:
        print("\n✅ No leaked secrets found.")

    # Summary
    print(f"\n{'─'*50}")
    print(f"Files scanned:     {report['scanned']}")
    print(f"Files skipped:     {report['skipped']}")
    print(f"Binary skipped:    {report['binary_skipped']}")
    print(f"Secrets found:     {report['secrets_found']}")
    print(f"Files affected:    {report['files_with_secrets']}")
    print(f"{'─'*50}")

    if args.json:
        # Strip actual values from JSON output for safety
        safe_report = report.copy()
        safe_report["findings"] = [
            {k: v for k, v in f.items() if k != "value"}
            for f in safe_report["findings"]
        ]
        print(json.dumps(safe_report, indent=2))

    # Exit code: 1 if secrets were found (blocks git commit)
    sys.exit(1 if report["secrets_found"] > 0 else 0)


if __name__ == "__main__":
    main()
