#!/usr/bin/env python3
"""
Manteclaw Checkpoint — State snapshot manager.

Before any destructive operation, auto-snapshot the current state.
API:
    checkpoint.save(reason="pre-key-rotation")
    checkpoint.restore(id="2026-05-07_04-11-30")
    checkpoint.list()

Keeps last 20 checkpoints. Auto-deletes older ones.
"""

import os
import sys
import shutil
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

WORKSPACE = Path("/root/.openclaw/workspace")
CHECKPOINT_DIR = WORKSPACE / "checkpoints"
MAX_CHECKPOINTS = 20

# Files to snapshot — add more as the workspace grows
CHECKPOINT_FILES = [
    ".env",
    "WALLET.md",
    "USER.md",
    "TOOLS.md",
    "MEMORY.md",
    "SOUL.md",
    "HEARTBEAT.md",
    "selfheal.py",
    "daemon.py",
    "orchestrator.py",
    "autobackup.py",
    "credential_manager.py",
    "checkpoint.py",
    # Project-level envs
    "projects/litcoin/.env",
    "projects/zyfai/.env",
    "projects/0xwork/.env",
    "projects/meshledger/.env",
    "projects/nookplot/.env",
    "projects/clawbank/.env",
    "projects/governance-bot/.env",
    "projects/x402-server/.env",
    "manteclaw/.env",
]


def _ensure_dir():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def save(reason: str = "manual", extra_files: Optional[List[str]] = None) -> str:
    """
    Create a new checkpoint.
    Returns the checkpoint ID (timestamp string).
    """
    _ensure_dir()
    cp_id = _now_str()
    cp_path = CHECKPOINT_DIR / cp_id
    cp_path.mkdir(parents=True, exist_ok=False)

    manifest: Dict[str, Any] = {
        "id": cp_id,
        "reason": reason,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "workspace": str(WORKSPACE),
        "files": {},
    }

    files_to_copy = list(CHECKPOINT_FILES)
    if extra_files:
        files_to_copy.extend(extra_files)

    for rel in files_to_copy:
        src = WORKSPACE / rel
        if src.exists():
            dst = cp_path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src, dst)
                manifest["files"][rel] = {
                    "sha256": _sha256_file(src),
                    "size": src.stat().st_size,
                }
            except Exception as e:
                manifest["files"][rel] = {"error": str(e)}
        else:
            manifest["files"][rel] = {"status": "missing"}

    # Write manifest
    (cp_path / "_manifest.json").write_text(json.dumps(manifest, indent=2))

    # Prune old checkpoints
    _prune_old()

    print(f"✅ Checkpoint saved: {cp_id} ({reason})")
    return cp_id


def restore(cp_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Restore workspace files from a checkpoint.
    By default dry_run=True — shows what would happen without doing it.
    Pass dry_run=False to actually restore.
    """
    cp_path = CHECKPOINT_DIR / cp_id
    if not cp_path.exists():
        return {"error": f"Checkpoint {cp_id} not found"}

    manifest_path = cp_path / "_manifest.json"
    if not manifest_path.exists():
        return {"error": "Manifest missing in checkpoint"}

    manifest = json.loads(manifest_path.read_text())
    results: Dict[str, Any] = {"restored": [], "skipped": [], "errors": []}

    for rel, meta in manifest.get("files", {}).items():
        src = cp_path / rel
        dst = WORKSPACE / rel
        if not src.exists():
            results["skipped"].append({"file": rel, "reason": "not in checkpoint"})
            continue

        if dry_run:
            results["skipped"].append({"file": rel, "reason": "dry_run"})
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            results["restored"].append(rel)
        except Exception as e:
            results["errors"].append({"file": rel, "error": str(e)})

    return {
        "checkpoint_id": cp_id,
        "dry_run": dry_run,
        **results,
        "manifest": manifest.get("reason", "unknown"),
    }


def list_checkpoints() -> List[Dict[str, Any]]:
    """List all available checkpoints with metadata."""
    _ensure_dir()
    cps = []
    for p in sorted(CHECKPOINT_DIR.iterdir()):
        if p.is_dir() and (p / "_manifest.json").exists():
            mf = json.loads((p / "_manifest.json").read_text())
            cps.append({
                "id": p.name,
                "reason": mf.get("reason"),
                "created_at": mf.get("created_at"),
                "file_count": len([f for f, m in mf.get("files", {}).items() if "sha256" in m]),
            })
    return list(reversed(cps))


def _prune_old():
    """Keep only the last MAX_CHECKPOINTS."""
    cps = list(CHECKPOINT_DIR.iterdir())
    cps = [p for p in cps if p.is_dir() and (p / "_manifest.json").exists()]
    cps.sort(key=lambda p: p.name)
    while len(cps) > MAX_CHECKPOINTS:
        oldest = cps.pop(0)
        try:
            shutil.rmtree(oldest)
            print(f"🗑️  Pruned old checkpoint: {oldest.name}")
        except Exception as e:
            print(f"⚠️  Failed to prune {oldest.name}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

class CheckpointManager:
    """Convenience class for programmatic use."""

    @staticmethod
    def before_destructive(reason: str, extra_files: Optional[List[str]] = None) -> str:
        """Save checkpoint before a destructive operation. Prints and returns ID."""
        return save(reason=reason, extra_files=extra_files)

    @staticmethod
    def list() -> List[Dict[str, Any]]:
        return list_checkpoints()

    @staticmethod
    def restore_id(cp_id: str, dry_run: bool = True) -> Dict[str, Any]:
        return restore(cp_id, dry_run=dry_run)


def cli():
    if len(sys.argv) < 2:
        print("Usage: python3 checkpoint.py [save <reason>|list|restore <id> [--yes]|prune]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "save":
        reason = sys.argv[2] if len(sys.argv) > 2 else "manual"
        save(reason=reason)

    elif cmd == "list":
        cps = list_checkpoints()
        if not cps:
            print("No checkpoints found.")
            return
        print(f"{'ID':<22} {'Reason':<20} {'Files':>6} {'Created'}")
        print("-" * 70)
        for cp in cps:
            print(f"{cp['id']:<22} {cp['reason']:<20} {cp['file_count']:>6} {cp['created_at']}")

    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("Usage: python3 checkpoint.py restore <id> [--yes]")
            sys.exit(1)
        cp_id = sys.argv[2]
        dry_run = "--yes" not in sys.argv
        result = restore(cp_id, dry_run=dry_run)
        print(json.dumps(result, indent=2))
        if dry_run:
            print("\n⚠️ This was a dry run. Pass --yes to actually restore.")

    elif cmd == "prune":
        _prune_old()
        print("Pruning complete.")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 checkpoint.py [save <reason>|list|restore <id> [--yes]|prune]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
