#!/usr/bin/env python3
"""
Manteclaw Daemon — Lightweight autonomous lane scheduler.
Always-on polling for earning lanes. Uses selfheal.py for resilience.

Lanes:
  A — Litcoiin balance poll        (every 5 min)
  B — Nookplot bounty scrape         (every 10 min)
  C — 0xWork task discovery          (every 15 min)
  D — Zyfai APY monitor              (every 30 min)

Start:   python3 daemon.py start
Stop:    python3 daemon.py stop
Status:  python3 daemon.py status
Logs:    tail -f daemon.log
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Any, Optional

# ── paths ──
WORKSPACE = Path("/root/.openclaw/workspace")
STATUS_FILE = WORKSPACE / "lanes" / "status.json"
PID_FILE = Path("/tmp/manteclaw-daemon.pid")
LOG_FILE = WORKSPACE / "daemon.log"

# ── logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("manteclaw-daemon")

# ── import selfheal ──
sys.path.insert(0, str(WORKSPACE))
try:
    from selfheal import (
        SelfHealExecutor,
        heal_litcoiin_call,
        heal_nookplot_call,
        heal_0xwork_call,
        heal_bankr_call,
    )
except Exception as e:
    logger.error(f"Failed to import selfheal.py: {e}")
    SelfHealExecutor = None  # type: ignore

# ── import orchestrator ──
try:
    from orchestrator import LaneState
except Exception as e:
    logger.error(f"Failed to import orchestrator.py: {e}")
    LaneState = None  # type: ignore


# ═══════════════════════════════════════════════════════════════════════
# LANE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

LANE_CONFIG: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "Litcoiin Balance Polling",
        "interval_sec": 300,   # 5 min
        "enabled": True,
    },
    "B": {
        "name": "Nookplot Bounty Scraping",
        "interval_sec": 600,   # 10 min
        "enabled": True,
    },
    "C": {
        "name": "0xWork Task Discovery",
        "interval_sec": 900,   # 15 min
        "enabled": True,
    },
    "D": {
        "name": "Zyfai APY Monitor",
        "interval_sec": 1800,  # 30 min
        "enabled": True,
    },
}

# ═══════════════════════════════════════════════════════════════════════
# LANE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def lane_A_litcoiin_balance(state: LaneState, executor: "SelfHealExecutor") -> Dict[str, Any]:
    """Check Litcoiin balance via Bankr CLI or litcoin SDK."""
    result: Dict[str, Any] = {
        "status": "running",
        "balance_lit": None,
        "claim_ready": False,
        "threshold": 50000,
        "error": None,
    }
    try:
        # Try litcoin SDK first
        cmd = [
            sys.executable, "-c",
            "from litcoin import Agent; "
            "a=Agent.load(); "
            "print(a.balance())",
        ]
        # Or fallback to checking known wallet via bankr CLI
        proc = subprocess.run(
            [sys.executable, "-m", "litcoin", "balance"],
            cwd=str(WORKSPACE / "projects" / "litcoin"),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip()
            # Parse "Balance: 12345 LITCOIN" or raw number
            balance = None
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    balance = int(line)
                elif "LITCOIN" in line or "balance" in line.lower():
                    digits = "".join(ch for ch in line if ch.isdigit() or ch == ".")
                    if digits:
                        balance = int(float(digits))
            result["balance_lit"] = balance
            result["claim_ready"] = (balance is not None and balance >= result["threshold"])
            result["status"] = "ok"
            if result["claim_ready"]:
                logger.warning(f"🚨 LITCOIIN CLAIM READY: {balance} >= {result['threshold']}")
        else:
            result["status"] = "error"
            result["error"] = proc.stderr.strip()[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def lane_B_nookplot_bounties(state: LaneState, executor: "SelfHealExecutor") -> Dict[str, Any]:
    """Poll Nookplot for new bounties matching our skills."""
    result: Dict[str, Any] = {
        "status": "running",
        "bounties_found": 0,
        "new_matches": [],
        "error": None,
    }
    try:
        cmd = [sys.executable, "-m", "nookplot", "bounties", "--format", "json"]
        proc = subprocess.run(
            cmd,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                bounties = data if isinstance(data, list) else data.get("bounties", [])
                result["bounties_found"] = len(bounties)
                # Simple match heuristic: keywords in title/description
                keywords = {"python", "base", "l2", "automation", "research", "ai", "mcp", "security"}
                matches = []
                for b in bounties:
                    text = f"{b.get('title','')} {b.get('description','')}".lower()
                    if any(kw in text for kw in keywords):
                        matches.append({
                            "id": b.get("id"),
                            "title": b.get("title"),
                            "reward": b.get("reward"),
                            "url": b.get("url"),
                        })
                result["new_matches"] = matches[:5]
                result["status"] = "ok"
                if matches:
                    logger.info(f"🔥 Nookplot bounty matches: {[m['title'] for m in matches]}")
            except json.JSONDecodeError:
                result["status"] = "parse_error"
                result["error"] = proc.stdout[:200]
        else:
            result["status"] = "error"
            result["error"] = proc.stderr.strip()[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def lane_C_0xwork_discovery(state: LaneState, executor: "SelfHealExecutor") -> Dict[str, Any]:
    """Discover tasks on 0xWork marketplace."""
    result: Dict[str, Any] = {
        "status": "running",
        "tasks_found": 0,
        "open_tasks": [],
        "error": None,
    }
    try:
        cmd = ["npx", "-y", "0xwork", "discover", "--json"]
        proc = subprocess.run(
            cmd,
            cwd=str(WORKSPACE / "projects" / "0xwork"),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                tasks = data if isinstance(data, list) else data.get("tasks", [])
                result["tasks_found"] = len(tasks)
                open_tasks = [t for t in tasks if t.get("status") == "open"]
                result["open_tasks"] = open_tasks[:5]
                result["status"] = "ok"
                if open_tasks:
                    logger.info(f"💼 0xWork open tasks: {len(open_tasks)}")
            except json.JSONDecodeError:
                result["status"] = "parse_error"
                result["error"] = proc.stdout[:200]
        else:
            result["status"] = "error"
            result["error"] = proc.stderr.strip()[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def lane_D_zyfai_monitor(state: LaneState, executor: "SelfHealExecutor") -> Dict[str, Any]:
    """Monitor Zyfai APY and Safe status."""
    result: Dict[str, Any] = {
        "status": "running",
        "apy_7d": None,
        "safe_balance_usdc": None,
        "strategy": "safe_strategy",
        "error": None,
    }
    try:
        # Read from existing zyfai report if present
        report_file = WORKSPACE / "projects" / "zyfai" / "REPORT.md"
        if report_file.exists():
            text = report_file.read_text()
            # Naive parse for "7d USDC APY: X.XX%"
            for line in text.splitlines():
                if "APY" in line and "%" in line:
                    digits = "".join(ch for ch in line if ch.isdigit() or ch == ".")
                    if digits:
                        result["apy_7d"] = float(digits)
                if "Safe" in line and "0x" in line:
                    addr = line.split("0x")[1].split()[0] if "0x" in line else None
                    if addr:
                        result["safe_address"] = "0x" + addr
            result["status"] = "ok"
        else:
            result["status"] = "no_data"
            result["error"] = "No REPORT.md found"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


LANE_RUNNERS: Dict[str, Callable[[LaneState, "SelfHealExecutor"], Dict[str, Any]]] = {
    "A": lane_A_litcoiin_balance,
    "B": lane_B_nookplot_bounties,
    "C": lane_C_0xwork_discovery,
    "D": lane_D_zyfai_monitor,
}

# ═══════════════════════════════════════════════════════════════════════
# DAEMON CORE
# ═══════════════════════════════════════════════════════════════════════

class ManteclawDaemon:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.threads: Dict[str, threading.Thread] = {}
        self.executor = SelfHealExecutor() if SelfHealExecutor else None
        self.state = LaneState() if LaneState else None
        self._ensure_dirs()

    def _ensure_dirs(self):
        (WORKSPACE / "lanes").mkdir(parents=True, exist_ok=True)

    def _run_lane(self, lane_id: str):
        """Thread worker: run lane on its interval until shutdown."""
        cfg = LANE_CONFIG[lane_id]
        runner = LANE_RUNNERS[lane_id]
        interval = cfg["interval_sec"]
        name = cfg["name"]

        logger.info(f"[{lane_id}] {name} started (interval: {interval}s)")

        while not self.shutdown_event.is_set():
            start = time.time()
            try:
                if not cfg.get("enabled", True):
                    self._update_status(lane_id, "disabled", {})
                    self.shutdown_event.wait(interval)
                    continue

                self._update_status(lane_id, "running", {})
                result = runner(self.state, self.executor)
                result["last_run"] = datetime.utcnow().isoformat() + "Z"
                result["next_run"] = (datetime.utcnow() + timedelta(seconds=interval)).isoformat() + "Z"
                self._update_status(lane_id, result.get("status", "ok"), result)

                # Write to orchestrator state
                if self.state:
                    earnings = result.get("balance_lit") or result.get("bounties_found") or 0
                    blocker = result.get("error")
                    self.state.update_lane(lane_id, {
                        "status": result.get("status", "ok"),
                        "last_run": result["last_run"],
                        "earnings": earnings,
                        "blocker": blocker,
                        "details": {k: v for k, v in result.items() if k not in ("last_run", "next_run")},
                    })

                # If claim ready, escalate
                if result.get("claim_ready"):
                    logger.warning(f"🚨 [{lane_id}] CLAIM THRESHOLD REACHED — action required!")

            except Exception as e:
                logger.exception(f"[{lane_id}] Lane crashed: {e}")
                self._update_status(lane_id, "crashed", {"error": str(e)})

            elapsed = time.time() - start
            sleep_for = max(0, interval - elapsed)
            self.shutdown_event.wait(sleep_for)

        logger.info(f"[{lane_id}] {name} stopped")

    def _update_status(self, lane_id: str, status: str, data: Dict[str, Any]):
        """Write aggregate status to lanes/status.json (atomic)."""
        try:
            tmp = STATUS_FILE.with_suffix(".tmp")
            current: Dict[str, Any] = {}
            if STATUS_FILE.exists():
                try:
                    current = json.loads(STATUS_FILE.read_text())
                except json.JSONDecodeError:
                    current = {}
            if "lanes" not in current:
                current["lanes"] = {}
            current["lanes"][lane_id] = {
                "status": status,
                **data,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            current["daemon_heartbeat"] = datetime.utcnow().isoformat() + "Z"
            tmp.write_text(json.dumps(current, indent=2))
            os.replace(str(tmp), str(STATUS_FILE))
        except Exception as e:
            logger.warning(f"Failed to write status: {e}")

    def start(self):
        """Spawn lane threads and block until shutdown."""
        logger.info("=" * 60)
        logger.info("Manteclaw Daemon STARTING")
        logger.info(f"Workspace: {WORKSPACE}")
        logger.info(f"PID file: {PID_FILE}")
        logger.info(f"Status file: {STATUS_FILE}")
        logger.info("=" * 60)

        # Write PID
        PID_FILE.write_text(str(os.getpid()))

        # Trap signals
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

        # Spawn threads
        for lane_id in LANE_CONFIG:
            t = threading.Thread(target=self._run_lane, args=(lane_id,), name=f"lane-{lane_id}", daemon=True)
            self.threads[lane_id] = t
            t.start()

        # Block
        try:
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _on_signal(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()

    def stop(self):
        """Signal shutdown and cleanup."""
        logger.info("Manteclaw Daemon STOPPING")
        self.shutdown_event.set()
        for t in self.threads.values():
            t.join(timeout=5)
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("Manteclaw Daemon STOPPED")

    def status(self) -> Dict[str, Any]:
        """Return current daemon + lane status (non-blocking)."""
        if STATUS_FILE.exists():
            try:
                return json.loads(STATUS_FILE.read_text())
            except Exception:
                pass
        return {"error": "No status file"}


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def cli():
    if len(sys.argv) < 2:
        print("Usage: python3 daemon.py [start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        # Check if already running
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text().strip())
                os.kill(pid, 0)
                print(f"Daemon already running (PID {pid}). Use 'stop' first.")
                sys.exit(1)
            except (OSError, ValueError):
                PID_FILE.unlink(missing_ok=True)
        daemon = ManteclawDaemon()
        daemon.start()

    elif cmd == "stop":
        if not PID_FILE.exists():
            print("Daemon not running (no PID file)")
            sys.exit(1)
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to PID {pid}")
            # Wait briefly
            for _ in range(10):
                time.sleep(0.5)
                if not PID_FILE.exists():
                    break
            print("Daemon stopped" if not PID_FILE.exists() else f"PID file still present ({PID_FILE})")
        except (OSError, ValueError) as e:
            print(f"Failed to stop daemon: {e}")
            PID_FILE.unlink(missing_ok=True)

    elif cmd == "status":
        daemon = ManteclawDaemon()
        st = daemon.status()
        print(json.dumps(st, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 daemon.py [start|stop|status]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
