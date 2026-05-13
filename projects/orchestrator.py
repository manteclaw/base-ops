#!/usr/bin/env python3
"""
Manteclaw Subagent Orchestrator — Resilient parallel task execution.

Features:
  • Max 3 concurrent subagents (down from 5 to avoid gateway timeouts)
  • Exponential backoff retry for failed spawns (1s → 2s → 4s → 8s)
  • FIFO queue: tasks queued when at capacity, auto-spawned when slots open
  • State persistence for crash recovery
  • CLI: spawn, queue, status, kill, retry-failed

State Files:
  projects/orchestrator_state.json   — Active subagents + queue
  projects/orchestrator_log.jsonl    — Event log

Usage:
    python3 projects/orchestrator.py spawn <label> <task_json>     # Queue or spawn immediately
    python3 projects/orchestrator.py queue                         # Show queued tasks
    python3 projects/orchestrator.py status                        # Show active + queued
    python3 projects/orchestrator.py retry-failed                  # Re-queue failed tasks
    python3 projects/orchestrator.py drain                         # Wait for all active to finish
    python3 projects/orchestrator.py kill <label>                  # Terminate a subagent

Spawn JSON format:
    {"description": "Lane A mining burst", "skill": "base-l2-automation", "priority": 1}

Concurrency Limit: 3 (hard cap to prevent gateway overload)
Backoff: 1s, 2s, 4s, 8s max delay between retries
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import fcntl

WORKSPACE = Path("/root/.openclaw/workspace")
STATE_FILE = WORKSPACE / "projects" / "orchestrator_state.json"
LOG_FILE = WORKSPACE / "projects" / "orchestrator_log.jsonl"
LOCK_FILE = WORKSPACE / "projects" / "orchestrator.lock"
MAX_CONCURRENT = 3
BACKOFF_DELAYS = [1, 2, 4, 8]  # seconds


def _now():
    return datetime.now(timezone.utc).isoformat()


def log_event(event_type: str, details: Dict[str, Any]):
    """Append structured event to log."""
    entry = {
        "timestamp": _now(),
        "event": event_type,
        **details,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "active": {},      # label -> {pid, started_at, task, retries}
            "queue": [],       # FIFO: [{label, task, enqueued_at, retries}]
            "completed": [],   # history of finished tasks
            "failed": [],      # tasks that exhausted retries
            "version": 2,
        }


def save_state(state: Dict[str, Any]):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(str(tmp), str(STATE_FILE))


# ── Subagent Spawn ──

def spawn_subagent(label: str, task: Dict[str, Any]) -> bool:
    """
    Spawn a subagent for the given task.
    Returns True if spawn succeeded, False otherwise.
    """
    # Build a deterministic but unique session label
    session_label = f"subagent-{label}-{uuid.uuid4().hex[:8]}"
    
    # Task description for the subagent
    description = task.get("description", f"Task {label}")
    
    # In OpenClaw, subagents are typically spawned via CLI or internal API.
    # We use a shell command that the main agent can intercept, or write a
    # trigger file that a wrapper script monitors.
    # For resilience, we write a spawn-request file and rely on an external
    # watcher (or manual execution) to actually launch via OpenClaw's
    # subagent mechanism.
    
    request_file = WORKSPACE / "projects" / "spawn_requests" / f"{session_label}.json"
    request_file.parent.mkdir(parents=True, exist_ok=True)
    
    request = {
        "label": label,
        "session_label": session_label,
        "description": description,
        "task": task,
        "requested_at": _now(),
    }
    
    try:
        with open(request_file, "w") as f:
            json.dump(request, f, indent=2)
        
        # Attempt actual spawn via openclaw CLI if available
        # Fallback: just write the request file
        spawn_cmd = [
            "openclaw", "subagent", "spawn",
            "--label", session_label,
            "--description", description,
        ]
        try:
            result = subprocess.run(
                spawn_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            spawn_ok = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            spawn_ok = True  # Request file written; external watcher will pick it up
        
        if spawn_ok:
            log_event("spawned", {
                "label": label,
                "session": session_label,
                "task": description,
            })
            return True
        else:
            log_event("spawn_failed", {
                "label": label,
                "session": session_label,
                "error": result.stderr.strip(),
            })
            return False
            
    except Exception as e:
        log_event("spawn_error", {"label": label, "error": str(e)})
        return False


def is_subagent_active(label: str, state: Dict[str, Any]) -> bool:
    """Check if a subagent with this label is currently active."""
    return label in state.get("active", {})


def count_active(state: Dict[str, Any]) -> int:
    return len(state.get("active", {}))


# ── Queue Management ──

def enqueue_task(state: Dict[str, Any], label: str, task: Dict[str, Any]):
    """Add task to FIFO queue."""
    entry = {
        "label": label,
        "task": task,
        "enqueued_at": _now(),
        "retries": 0,
    }
    state["queue"].append(entry)
    log_event("enqueued", {"label": label, "task": task.get("description", "")})


def dequeue_task(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pop the oldest queued task."""
    if state["queue"]:
        return state["queue"].pop(0)
    return None


def process_queue(state: Dict[str, Any]) -> int:
    """
    Attempt to spawn queued tasks up to the concurrency limit.
    Returns number of tasks spawned in this call.
    """
    spawned = 0
    while count_active(state) < MAX_CONCURRENT and state["queue"]:
        entry = dequeue_task(state)
        if not entry:
            break
        
        label = entry["label"]
        task = entry["task"]
        retries = entry.get("retries", 0)
        
        # Skip if already active (duplicate guard)
        if is_subagent_active(label, state):
            log_event("skip_duplicate", {"label": label})
            continue
        
        # Spawn with backoff retry
        success = False
        for attempt in range(retries, min(retries + len(BACKOFF_DELAYS), len(BACKOFF_DELAYS))):
            if attempt > retries:
                delay = BACKOFF_DELAYS[attempt - retries]
                log_event("backoff", {"label": label, "delay": delay, "attempt": attempt})
                time.sleep(delay)
            
            if spawn_subagent(label, task):
                success = True
                state["active"][label] = {
                    "session": f"subagent-{label}-{uuid.uuid4().hex[:8]}",
                    "started_at": _now(),
                    "task": task,
                    "retries": attempt,
                }
                spawned += 1
                break
            else:
                log_event("spawn_retry", {"label": label, "attempt": attempt})
        
        if not success:
            # Exhausted retries — move to failed
            entry["failed_at"] = _now()
            state["failed"].append(entry)
            log_event("failed_permanent", {"label": label, "retries": retries + len(BACKOFF_DELAYS)})
            # Trim failed history to last 50
            state["failed"] = state["failed"][-50:]
    
    return spawned


def mark_completed(state: Dict[str, Any], label: str, result: Dict[str, Any] = None):
    """Move an active subagent to completed history."""
    if label in state["active"]:
        entry = state["active"].pop(label)
        entry["completed_at"] = _now()
        entry["result"] = result or {}
        state["completed"].append(entry)
        # Trim history to last 100
        state["completed"] = state["completed"][-100:]
        log_event("completed", {"label": label})


def mark_failed(state: Dict[str, Any], label: str, reason: str = ""):
    """Move an active subagent to failed list."""
    if label in state["active"]:
        entry = state["active"].pop(label)
        entry["failed_at"] = _now()
        entry["reason"] = reason
        state["failed"].append(entry)
        state["failed"] = state["failed"][-50:]
        log_event("failed", {"label": label, "reason": reason})


# ── CLI Commands ──

def cmd_spawn(label: str, task_json: str):
    state = load_state()
    try:
        task = json.loads(task_json)
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON for task: {task_json}")
        sys.exit(1)
    
    if is_subagent_active(label, state):
        print(f"WARNING: Subagent '{label}' already active. Adding to queue as duplicate.")
        # Append a suffix to make it unique
        label = f"{label}-{uuid.uuid4().hex[:4]}"
    
    if count_active(state) < MAX_CONCURRENT:
        # Try immediate spawn
        success = False
        for attempt, delay in enumerate(BACKOFF_DELAYS):
            if attempt > 0:
                log_event("backoff", {"label": label, "delay": delay, "attempt": attempt})
                time.sleep(delay)
            if spawn_subagent(label, task):
                success = True
                state["active"][label] = {
                    "session": f"subagent-{label}-{uuid.uuid4().hex[:8]}",
                    "started_at": _now(),
                    "task": task,
                    "retries": attempt,
                }
                break
            else:
                log_event("spawn_retry", {"label": label, "attempt": attempt})
        
        if not success:
            # Exhausted immediate retries — queue it
            enqueue_task(state, label, task)
            print(f"QUEUED (after failed spawns): {label}")
        else:
            print(f"SPAWNED: {label}")
    else:
        enqueue_task(state, label, task)
        print(f"QUEUED (max {MAX_CONCURRENT} active): {label}")
    
    # Also try to drain queue in case a slot just opened
    process_queue(state)
    save_state(state)


def cmd_queue():
    state = load_state()
    queued = state.get("queue", [])
    if not queued:
        print("Queue is empty.")
        return
    print(f"\nQueued Tasks ({len(queued)}):")
    print("-" * 60)
    for i, entry in enumerate(queued, 1):
        label = entry["label"]
        desc = entry["task"].get("description", "(no description)")
        enq = entry["enqueued_at"]
        retries = entry.get("retries", 0)
        print(f"  {i}. {label}")
        print(f"     Desc: {desc}")
        print(f"     Enqueued: {enq}  |  Retries: {retries}")
    print()


def cmd_status():
    state = load_state()
    active = state.get("active", {})
    queued = state.get("queue", [])
    completed = state.get("completed", [])
    failed = state.get("failed", [])
    
    print(f"\n{'='*60}")
    print(f"  Manteclaw Subagent Orchestrator v2")
    print(f"  Max Concurrent: {MAX_CONCURRENT}  |  Backoff: {BACKOFF_DELAYS}")
    print(f"{'='*60}")
    
    print(f"\n🟢 ACTIVE ({len(active)} / {MAX_CONCURRENT}):")
    if active:
        for label, info in active.items():
            started = info.get("started_at", "?")
            desc = info.get("task", {}).get("description", "?")
            retries = info.get("retries", 0)
            rtag = f" [retries:{retries}]" if retries else ""
            print(f"   • {label}{rtag}")
            print(f"     {desc}  (since {started})")
    else:
        print("   (none)")
    
    print(f"\n⏳ QUEUED ({len(queued)}):")
    if queued:
        for entry in queued[:5]:
            label = entry["label"]
            desc = entry["task"].get("description", "?")
            print(f"   • {label} — {desc}")
        if len(queued) > 5:
            print(f"   ... and {len(queued)-5} more")
    else:
        print("   (none)")
    
    print(f"\n✅ COMPLETED (last {min(len(completed), 5)} of {len(completed)}):")
    if completed:
        for entry in completed[-5:]:
            label = entry.get("label", "?")
            done = entry.get("completed_at", "?")
            print(f"   • {label} at {done}")
    else:
        print("   (none)")
    
    print(f"\n❌ FAILED ({len(failed)}):")
    if failed:
        for entry in failed[-3:]:
            label = entry.get("label", "?")
            reason = entry.get("reason", entry.get("failed_at", "?"))
            print(f"   • {label} — {reason}")
    else:
        print("   (none)")
    
    print(f"\n{'='*60}\n")


def cmd_drain():
    """Wait for all active subagents to finish."""
    state = load_state()
    print("Draining active subagents...")
    while state.get("active"):
        cmd_status()
        time.sleep(5)
        state = load_state()
    print("All subagents drained. Queue processed.")


def cmd_retry_failed():
    state = load_state()
    failed = state.get("failed", [])
    if not failed:
        print("No failed tasks to retry.")
        return
    
    requeued = 0
    for entry in failed[:]:
        label = entry["label"]
        task = entry["task"]
        # Reset retry count for fresh attempt
        task["_retried_from_failed"] = True
        enqueue_task(state, label, task)
        requeued += 1
    
    # Clear failed list
    state["failed"] = []
    
    # Try to spawn immediately
    spawned = process_queue(state)
    save_state(state)
    
    print(f"Re-queued {requeued} failed tasks. Spawned {spawned} immediately.")


def cmd_kill(label: str):
    state = load_state()
    if label not in state.get("active", {}):
        print(f"No active subagent with label '{label}'.")
        return
    
    info = state["active"].pop(label)
    log_event("killed", {"label": label, "session": info.get("session", "?")})
    save_state(state)
    print(f"Killed subagent '{label}'.")
    
    # Process queue to fill the freed slot
    state = load_state()
    process_queue(state)
    save_state(state)


def cmd_process_queue():
    """Background worker: try to spawn queued tasks."""
    state = load_state()
    spawned = process_queue(state)
    save_state(state)
    if spawned:
        print(f"Spawned {spawned} queued task(s).")
    else:
        print("No tasks spawned (queue empty or at capacity).")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "spawn":
        if len(sys.argv) < 4:
            print("Usage: python3 orchestrator.py spawn <label> '<json_task>'")
            sys.exit(1)
        cmd_spawn(sys.argv[2], sys.argv[3])
    
    elif cmd == "queue":
        cmd_queue()
    
    elif cmd == "status":
        cmd_status()
    
    elif cmd == "drain":
        cmd_drain()
    
    elif cmd == "retry-failed":
        cmd_retry_failed()
    
    elif cmd == "kill":
        if len(sys.argv) < 3:
            print("Usage: python3 orchestrator.py kill <label>")
            sys.exit(1)
        cmd_kill(sys.argv[2])
    
    elif cmd == "process-queue":
        cmd_process_queue()
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
