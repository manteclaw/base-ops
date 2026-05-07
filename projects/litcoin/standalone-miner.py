#!/usr/bin/env python3
"""
Standalone LITCOIN Research Miner — No Bankr required.

Uses your recovered Base wallet to sign submissions directly.
Mines RESEARCH tasks (comprehension was retired 2026-04-24).

Usage:
    cd /root/.openclaw/workspace/projects/litcoin
    source venv/bin/activate
    export LITCOIN_SEED="your seed phrase"
    export OPENROUTER_API_KEY="your key"
    python3 standalone-miner.py
"""

import os
import sys
import time
import json
import logging
import re
import math
from pathlib import Path

# ── Miner state file (survives restarts) ──
STATE_FILE = Path(__file__).with_suffix("").name + "_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("standalone-miner")

COORDINATOR_URL = "https://api.litcoin.app"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"
WALLET_ADDRESS = "0xC4Cf88b691D9b820040d861954d32e0C5f4538b7"
MODEL_PRIMARY = "inclusionai/ling-2.6-1t:free"
MODEL_FALLBACK = "accounts/fireworks/models/llama-v3p3-70b-instruct"
MODEL_OPENROUTER_BACKUP = "nvidia/nemotron-3-super-120b-a12b:free"  # Backup when primary rate-limited
MODEL_FIREWORKS_BACKUP = "accounts/fireworks/models/qwen3-235b-a22b"  # Backup Fireworks model

# Circuit-breaker constants
CB_TRIGGER_FAILURES = 3      # consecutive failures before flipping provider
CB_LOCKOUT_ROUNDS = 2       # how many rounds to stay on the alt provider (reduced from 5)
BACKOFF_BASE_SECONDS = 15    # base for 2^attempt * 15s (reduced from 30)
BACKOFF_MAX_SECONDS = 120    # cap at 2 minutes (reduced from 5 minutes)
KILL_SWITCH_CONSECUTIVE_FAILS = 10

try:
    import requests
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
    from eth_account.messages import encode_defunct
    from mnemonic import Mnemonic
except ImportError:
    log.error("Missing dependencies. Run: pip install requests eth-account mnemonic")
    sys.exit(1)


def load_state():
    """Load persistent miner state from disk."""
    path = Path(STATE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def save_state(state):
    """Write miner state to disk."""
    try:
        Path(STATE_FILE).write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"Failed to save state: {e}")


def get_wallet():
    """Derive wallet from seed phrase."""
    seed = os.environ.get("LITCOIN_SEED", "").strip()
    if not seed:
        wallet_file = Path(__file__).parent.parent.parent / "WALLET.md"
        if wallet_file.exists():
            content = wallet_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if " " in line and len(line.split()) >= 12 and not line.startswith("#"):
                    words = line.split()
                    if len(words) in [12, 15, 18, 21, 24]:
                        seed = line
                        break
    if not seed:
        raise ValueError("No seed phrase found. Set LITCOIN_SEED env var.")
    mnemo = Mnemonic("english")
    if not mnemo.check(seed):
        raise ValueError("Invalid seed phrase checksum")
    account = Account.from_mnemonic(seed, account_path="m/44'/60'/0'/0/0")
    log.info(f"Wallet loaded: {account.address}")
    assert account.address.lower() == WALLET_ADDRESS.lower(), \
        f"Address mismatch! Derived {account.address}, expected {WALLET_ADDRESS}"
    return account


class LitcoiinResearchMiner:
    # Tasks that are too hard for free models — skip entirely
    SKIP_TASK_TYPES = [
        "software_engineering",
        "exploit_forensics",
        "pattern_recognition",
        "mathematics",
        "compiler",
        "compression",
    ]
    # Tasks that don't earn enough (< 50 avg) — skip to save rounds
    LOW_VALUE_TASKS = [
        "algorithm",           # 24.2 avg (22 rounds wasted)
        "knowledge_synthesis", # 27.2 avg
        "verification",        # 23.0 avg
        "ai_safety",           # 30.0 avg
        "runescape_insight",   # 42.6 avg
    ]
    # High-value tasks we want to prioritize (> 100 avg)
    HIGH_VALUE_TASKS = [
        "smart_contracts",      # 193.0 avg
        "instruction_tuning",   # 166.3 avg
        "adversarial_robustness", # 139.1 avg
        "agentic_trace",        # 131.3 avg
        "bioinformatics",       # 94.0 avg
        "tcg_card_profile",     # 80.6 avg
    ]
    # Task rotation: don't repeat same type for N rounds
    TASK_ROTATION_MEMORY = 5  # remember last 5 task types
    # Min solutions to queue before batch submit
    BATCH_SIZE = 1  # set to 3+ to enable batching (coordinator may not support)

    def __init__(self, account, openrouter_key, fireworks_key=None):
        self.account = account
        self.openrouter_key = openrouter_key
        self.fireworks_key = fireworks_key
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["X-Litcoin-SDK"] = "standalone-research-4.14.3"
        self.auth_token = None
        self.auth_expiry = 0
        self.last_model_used = MODEL_PRIMARY

        # ── Enhancement state ──
        self.state = load_state()
        # circuit breaker counters
        self.or_fails = 0                 # consecutive OpenRouter failures
        self.fw_fails = 0                 # consecutive Fireworks failures
        self.cb_lockout_remaining = 0     # rounds left on forced-alt provider
        self.cb_forced_provider = None    # "openrouter" | "fireworks" | None
        # backoff
        self.backoff_attempt = 0          # resets on any success
        # task rotation state
        self.recent_task_types = self.state.get("recent_task_types", [])
        # time-of-day tracking: {hour: {"count": 0, "total": 0}}
        self.hourly_stats = self.state.get("hourly_stats", {})
        # batch submission queue
        self.batch_queue = []
        # solution quality tracking
        self.quality_scores = self.state.get("quality_scores", {})
        self.provider_latency = {}  # {provider: [times]}
        # solution cache: {task_hash: solution}
        self.solution_cache = {}
        self.cache_hits = 0
        # kill switch
        self.consec_global_fails = 0
        self.initial_balance = self.state.get("initial_balance")
        # smart model tracker: {task_type: {model: {"rewards": [], "total": 0, "count": 0}}}
        self.model_tracker = self.state.get("model_tracker", {})
        # round stats
        self.round_count = self.state.get("round_count", 0)
        self.total_earned = self.state.get("total_earned", 0)
        self.best_model_overall = self.state.get("best_model_overall")
        self.last_task_type = self.state.get("last_task_type")

    # ── State helpers ──
    def _persist(self):
        payload = {
            "round_count": self.round_count,
            "total_earned": self.total_earned,
            "last_task_type": self.last_task_type,
            "best_model_overall": self.best_model_overall,
            "model_tracker": self.model_tracker,
            "initial_balance": self.initial_balance,
            "provider_latency": self.provider_latency,
            "cache_hits": self.cache_hits,
            "recent_task_types": self.recent_task_types,
            "hourly_stats": self.hourly_stats,
            "quality_scores": self.quality_scores,
        }
        save_state(payload)

    def _update_model_tracker(self, task_type, model, reward):
        """Record reward for a task_type + model combo."""
        if not model:
            return
        tracker = self.model_tracker.setdefault(task_type, {})
        entry = tracker.setdefault(model, {"total": 0, "count": 0, "avg": 0.0})
        entry["total"] += reward
        entry["count"] += 1
        entry["avg"] = entry["total"] / entry["count"]
        # update overall best
        best = None
        best_avg = -1
        for tt, models in self.model_tracker.items():
            for m, stats in models.items():
                if stats["count"] >= 2 and stats["avg"] > best_avg:
                    best_avg = stats["avg"]
                    best = m
        self.best_model_overall = best

    def _should_rotate_task(self, task_type):
        """Check if this task type was recently used (rotation)."""
        if task_type in self.recent_task_types:
            log.info(f"🔄 Task rotation: {task_type} was recently used, deprioritizing")
            return True
        return False

    def _record_task_type(self, task_type):
        """Remember recent task types for rotation."""
        self.recent_task_types.append(task_type)
        self.recent_task_types = self.recent_task_types[-self.TASK_ROTATION_MEMORY:]

    def _score_solution(self, solution, task_type):
        """Score solution quality (0-100). Higher = better expected reward."""
        score = 50  # base
        # Length bonus: longer solutions often earn more (up to +30)
        length = len(solution)
        if length > 3000:
            score += 30
        elif length > 1500:
            score += 20
        elif length > 500:
            score += 10
        # Complexity bonus: code density
        code_lines = len([l for l in solution.split('\n') if l.strip() and not l.strip().startswith('#')])
        if code_lines > 30:
            score += 15
        elif code_lines > 10:
            score += 5
        # Has imports = real code
        if 'import ' in solution or 'from ' in solution:
            score += 5
        log.info(f"📊 Solution quality score: {score}/100 ({length} chars, {code_lines} code lines)")
        return score

    def _record_hourly(self, reward):
        """Track rewards by hour of day."""
        hour = time.strftime("%H")
        if hour not in self.hourly_stats:
            self.hourly_stats[hour] = {"count": 0, "total": 0}
        self.hourly_stats[hour]["count"] += 1
        self.hourly_stats[hour]["total"] += reward

    def _get_best_hours(self):
        """Return hours sorted by average reward."""
        hours = []
        for h, stats in self.hourly_stats.items():
            if stats["count"] >= 3:
                hours.append((h, stats["total"] / stats["count"]))
        hours.sort(key=lambda x: x[1], reverse=True)
        return hours

    def _add_to_batch(self, task_id, solution, model):
        """Queue solution for batch submission."""
        self.batch_queue.append({"task_id": task_id, "solution": solution, "model": model})
        log.info(f"📦 Batch queue: {len(self.batch_queue)}/{self.BATCH_SIZE}")
        if len(self.batch_queue) >= self.BATCH_SIZE:
            return self._flush_batch()
        return None

    def _flush_batch(self):
        """Submit all queued solutions."""
        if not self.batch_queue:
            return []
        results = []
        log.info(f"🚀 Submitting batch of {len(self.batch_queue)} solutions...")
        for item in self.batch_queue:
            try:
                result = self.submit_solution(item["task_id"], item["solution"], item["model"])
                results.append(result)
            except Exception as e:
                log.error(f"Batch item failed: {e}")
                results.append(None)
        self.batch_queue = []
        return results
        """Track provider response times."""
        if provider not in self.provider_latency:
            self.provider_latency[provider] = []
        self.provider_latency[provider].append(elapsed_ms)
        # Keep last 20 measurements
        self.provider_latency[provider] = self.provider_latency[provider][-20:]

    def _get_fastest_provider(self):
        """Return the provider with lowest average latency."""
        avgs = {}
        for provider, times in self.provider_latency.items():
            if times:
                avgs[provider] = sum(times) / len(times)
        if not avgs:
            return None
        return min(avgs, key=avgs.get)

    def _hash_task(self, task):
        """Create a hash for task caching."""
        import hashlib
        prompt = task.get("prompt", task.get("description", ""))
        task_type = task.get("type", "unknown")
        return hashlib.md5(f"{task_type}:{prompt[:200]}".encode()).hexdigest()

    def _get_cached_solution(self, task):
        """Check if we have a cached solution for this task."""
        task_hash = self._hash_task(task)
        if task_hash in self.solution_cache:
            self.cache_hits += 1
            log.info(f"💾 Cache hit! (hits: {self.cache_hits})")
            return self.solution_cache[task_hash]
        return None

    def _cache_solution(self, task, solution):
        """Cache a successful solution."""
        task_hash = self._hash_task(task)
        self.solution_cache[task_hash] = solution
        # Keep cache under 100 entries
        if len(self.solution_cache) > 100:
            # Remove oldest (first inserted)
            oldest = next(iter(self.solution_cache))
            del self.solution_cache[oldest]

    def _pick_smart_model(self, task_type):
        """Return the model with highest avg reward for this task type (min 2 samples)."""
        tracker = self.model_tracker.get(task_type)
        if not tracker:
            return None
        best = None
        best_avg = -1
        for model, stats in tracker.items():
            if stats["count"] >= 2 and stats["avg"] > best_avg:
                best_avg = stats["avg"]
                best = model
        return best
        models = self.model_tracker.get(task_type, {})
        candidates = [(m, s["avg"], s["count"]) for m, s in models.items() if s["count"] >= 2]
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None

    # ── Provider helpers ──
    def _provider_available(self, name):
        if name == "openrouter":
            return bool(self.openrouter_key)
        if name == "fireworks":
            return bool(self.fireworks_key)
        return False

    def _select_provider(self, task_type):
        """Pick provider respecting circuit breaker, smart model preferences, and latency."""
        # 1. Circuit-breaker lockout overrides everything
        if self.cb_lockout_remaining > 0 and self.cb_forced_provider:
            self.cb_lockout_remaining -= 1
            log.info(f"[CB] Locked to {self.cb_forced_provider} ({self.cb_lockout_remaining+1} rounds left)")
            return self.cb_forced_provider

        # 2. Smart model preference: if a model dominates for this task_type, use its provider
        smart = self._pick_smart_model(task_type)
        if smart:
            if "fireworks" in smart.lower() or "llama" in smart.lower():
                if self._provider_available("fireworks"):
                    return "fireworks"
            if self._provider_available("openrouter"):
                return "openrouter"

        # 3. Latency-based selection: use fastest provider when both healthy
        if (self._provider_available("fireworks") and self.fw_fails < CB_TRIGGER_FAILURES and
            self._provider_available("openrouter") and self.or_fails < CB_TRIGGER_FAILURES):
            fastest = self._get_fastest_provider()
            if fastest:
                log.info(f"[LATENCY] Fastest provider: {fastest} ({self.provider_latency.get(fastest, [])[-3:]}) ms)")
                return fastest

        # 4. Default: Fireworks first if healthy, then OpenRouter
        if self._provider_available("fireworks") and self.fw_fails < CB_TRIGGER_FAILURES:
            return "fireworks"
        if self._provider_available("openrouter") and self.or_fails < CB_TRIGGER_FAILURES:
            return "openrouter"

        # 5. Fallback to whoever is available regardless of failures
        if self._provider_available("openrouter"):
            return "openrouter"
        if self._provider_available("fireworks"):
            return "fireworks"
        return None

    def _record_provider_result(self, provider, success):
        """Update circuit breaker counters."""
        if provider == "openrouter":
            if success:
                self.or_fails = 0
            else:
                self.or_fails += 1
                if self.or_fails >= CB_TRIGGER_FAILURES and self._provider_available("fireworks"):
                    log.warning(f"[CB] OpenRouter failed {self.or_fails}x → locking to Fireworks for {CB_LOCKOUT_ROUNDS} rounds")
                    self.cb_forced_provider = "fireworks"
                    self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
        elif provider == "fireworks":
            if success:
                self.fw_fails = 0
            else:
                self.fw_fails += 1
                if self.fw_fails >= CB_TRIGGER_FAILURES and self._provider_available("openrouter"):
                    log.warning(f"[CB] Fireworks failed {self.fw_fails}x → locking to OpenRouter for {CB_LOCKOUT_ROUNDS} rounds")
                    self.cb_forced_provider = "openrouter"
                    self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS

    def _check_kill_switch(self):
        """Return True if miner should stop immediately."""
        if self.consec_global_fails >= KILL_SWITCH_CONSECUTIVE_FAILS:
            log.error(f"[KILL] {self.consec_global_fails} consecutive global failures — STOPPING")
            return True
        if self.initial_balance is not None:
            try:
                current = self._fetch_balance()
                if current < self.initial_balance:
                    log.error(f"[KILL] Balance dropped: {self.initial_balance} → {current} — STOPPING")
                    return True
            except Exception as e:
                log.warning(f"Balance check failed: {e}")
        return False

    def _auto_claim(self):
        """Attempt to claim rewards when balance hits 50,000 threshold."""
        token = self.authenticate()
        payload = {"miner": self.account.address}
        r = self._api("POST", "/v1/research/claim", json=payload,
                       headers={"Authorization": f"Bearer {token}"}, retries=1)
        if r.status_code == 200:
            result = r.json()
            claimed = result.get("claimed", 0)
            tx_hash = result.get("txHash", "N/A")
            log.info(f"✅ AUTO-CLAIM SUCCESS: {claimed} LITCOIN claimed! TX: {tx_hash}")
            # Reset earned counter since we claimed
            self.total_earned = 0
            self._persist()
            return True
        else:
            log.warning(f"Auto-claim returned {r.status_code}: {r.text[:200]}")
            return False
        """Return True if miner should stop immediately."""
        if self.consec_global_fails >= KILL_SWITCH_CONSECUTIVE_FAILS:
            log.error(f"[KILL] {self.consec_global_fails} consecutive global failures — STOPPING")
            return True
        if self.initial_balance is not None:
            try:
                current = self._fetch_balance()
                if current < self.initial_balance:
                    log.error(f"[KILL] Balance dropped: {self.initial_balance} → {current} — STOPPING")
                    return True
            except Exception as e:
                log.warning(f"Balance check failed: {e}")
        return False

    def _fetch_balance(self):
        """Fetch on-chain ETH balance (proxy for LITCOIN balance check if API available)."""
        # We use the coordinator balance endpoint if it exists, otherwise ETH balance as proxy
        try:
            r = self._api("GET", f"/v1/miner/{self.account.address}/balance", retries=1)
            if r.status_code == 200:
                return r.json().get("balance", 0)
        except Exception:
            pass
        # Fallback: keep stale initial balance so we don't false-kill
        return self.initial_balance or 0

    # ── Core API wrapper with enhanced retry ──
    def _api(self, method, path, **kwargs):
        url = f"{COORDINATOR_URL}{path}"
        retries = kwargs.pop("retries", 3)
        for attempt in range(retries):
            try:
                r = self.session.request(method, url, timeout=30, **kwargs)
                if r.status_code == 429:
                    wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** self.backoff_attempt))
                    log.warning(f"Rate limited, exponential backoff: {wait}s (attempt {self.backoff_attempt})")
                    time.sleep(wait)
                    self.backoff_attempt += 1
                    continue
                if r.status_code >= 500:
                    wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** attempt))
                    log.warning(f"Server error {r.status_code}, retry in {wait}s")
                    time.sleep(wait)
                    continue
                # Success → reset backoff
                self.backoff_attempt = 0
                return r
            except Exception as e:
                if attempt < retries - 1:
                    wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** attempt))
                    log.warning(f"Request failed ({e}), retry in {wait}s")
                    time.sleep(wait)
                else:
                    raise
        raise Exception("All retries exhausted")

    # ── Existing methods with minor instrumentation ──
    def authenticate(self):
        if self.auth_token and time.time() < self.auth_expiry - 60:
            return self.auth_token
        log.info("Authenticating with coordinator...")
        r = self._api("POST", "/v1/auth/nonce", json={"miner": self.account.address})
        if r.status_code != 200:
            raise Exception(f"Nonce failed: {r.status_code} {r.text}")
        message = r.json()["message"]
        signable = encode_defunct(text=message)
        raw_sig = self.account.sign_message(signable)
        signature = "0x" + raw_sig.signature.hex()
        r = self._api("POST", "/v1/auth/verify", json={
            "miner": self.account.address, "message": message, "signature": signature
        })
        if r.status_code != 200:
            raise Exception(f"Auth verify failed: {r.status_code} {r.text}")
        self.auth_token = r.json()["token"]
        self.auth_expiry = time.time() + 3600
        log.info("Authenticated successfully")
        return self.auth_token

    def should_skip_task(self, task_type):
        """Skip tasks that don't earn enough or are too hard."""
        skip_reason = None
        if task_type in self.SKIP_TASK_TYPES:
            skip_reason = "too hard for free model"
        elif task_type in getattr(self, 'LOW_VALUE_TASKS', []):
            skip_reason = "low value (<50 avg)"
        if skip_reason:
            log.warning(f"Skipping {task_type} task ({skip_reason})")
            return True
        return False

    def fetch_task(self, task_type=None):
        """Fetch a suitable research task, prioritizing high-value types with rotation."""
        # Try high-value task types first (respecting rotation)
        if not task_type:
            # Sort by: not recently used first, then random within that group
            candidates = []
            for preferred_type in self.HIGH_VALUE_TASKS:
                if self._should_rotate_task(preferred_type):
                    candidates.append((1, preferred_type))  # lower priority
                else:
                    candidates.append((0, preferred_type))  # higher priority
            candidates.sort(key=lambda x: x[0])
            
            for priority, preferred_type in candidates:
                for _ in range(3):
                    token = self.authenticate()
                    payload = {"miner": self.account.address, "type": preferred_type}
                    r = self._api("POST", "/v1/research/task", json=payload,
                                   headers={"Authorization": f"Bearer {token}"})
                    if r.status_code == 401:
                        self.auth_token = None
                        continue
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    task = data.get("task", data)
                    ttype = task.get("type", "unknown")
                    if self.should_skip_task(ttype):
                        continue
                    log.info(f"🎯 High-value task: {ttype}")
                    return data
        
        # Fallback: any task
        for _ in range(10):
            token = self.authenticate()
            payload = {"miner": self.account.address}
            if task_type:
                payload["type"] = task_type
            r = self._api("POST", "/v1/research/task", json=payload,
                           headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 401:
                self.auth_token = None
                continue
            if r.status_code != 200:
                raise Exception(f"Task fetch failed: {r.status_code} {r.text}")
            data = r.json()
            task = data.get("task", data)
            ttype = task.get("type", "unknown")
            if self.should_skip_task(ttype):
                log.warning(f"Skipping {ttype} task (too hard for free model)")
                continue
            return data
        raise Exception("Could not find a suitable task after 5 attempts")

    def solve_with_llm(self, task):
        """Solve a research task using provider selection + circuit breaker."""
        task_type = task.get("type", "code_optimization")
        prompt = task.get("prompt", task.get("description", ""))
        entry = task.get("constraints", {}).get("entry_function", "solve")

        provider = self._select_provider(task_type)
        if not provider:
            log.error("No LLM provider available. Set OPENROUTER_API_KEY or FIREWORKS_API_KEY.")
            return None, None

        if provider == "fireworks":
            code, model = self._call_fireworks(task_type, prompt, entry)
            success = code is not None
            self._record_provider_result("fireworks", success)
            if success:
                self.last_model_used = model or MODEL_FALLBACK
                return code, self.last_model_used
            # Fallback to OpenRouter if Fireworks failed and we aren't already locked
            if self._provider_available("openrouter") and self.cb_forced_provider != "fireworks":
                log.info("Fireworks failed, trying OpenRouter fallback...")
                code, model = self._call_openrouter(task_type, prompt, entry)
                success2 = code is not None
                self._record_provider_result("openrouter", success2)
                if success2:
                    self.last_model_used = model or MODEL_PRIMARY
                    return code, self.last_model_used

        elif provider == "openrouter":
            code, model = self._call_openrouter(task_type, prompt, entry)
            success = code is not None
            self._record_provider_result("openrouter", success)
            if success:
                self.last_model_used = model or MODEL_PRIMARY
                return code, self.last_model_used
            # Fallback to Fireworks
            if self._provider_available("fireworks") and self.cb_forced_provider != "openrouter":
                log.info("OpenRouter failed, trying Fireworks fallback...")
                code, model = self._call_fireworks(task_type, prompt, entry)
                success2 = code is not None
                self._record_provider_result("fireworks", success2)
                if success2:
                    self.last_model_used = model or MODEL_FALLBACK
                    return code, self.last_model_used

        log.error("Both providers failed to produce a solution.")
        return None, None

    def _call_openrouter(self, task_type, prompt, entry):
        """Call OpenRouter API with model rotation on rate limits."""
        log.info(f"Solving {task_type} task with OpenRouter...")
        system_msg = self._build_system_msg(task_type, entry)
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://litcoin-miner.local",
            "X-Title": "Litcoin Standalone Miner"
        }
        # Smart model override if we have enough data
        smart = self._pick_smart_model(task_type)
        models_to_try = []
        if smart and ":" in smart:
            models_to_try.append(smart)
        models_to_try.extend([MODEL_PRIMARY, MODEL_OPENROUTER_BACKUP])
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }
            try:
                start = time.time()
                r = requests.post(f"{OPENROUTER_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=60)
                elapsed = (time.time() - start) * 1000
                self._record_latency("openrouter", elapsed)
                if r.status_code == 429:
                    log.warning(f"OpenRouter rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"OpenRouter error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                raw_code = result["choices"][0]["message"]["content"]
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"OpenRouter call failed for {model}: {e}")
                continue
        log.error("All OpenRouter models exhausted")
        return None, None

    def _call_fireworks(self, task_type, prompt, entry):
        """Call Fireworks AI API with model rotation."""
        log.info(f"Solving {task_type} task with Fireworks AI...")
        system_msg = self._build_system_msg(task_type, entry)
        headers = {
            "Authorization": f"Bearer {self.fireworks_key}",
            "Content-Type": "application/json"
        }
        # Smart model override
        smart = self._pick_smart_model(task_type)
        models_to_try = []
        if smart and "accounts/" in smart:
            models_to_try.append(smart)
        models_to_try.extend([MODEL_FALLBACK, MODEL_FIREWORKS_BACKUP])
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            }
            try:
                start = time.time()
                r = requests.post(f"{FIREWORKS_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=60)
                elapsed = (time.time() - start) * 1000
                self._record_latency("fireworks", elapsed)
                if r.status_code == 429:
                    log.warning(f"Fireworks rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"Fireworks error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                if not result.get("choices"):
                    log.error(f"Fireworks empty response: {result}")
                    continue
                message = result["choices"][0].get("message", {})
                raw_code = message.get("content", "")
                if not raw_code:
                    log.error("Fireworks returned empty content")
                    continue
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"Fireworks call failed for {model}: {e}")
                continue
        log.error("All Fireworks models exhausted")
        return None, None

    def _build_system_msg(self, task_type, entry):
        """Build system message based on task type."""
        if entry == "analyze":
            return (
                "You analyze code and security. Write ONLY a Python function called `analyze()` that returns a string with the analysis result. "
                "No explanations. No markdown. Return ONLY the code."
            )
        elif task_type in ["algorithm", "mathematics", "data_structures"]:
            return (
                "You solve competitive programming and math problems. "
                "Write ONLY a Python function called `solve()` that reads input and prints the answer. "
                "No explanations. No markdown. No main block. The function will be called with input as argument. "
                "Return ONLY the code."
            )
        elif task_type == "code_optimization":
            return (
                "You optimize code. Write ONLY a Python function called `solve()` that returns the optimized solution. "
                "No explanations. No markdown. Return ONLY the code."
            )
        elif task_type == "pattern_recognition":
            return (
                "You solve pattern recognition problems. Write ONLY a Python function called `solve()` that returns the answer. "
                "No explanations. No markdown. Return ONLY the code."
            )
        else:
            return (
                "You are a coding assistant. Write ONLY a Python function called `solve()` that solves the given task. "
                "No explanations. No markdown. Return ONLY the code."
            )

    def _extract_code(self, raw_code):
        """Extract code from markdown or raw text. Handles None."""
        if not raw_code:
            return ""
        # Remove ```python and ``` markers
        code_match = re.search(r'```(?:python)?\n(.*?)\n```', raw_code, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        # Also try without newline
        code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', raw_code, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return raw_code.strip()

    def submit_solution(self, task_id, code, actual_model=None):
        token = self.authenticate()
        payload = {
            "taskId": task_id,
            "miner": self.account.address,
            "code": code,
            "model": actual_model or self.last_model_used or MODEL_PRIMARY,
            "signature": "standalone-miner"
        }
        r = self._api("POST", "/v1/research/submit", json=payload,
                       headers={"Authorization": f"Bearer {token}"}, retries=1)
        if r.status_code != 200:
            log.error(f"Submit failed: {r.status_code} {r.text[:200]}")
            return None
        result = r.json()
        log.info(f"Submitted! Status: {result.get('status', 'unknown')}, Reward: {result.get('reward', 'N/A')}")
        return result

    def _poll_submission(self, sub_id, max_wait=600):
        start = time.time()
        while time.time() - start < max_wait:
            r = self._api("GET", f"/v1/research/submission-status/{sub_id}")
            if r.status_code == 404:
                time.sleep(5)
                continue
            if r.status_code != 200:
                time.sleep(5)
                continue
            data = r.json()
            status = data.get("status")
            log.info(f"Submission status: {status}")
            if status in ["completed", "failed", "rejected"]:
                return data
            time.sleep(5)
        raise Exception("Submission polling timed out")

    def mine_once(self):
        log.info("═" * 50)
        log.info("Starting research mining round...")
        task_data = self.fetch_task()
        task = task_data.get("task", task_data)
        task_id = task.get("id") or task_data.get("taskId")
        task_type = task.get("type", "unknown")
        self.last_task_type = task_type
        self._record_task_type(task_type)
        log.info(f"Task: {task_id} | Type: {task_type}")
        
        # ── Check cache first ──
        cached = self._get_cached_solution(task)
        if cached:
            solution = cached
            actual_model = "cached"
            log.info(f"💾 Using cached solution ({len(solution)} chars)")
        else:
            solution, actual_model = self.solve_with_llm(task)
        
        if not solution:
            log.error("No solution generated, skipping")
            self.consec_global_fails += 1
            self._persist()
            return None
        log.info(f"Solution length: {len(solution)} chars | Model: {actual_model or 'unknown'}")
        
        # ── Pre-submission validation ──
        if self._validate_solution(solution):
            log.info("✅ Solution passed validation")
        else:
            log.warning("⚠️ Solution validation failed — will submit anyway but flagging")
        
        # ── Solution quality scoring ──
        quality = self._score_solution(solution, task_type)
        if quality < 40:
            log.warning(f"⚠️ Low quality score ({quality}), regenerating...")
            solution2, actual_model2 = self.solve_with_llm(task)
            if solution2:
                quality2 = self._score_solution(solution2, task_type)
                if quality2 > quality:
                    solution = solution2
                    actual_model = actual_model2
                    log.info(f"🔄 Regenerated with better quality: {quality2}")
        
        # ── Batch or immediate submit ──
        if self.BATCH_SIZE > 1:
            result = self._add_to_batch(task_id, solution, actual_model)
            # Batch returns results only when full
            if result is not None:
                for r in result:
                    if r:
                        self.consec_global_fails = 0
                        reward = r.get("reward", 0)
                        self._record_hourly(reward)
                        if actual_model != "cached":
                            self._cache_solution(task, solution)
                    else:
                        self.consec_global_fails += 1
                self._persist()
                return result[0] if result else None
            return None  # queued, not submitted yet
        else:
            # Immediate submission (default)
            try:
                result = self.submit_solution(task_id, solution, actual_model)
                if result:
                    self.consec_global_fails = 0
                    reward = result.get("reward", 0)
                    self._record_hourly(reward)
                    if actual_model != "cached":
                        self._cache_solution(task, solution)
                        log.info(f"💾 Cached solution for future use")
                else:
                    self.consec_global_fails += 1
                self._persist()
                return result
            except Exception as e:
                log.error(f"Submit failed: {e}")
                self.consec_global_fails += 1
                self._persist()
                return None

    def _validate_solution(self, solution):
        """Quick validation: try to compile Python code, or check JSON validity."""
        if not solution:
            return False
        try:
            # Check if it's valid Python
            compile(solution, '<solution>', 'exec')
            return True
        except SyntaxError:
            # Not Python, might be JSON or text
            try:
                json.loads(solution)
                return True
            except (json.JSONDecodeError, ValueError):
                # Plain text is fine too
                return len(solution) > 50
        except Exception:
            return len(solution) > 50

    def run(self, rounds=10, delay=3):
        log.info(f"Starting standalone RESEARCH miner — {rounds} rounds, {delay}s delay")
        log.info(f"Wallet: {self.account.address}")
        provider = "OpenRouter" if self.openrouter_key else "Fireworks" if self.fireworks_key else "NONE"
        log.info(f"Provider: Fireworks PRIMARY / OpenRouter fallback | Primary model: {MODEL_FALLBACK} | Fallback: {MODEL_PRIMARY}")

        # Seed initial balance for kill-switch monitoring
        if self.initial_balance is None:
            try:
                self.initial_balance = self._fetch_balance()
                log.info(f"Initial balance snapshot: {self.initial_balance}")
            except Exception as e:
                log.warning(f"Could not snapshot balance: {e}")

        i = 0
        restart_count = 0
        max_restarts = 5
        while True:
            if rounds != float('inf') and i >= rounds:
                break
            # ── Kill switch check ──
            if self._check_kill_switch():
                log.error("Miner stopped by kill switch. Check logs above.")
                self._persist()
                break

            # ── Round execution ──
            reward = 0
            status = "failed"
            try:
                result = self.mine_once()
                if result:
                    reward = result.get("reward", 0)
                    status = result.get("status", "unknown")
                    self.total_earned += reward
                    self.round_count += 1
                    # Track model performance
                    self._update_model_tracker(self.last_task_type, self.last_model_used, reward)
                else:
                    self.round_count += 1
            except Exception as e:
                log.error(f"Round error: {e}")
                self.round_count += 1
                restart_count += 1
                if restart_count > max_restarts:
                    log.error(f"Too many consecutive errors ({restart_count}). Stopping.")
                    break
                log.info(f"🔄 Auto-restart {restart_count}/{max_restarts} in 5s...")
                time.sleep(5)
                continue
            else:
                restart_count = 0  # Reset on success

            # ── Round summary ──
            avg = self.total_earned / max(1, self.round_count)
            provider_used = self._select_provider(self.last_task_type or "code_optimization")
            log.info(
                f"Round {self.round_count}/{rounds} | Provider: {provider_used} | "
                f"Reward: {reward} | Total: {self.total_earned} | Avg: {avg:.2f} | Status: {status}"
            )
            
            # ── Hourly stats every 10 rounds ──
            if self.round_count % 10 == 0 and self.hourly_stats:
                best_hours = self._get_best_hours()
                if best_hours:
                    top = best_hours[:3]
                    log.info(f"📈 Best hours: {', '.join(f'{h}h={a:.1f}' for h,a in top)}")
            
            self._persist()

            # ── Auto-claim check ──
            if self.total_earned >= 50000:
                log.info("🎉 BALANCE THRESHOLD HIT — 50,000 LITCOIN! Attempting auto-claim...")
                try:
                    self._auto_claim()
                except Exception as e:
                    log.warning(f"Auto-claim failed: {e}")
            
            # ── Delay with early-exit on kill switch ──
            if rounds == float('inf') or i < rounds - 1:
                log.info(f"Waiting {delay}s before next round...")
                for _ in range(delay):
                    if self._check_kill_switch():
                        log.error("Kill switch triggered during delay. Stopping.")
                        self._persist()
                        return self.total_earned
                    time.sleep(1)

            i += 1

        log.info("═" * 50)
        log.info(f"Mining complete. Total earned: {self.total_earned} LITCOIN across {self.round_count} rounds")
        self._persist()
        return self.total_earned


if __name__ == "__main__":
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    fireworks_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not openrouter_key and not fireworks_key:
        log.error("Set OPENROUTER_API_KEY or FIREWORKS_API_KEY environment variable")
        sys.exit(1)
    try:
        account = get_wallet()
    except Exception as e:
        log.error(f"Wallet load failed: {e}")
        sys.exit(1)
    miner = LitcoiinResearchMiner(account, openrouter_key, fireworks_key)
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        result = miner.mine_once()
        print(json.dumps(result, indent=2) if result else "Failed")
    else:
        rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 50
        delay = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        if rounds <= 0:
            rounds = float('inf')
        miner.run(rounds=rounds, delay=delay)

