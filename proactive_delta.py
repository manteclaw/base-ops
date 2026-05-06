#!/usr/bin/env python3
"""
Proactive Delta Engine — Only acts/speaks when state CHANGES.
Integrates with daemon.py heartbeat to eliminate noise.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Callable, Optional

STATE_FILE = "/root/.openclaw/workspace/.lane_state/proactive_state.json"
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


class ProactiveDelta:
    """
    Attach callbacks to state keys. Only fires when value changes.
    Eliminates "I checked, nothing changed" spam.
    """
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self._state = self._load()
        self._handlers: Dict[str, Callable[[Any, Any], Optional[str]]] = {}
    
    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return {}
    
    def _save(self):
        with open(self.state_file, "w") as f:
            json.dump(self._state, f, indent=2)
    
    def on_change(self, key: str, handler: Callable[[Any, Any], Optional[str]]):
        """Register a handler: handler(old_val, new_val) -> message or None."""
        self._handlers[key] = handler
    
    def check(self, key: str, new_value: Any) -> Optional[str]:
        """
        Check if key changed. If yes, fire handler and return message.
        If no change, return None (stay silent).
        """
        old_value = self._state.get(key)
        
        # JSON-safe comparison
        if json.dumps(old_value, sort_keys=True) == json.dumps(new_value, sort_keys=True):
            return None  # No change = no noise
        
        self._state[key] = new_value
        self._save()
        
        handler = self._handlers.get(key)
        if handler:
            return handler(old_value, new_value)
        return None
    
    def bulk_check(self, readings: Dict[str, Any]) -> list[str]:
        """Check multiple keys, return only messages for changed ones."""
        messages = []
        for key, value in readings.items():
            msg = self.check(key, value)
            if msg:
                messages.append(msg)
        return messages
    
    def reset(self):
        self._state = {}
        self._save()


# ── Pre-built handlers for common lanes ──

def litcoiin_balance_handler(old, new):
    if new >= 50000 and (old is None or old < 50000):
        return f"💰 Litcoiin balance hit {new:,.0f} — CLAIM NOW!"
    if new > (old or 0) + 1000:
        return f"⛏️ Litcoiin +{new - (old or 0):,.0f} → {new:,.0f} total"
    return None

def nookplot_bounty_handler(old, new):
    if new and (not old or len(new) > len(old)):
        return f"🔥 New Nookplot bounties available: {len(new)} total"
    return None

def marketplace_task_handler(old, new):
    if new and (not old or len(new) > len(old)):
        return f"📋 New tasks on 0xWork: {len(new)} matches"
    return None

def calendar_event_handler(old, new):
    if new:
        soon = [e for e in new if e.get("minutes_until", 999) < 120]
        if soon:
            return f"📅 Event soon: {soon[0].get('title', 'Unknown')} in {soon[0].get('minutes_until')} min"
    return None


# ── Bootstrap standard watches ──
def _bootstrap():
    watch("litcoiin_balance", litcoiin_balance_handler)
    watch("nookplot_bounties", nookplot_bounty_handler)
    watch("0xwork_tasks", marketplace_task_handler)
    watch("calendar_events", calendar_event_handler)

# ── Singleton + convenience ──
_engine: Optional[ProactiveDelta] = None

def get_engine() -> ProactiveDelta:
    global _engine
    if _engine is None:
        _engine = ProactiveDelta()
    return _engine


def watch(key: str, handler: Callable):
    get_engine().on_change(key, handler)


def check(key: str, value: Any) -> Optional[str]:
    return get_engine().check(key, value)


def check_all(readings: Dict[str, Any]) -> list[str]:
    return get_engine().bulk_check(readings)


# ── Daemon / heartbeat mode ──

def heartbeat_cycle(config_path: str = "proactive_delta_config.json"):
    """Run one heartbeat check cycle against orchestrator state."""
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)

    # Read current lane states from orchestrator
    lane_state = {}
    if os.path.exists(".lane_state.json"):
        with open(".lane_state.json") as f:
            lane_state = json.load(f)

    engine = get_engine()
    messages = []

    # Litcoiin balance
    if config.get("lanes", {}).get("litcoiin_balance", {}).get("enabled", True):
        bal = lane_state.get("lane_a", {}).get("litcoiin_balance")
        if bal is not None:
            msg = engine.check("litcoiin_balance", bal)
            if msg:
                messages.append(msg)

    # Nookplot bounties
    if config.get("lanes", {}).get("nookplot_bounties", {}).get("enabled", True):
        bounties = lane_state.get("lane_b", {}).get("bounties")
        if bounties is not None:
            msg = engine.check("nookplot_bounties", bounties)
            if msg:
                messages.append(msg)

    # 0xWork tasks
    if config.get("lanes", {}).get("0xwork_tasks", {}).get("enabled", True):
        tasks = lane_state.get("lane_c", {}).get("tasks")
        if tasks is not None:
            msg = engine.check("0xwork_tasks", tasks)
            if msg:
                messages.append(msg)

    # Calendar events
    if config.get("lanes", {}).get("calendar_events", {}).get("enabled", True):
        events = lane_state.get("global", {}).get("calendar_events", [])
        if events:
            msg = engine.check("calendar_events", events)
            if msg:
                messages.append(msg)

    # Webhook dispatch
    webhook_url = config.get("webhooks", {}).get("url", "")
    if messages and webhook_url and config.get("webhooks", {}).get("enabled", False):
        try:
            import requests
            requests.post(webhook_url, json={"alerts": messages, "timestamp": datetime.utcnow().isoformat()}, timeout=10)
        except Exception:
            pass

    return messages


def daemon_loop(config_path: str = "proactive_delta_config.json"):
    """Background heartbeat loop."""
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)

    interval = config.get("heartbeat_interval_seconds", 300)
    print(f"🔔 Proactive delta monitor starting — interval: {interval}s")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            msgs = heartbeat_cycle(config_path)
            if msgs:
                for m in msgs:
                    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {m}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


# ── CLI ──
if __name__ == "__main__":
    import argparse, time
    _bootstrap()
    parser = argparse.ArgumentParser(description="Proactive Delta Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run background heartbeat loop")
    parser.add_argument("--config", default="proactive_delta_config.json", help="Config file path")
    parser.add_argument("--test", action="store_true", help="Run demo checks and exit")
    parser.add_argument("--reset", action="store_true", help="Clear state and exit")
    args = parser.parse_args()

    if args.reset:
        get_engine().reset()
        print("State cleared.")
        exit(0)

    if args.test:
        print(check("litcoiin_balance", 48000))   # None
        print(check("litcoiin_balance", 51000))   # Claim alert
        print(check("litcoiin_balance", 51500))   # Increment
        print(check("litcoiin_balance", 51500))   # None (same)
        exit(0)

    if args.daemon:
        daemon_loop(args.config)
    else:
        msgs = heartbeat_cycle(args.config)
        if msgs:
            for m in msgs:
                print(m)
        else:
            print("No changes detected.")
