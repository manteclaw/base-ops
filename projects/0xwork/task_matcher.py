#!/usr/bin/env python3
"""
task_matcher.py — Lane C Enhancement
0xWork task discovery + skill matching pipeline.
Polls 0xWork API for open tasks, scores them against Manteclaw's skill tags,
auto-logs high-match tasks to .lane_state.json for human review.
Does NOT auto-bid — human approval required.

Uses selfheal.py retry wrappers for all API calls.

Skill tags: ["Base", "Python", "automation", "research", "crypto", "MCP"]

Usage:
    python3 task_matcher.py                    # Single poll + report
    python3 task_matcher.py --daemon --interval 300  # Background polling every 5 min
    python3 task_matcher.py --min-bounty 10    # Only tasks >= $10
"""

import sys
import json
import os
import time
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

# Import selfheal retry wrappers
sys.path.insert(0, "/root/.openclaw/workspace")
from selfheal import retry, heal

# ── Config ──────────────────────────────────────────────────────────

OXWORK_API_BASE = "https://api.0xwork.org"
OXWORK_DISCOVER_CMD = "npx -y @0xwork/cli discover --json"

# Manteclaw's core skill profile
SKILL_TAGS = ["base", "python", "automation", "research", "crypto", "mcp", "l2", "defi"]

# Category → skill relevance mapping
category_skills = {
    "Code":        ["python", "automation", "mcp", "scripting"],
    "Research":    ["research", "crypto", "base", "defi", "analysis"],
    "Writing":     ["research", "crypto", "automation"],
    "Social":      ["social", "crypto", "base"],
    "Creative":    ["creative", "automation"],
    "Data":        ["python", "automation", "research", "analysis"],
    "Verification": ["verification"],
}

STATE_FILE = Path("/root/.openclaw/workspace/.lane_state.json")

# ── Helpers ─────────────────────────────────────────────────────────

def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_poll": None,
        "tasks_seen": {},   # task_id → {first_seen, last_seen, score, action}
        "tasks_claimed": [],
        "tasks_skipped": [],
        "high_matches": [],
        "total_earned_usdc": 0.0,
    }


def save_state(state: Dict[str, Any]):
    state["saved_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def score_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Score a task against our skill profile. Returns enriched task dict."""
    desc = str(task.get("description", "")).lower()
    title = str(task.get("title", "")).lower()
    category = str(task.get("category", ""))
    requirements = str(task.get("requirements", "")).lower()
    text = f"{desc} {title} {requirements}"
    
    # Base score from category match
    relevant = category_skills.get(category, [])
    category_score = sum(1 for s in relevant if s in SKILL_TAGS) * 2
    
    # Keyword matches
    keyword_hits = [tag for tag in SKILL_TAGS if tag in text]
    keyword_score = len(keyword_hits) * 1.5
    
    # Special signals
    bonus = 0
    if "base" in text or "l2" in text:
        bonus += 3  # Native to our chain
    if "mcp" in text or "model context protocol" in text:
        bonus += 3  # Our specialty
    if "automation" in text or "bot" in text or "agent" in text:
        bonus += 2
    if "smart contract" in text or "solidity" in text:
        bonus += 1
    if "defi" in text or "yield" in text or "apy" in text:
        bonus += 2
    
    # Penalties
    penalty = 0
    if any(w in text for w in ["frontend", "ui/ux", "design", "logo", "banner", "image generation"]):
        penalty += 3  # We don't do visual
    if any(w in text for w in ["physical", "location", "photo", "kyc", "identity verification"]):
        penalty += 5  # Can't do physical
    if "safetyFlags" in task and task["safetyFlags"]:
        penalty += 5  # Flagged tasks
    
    total_score = category_score + keyword_score + bonus - penalty
    max_possible = len(SKILL_TAGS) * 2 + len(SKILL_TAGS) * 1.5 + 5  # rough max
    normalized = max(0, min(100, int((total_score / max_possible) * 100)))
    
    return {
        "chain_task_id": task.get("chainTaskId") or task.get("dbId"),
        "category": category,
        "bounty_usd": float(task.get("bounty", 0) or 0),
        "description_preview": task.get("description", "")[:120] + "...",
        "poster": task.get("poster", "N/A"),
        "created_at": task.get("createdAt", "N/A"),
        "score": normalized,
        "score_breakdown": {
            "category": category_score,
            "keywords": keyword_hits,
            "keyword_score": keyword_score,
            "bonus": bonus,
            "penalty": penalty,
            "raw_total": total_score,
        },
        "safety_flags": task.get("safetyFlags", []),
        "deadline": task.get("deadlineHuman", "N/A"),
    }


# ── API Functions (with selfheal) ───────────────────────────────────

@heal(service="0xwork-api", max_retries=5, base_delay=3.0)
def fetch_tasks_api(min_bounty: float = 0, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch open tasks from 0xWork REST API."""
    import urllib.request
    import urllib.error
    
    url = f"{OXWORK_API_BASE}/tasks?status=Open"
    if category:
        url += f"&category={category}"
    
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Manteclaw-TaskMatcher/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        tasks = tasks if isinstance(tasks, list) else []
        if min_bounty > 0:
            tasks = [t for t in tasks if float(t.get("bounty", 0) or 0) >= min_bounty]
        return tasks


@heal(service="0xwork-cli", max_retries=3, base_delay=5.0)
def fetch_tasks_cli() -> List[Dict[str, Any]]:
    """Fallback: use 0xWork CLI discover (requires no wallet)."""
    import subprocess
    result = subprocess.run(
        OXWORK_DISCOVER_CMD.split(),
        capture_output=True,
        text=True,
        timeout=60,
        cwd="/root/.openclaw/workspace/projects/0xwork",
    )
    if result.returncode != 0:
        raise RuntimeError(f"0xwork CLI failed: {result.stderr[:200]}")
    data = json.loads(result.stdout)
    return data.get("tasks", [])


# ── Core Logic ─────────────────────────────────────────────────────

def poll_tasks(min_bounty: float = 0, use_cli: bool = False) -> Dict[str, Any]:
    """Poll for tasks, score them, update state."""
    state = load_state()
    
    try:
        if use_cli:
            tasks = fetch_tasks_cli()
        else:
            tasks = fetch_tasks_api(min_bounty=min_bounty)
    except Exception as e:
        print(f"[WARN] API poll failed ({e}), trying CLI fallback...")
        try:
            tasks = fetch_tasks_cli()
        except Exception as e2:
            print(f"[ERROR] CLI fallback also failed: {e2}")
            return {"error": str(e2), "tasks": [], "high_matches": []}
    
    scored = [score_task(t) for t in tasks]
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    new_tasks = []
    high_matches = []
    
    for s in scored:
        tid = s["chain_task_id"]
        if tid is None:
            continue
        
        tid_str = str(tid)
        if tid_str not in state["tasks_seen"]:
            state["tasks_seen"][tid_str] = {
                "first_seen": now,
                "last_seen": now,
                "score": s["score"],
                "bounty": s["bounty_usd"],
                "category": s["category"],
                "action": "pending_review",
            }
            new_tasks.append(s)
        else:
            state["tasks_seen"][tid_str]["last_seen"] = now
        
        if s["score"] >= 60:
            high_matches.append(s)
    
    state["last_poll"] = now
    if high_matches:
        state["high_matches"] = [h["chain_task_id"] for h in high_matches[:20]]
    
    save_state(state)
    
    return {
        "poll_time": now,
        "tasks_found": len(tasks),
        "new_tasks": len(new_tasks),
        "high_matches": high_matches,
        "all_scored": scored,
        "state_file": str(STATE_FILE),
    }


def print_report(report: Dict[str, Any]):
    print(f"\n{'='*70}")
    print(f"  0xWORK TASK MATCHER — {report['poll_time']}")
    print(f"{'='*70}")
    print(f"  Tasks found: {report['tasks_found']} | New: {report['new_tasks']}")
    
    if report.get("high_matches"):
        print(f"\n  🔥 HIGH MATCHES (score ≥60) — {len(report['high_matches'])} tasks:")
        for h in report["high_matches"]:
            print(f"  ┌ Task #{h['chain_task_id']} | {h['category']:12} | ${h['bounty_usd']:.0f} | Score: {h['score']}/100")
            print(f"  │ Poster: {h['poster'][:20]}... | Created: {h['created_at'][:10]}")
            print(f"  │ {h['description_preview']}")
            print(f"  └ Keywords: {', '.join(h['score_breakdown']['keywords']) or 'none'}")
            print()
    else:
        print(f"\n  😴 No high-match tasks this poll. (Score threshold: 60/100)")
    
    if report.get("all_scored"):
        print(f"  ── All Scored Tasks ──")
        for s in report["all_scored"]:
            flag = "🔥" if s["score"] >= 60 else "  "
            print(f"  {flag} #{s['chain_task_id']:4} | {s['category']:10} | ${s['bounty_usd']:>5.0f} | Score: {s['score']:3}/100 | {s['description_preview'][:50]}")
    
    print(f"\n  State saved to: {report['state_file']}")
    print(f"{'='*70}\n")


# ── Daemon Mode ────────────────────────────────────────────────────

def daemon_loop(interval: int = 300, min_bounty: float = 0):
    print(f"[DAEMON] Starting 0xWork task matcher — poll every {interval}s")
    print(f"[DAEMON] Press Ctrl+C to stop")
    try:
        while True:
            report = poll_tasks(min_bounty=min_bounty)
            print_report(report)
            print(f"[DAEMON] Sleeping {interval}s...\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[DAEMON] Stopped.")


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="0xWork Task Matcher")
    parser.add_argument("--min-bounty", type=float, default=0, help="Minimum bounty in USDC")
    parser.add_argument("--daemon", action="store_true", help="Run as background poller")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds (default: 300)")
    parser.add_argument("--cli", action="store_true", help="Use CLI instead of REST API")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()
    
    if args.daemon:
        daemon_loop(interval=args.interval, min_bounty=args.min_bounty)
    else:
        report = poll_tasks(min_bounty=args.min_bounty, use_cli=args.cli)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print_report(report)


if __name__ == "__main__":
    main()
