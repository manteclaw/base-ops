#!/usr/bin/env python3
"""
Manteclaw Reporting Engine — Signal-to-noise optimized.
Only surfaces actionable deltas. No "I checked, nothing changed."
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

STATE_DIR = "/root/.openclaw/workspace/.lane_state"
os.makedirs(STATE_DIR, exist_ok=True)


@dataclass
class LaneSnapshot:
    """Minimal snapshot of a lane's state. Only what matters."""
    lane: str
    status: str              # "earning", "blocked", "idle", "error"
    earnings_delta: float = 0.0   # Change since last report
    blocker: Optional[str] = None
    next_action: Optional[str] = None
    urgency: str = "low"      # "low", "medium", "high", "critical"


class DeltaReporter:
    """
    Compares current state against last-known state.
    Only returns items that CHANGED or need attention.
    """
    
    def __init__(self, state_file: str = f"{STATE_DIR}/last_reported.json"):
        self.state_file = state_file
        self._last = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return {}
    
    def _save(self, current: dict):
        with open(self.state_file, "w") as f:
            json.dump(current, f, indent=2)
    
    def report(self, lanes: list[LaneSnapshot]) -> str:
        """
        Returns human-readable report of ONLY changed/urgent items.
        Silent on "same as before" unless it's been >6h since last report.
        """
        current = {s.lane: asdict(s) for s in lanes}
        lines = []
        now = datetime.utcnow()
        
        for snap in lanes:
            lane_id = snap.lane
            prev = self._last.get(lane_id, {})
            
            # Always report if status changed
            if prev.get("status") != snap.status:
                lines.append(self._format_change(snap, prev))
                continue
            
            # Always report if blocker appeared or cleared
            if prev.get("blocker") != snap.blocker:
                if snap.blocker:
                    lines.append(f"🚫 [{snap.lane}] NEW BLOCKER: {snap.blocker}")
                else:
                    lines.append(f"✅ [{snap.lane}] Blocker cleared — resuming")
                continue
            
            # Always report earnings changes
            if abs(snap.earnings_delta) > 0:
                lines.append(f"💰 [{snap.lane}] +{snap.earnings_delta:.4f} since last check")
                continue
            
            # Always report critical/high urgency
            if snap.urgency in ("critical", "high"):
                lines.append(self._format_change(snap, prev))
                continue
            
            # Medium urgency: only if >6h since last report of this lane
            if snap.urgency == "medium":
                last_time = prev.get("_reported_at")
                if last_time:
                    last_dt = datetime.fromisoformat(last_time)
                    if (now - last_dt).total_seconds() > 21600:  # 6h
                        lines.append(self._format_reminder(snap))
                else:
                    lines.append(self._format_reminder(snap))
            
            # Low urgency: silent
        
        # Update timestamps for reported lanes
        for snap in lanes:
            if snap.lane in [s.lane for s in lanes if self._should_report(snap)]:
                current[snap.lane]["_reported_at"] = now.isoformat()
        
        self._save(current)
        
        if not lines:
            return ""
        
        header = f"⚡ Manteclaw Status — {now.strftime('%H:%M UTC')}"
        return header + "\n" + "\n".join(lines)
    
    def _should_report(self, snap: LaneSnapshot) -> bool:
        prev = self._last.get(snap.lane, {})
        return (
            prev.get("status") != snap.status
            or prev.get("blocker") != snap.blocker
            or abs(snap.earnings_delta) > 0
            or snap.urgency in ("critical", "high")
        )
    
    def _format_change(self, snap: LaneSnapshot, prev: dict) -> str:
        emoji = {"earning": "⛏️", "blocked": "🚫", "idle": "⏸️", "error": "💥"}.get(snap.status, "❓")
        prev_status = prev.get("status", "unknown")
        return f"{emoji} [{snap.lane}] {prev_status} → {snap.status} | {snap.next_action or 'no action needed'}"
    
    def _format_reminder(self, snap: LaneSnapshot) -> str:
        emoji = {"earning": "⛏️", "blocked": "🚫", "idle": "⏸️", "error": "💥"}.get(snap.status, "❓")
        return f"{emoji} [{snap.lane}] {snap.status} | {snap.next_action or 'monitoring'}"


def quick_report(lane: str, status: str, earnings_delta: float = 0, blocker: str = None, next_action: str = None, urgency: str = "low") -> str:
    """One-liner to generate a single lane report."""
    reporter = DeltaReporter()
    snap = LaneSnapshot(lane=lane, status=status, earnings_delta=earnings_delta, blocker=blocker, next_action=next_action, urgency=urgency)
    return reporter.report([snap])


if __name__ == "__main__":
    # Demo
    reporter = DeltaReporter()
    lanes = [
        LaneSnapshot("A-Litcoiin", "earning", earnings_delta=23.5, next_action="claim at 50k", urgency="low"),
        LaneSnapshot("B-Nookplot", "blocked", blocker="private key mismatch", next_action="regenerate agent key", urgency="high"),
        LaneSnapshot("C-0xWork", "idle", next_action="poll for tasks", urgency="low"),
        LaneSnapshot("F-Zyfai", "earning", earnings_delta=0.12, next_action="compound yield", urgency="low"),
    ]
    print(reporter.report(lanes))
    print("\n--- Second call (same state, should be silent) ---")
    print(reporter.report(lanes))
