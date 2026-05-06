#!/usr/bin/env python3
"""
Manteclaw Auto-Backup — Git auto-commit daemon.

Watches workspace for changes (mtime check on tracked files).
Auto-commits every N hours with descriptive messages.
Pushes to origin if configured.
Respects .gitignore. Never commits .env or secrets.

Usage:
    python3 autobackup.py start    # background daemon
    python3 autobackup.py stop     # stop daemon
    python3 autobackup.py once     # single run (manual trigger)
    python3 autobackup.py status   # show last commit + next check
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

WORKSPACE = Path("/root/.openclaw/workspace")
STATE_FILE = WORKSPACE / ".autobackup_state.json"
LOG_FILE = WORKSPACE / "backup.log"
PID_FILE = Path("/tmp/manteclaw-autobackup.pid")

# Files that must NEVER be committed — absolute safety
FORBIDDEN_PATTERNS = [
    ".env", ".env.", ".secret", "secret", "WALLET.md",
    "private_key", "mnemonic", "password", "token",
]

# Default interval
DEFAULT_INTERVAL_HOURS = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("autobackup")


def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "last_commit_at": None,
        "last_push_at": None,
        "last_check_at": None,
        "file_mtimes": {},
    }


def _save_state(state: Dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _is_git_repo() -> bool:
    return (WORKSPACE / ".git").exists()


def _git(cmd: List[str], check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(WORKSPACE)] + cmd,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
    )


def _tracked_files() -> List[str]:
    """Return list of tracked files (relative paths)."""
    result = _git(["ls-files"], check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _modified_files() -> List[str]:
    """Return list of modified tracked files."""
    result = _git(["diff", "--name-only", "HEAD"], check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _untracked_files() -> List[str]:
    """Return untracked files (not ignored)."""
    result = _git(["ls-files", "--others", "--exclude-standard"], check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_forbidden(path: str) -> bool:
    """Check if a file path matches forbidden patterns."""
    lowered = path.lower()
    for pat in FORBIDDEN_PATTERNS:
        if pat.lower() in lowered:
            return True
    return False


def _generate_message(changes: List[str]) -> str:
    """Generate a descriptive commit message from changed files."""
    if not changes:
        return f"auto: checkpoint {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    # Group by directory/project
    dirs: Dict[str, int] = {}
    for c in changes:
        top = c.split("/")[0] if "/" in c else "root"
        dirs[top] = dirs.get(top, 0) + 1

    if len(dirs) == 1:
        top_dir = list(dirs.keys())[0]
        return f"auto: update {top_dir} ({len(changes)} files)"
    else:
        summary = ", ".join(f"{d}({n})" for d, n in sorted(dirs.items(), key=lambda x: -x[1])[:3])
        return f"auto: {summary}"


def _commit_if_needed(force: bool = False) -> Optional[str]:
    """
    Check for changes, commit if found.
    Returns commit hash if committed, None otherwise.
    """
    if not _is_git_repo():
        logger.warning("No git repo found. Skipping.")
        return None

    state = _load_state()
    tracked = _tracked_files()
    modified = _modified_files()
    untracked = _untracked_files()

    # Filter out forbidden files from consideration
    all_changes = [f for f in (modified + untracked) if not _is_forbidden(f)]

    if not all_changes and not force:
        logger.debug("No changes to commit.")
        state["last_check_at"] = datetime.utcnow().isoformat() + "Z"
        _save_state(state)
        return None

    # Stage safe files only
    staged = 0
    for f in all_changes:
        if _is_forbidden(f):
            logger.warning(f"SKIPPING forbidden file: {f}")
            continue
        r = _git(["add", f], check=False)
        if r.returncode == 0:
            staged += 1

    if staged == 0 and not force:
        logger.info("No safe files to stage.")
        return None

    msg = _generate_message(all_changes)
    r = _git(["commit", "-m", msg], check=False)
    if r.returncode == 0:
        commit_hash = r.stdout.strip().splitlines()[0].split()[-1]
        state["last_commit_at"] = datetime.utcnow().isoformat() + "Z"
        state["last_commit_msg"] = msg
        logger.info(f"✅ Committed: {msg} ({commit_hash})")

        # Try push
        push_r = _git(["push", "new-origin", "main"], check=False, timeout=60)
        if push_r.returncode == 0:
            state["last_push_at"] = datetime.utcnow().isoformat() + "Z"
            logger.info("✅ Pushed to new-origin/main")
        else:
            logger.warning(f"Push failed: {push_r.stderr.strip()[:200]}")

        _save_state(state)
        return commit_hash
    else:
        logger.warning(f"Commit failed: {r.stderr.strip()[:200]}")
        return None


class AutoBackupDaemon:
    def __init__(self, interval_hours: float = DEFAULT_INTERVAL_HOURS):
        self.interval_sec = int(interval_hours * 3600)
        self.shutdown_event = threading.Event()

    def start(self):
        logger.info("=" * 60)
        logger.info("Auto-Backup Daemon STARTING")
        logger.info(f"Interval: {self.interval_sec / 3600:.1f}h")
        logger.info("=" * 60)
        PID_FILE.write_text(str(os.getpid()))
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())

        # Initial commit check
        _commit_if_needed()

        while not self.shutdown_event.is_set():
            self.shutdown_event.wait(self.interval_sec)
            if not self.shutdown_event.is_set():
                try:
                    _commit_if_needed()
                except Exception as e:
                    logger.exception(f"Backup cycle failed: {e}")

        self._cleanup()

    def shutdown(self):
        logger.info("Auto-Backup Daemon shutting down...")
        self.shutdown_event.set()

    def _cleanup(self):
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("Auto-Backup Daemon STOPPED")


def _read_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            return None
    return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cli():
    if len(sys.argv) < 2:
        print("Usage: python3 autobackup.py [start|stop|once|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        pid = _read_pid()
        if pid and _is_running(pid):
            print(f"Daemon already running (PID {pid})")
            sys.exit(1)
        daemon = AutoBackupDaemon()
        daemon.start()

    elif cmd == "stop":
        pid = _read_pid()
        if not pid:
            print("Daemon not running")
            sys.exit(1)
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")
            for _ in range(10):
                time.sleep(0.5)
                if not PID_FILE.exists():
                    break
            print("Stopped" if not PID_FILE.exists() else "PID file still present")
        except OSError as e:
            print(f"Error stopping: {e}")
            PID_FILE.unlink(missing_ok=True)

    elif cmd == "once":
        result = _commit_if_needed(force="--force" in sys.argv)
        if result:
            print(f"Committed: {result}")
        else:
            print("No changes to commit")

    elif cmd == "status":
        state = _load_state()
        pid = _read_pid()
        running = pid and _is_running(pid)
        print(f"Running: {'yes' if running else 'no'} (PID: {pid})")
        print(f"Last commit: {state.get('last_commit_at', 'never')}")
        print(f"Last push:   {state.get('last_push_at', 'never')}")
        print(f"Last check:  {state.get('last_check_at', 'never')}")
        modified = _modified_files()
        if modified:
            print(f"Modified files ({len(modified)}):")
            for f in modified[:10]:
                print(f"  - {f}")
            if len(modified) > 10:
                print(f"  ... and {len(modified)-10} more")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 autobackup.py [start|stop|once|status]")
        sys.exit(1)


if __name__ == "__main__":
    import threading
    cli()
