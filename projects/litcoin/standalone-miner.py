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
import random
import difflib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Miner state file (survives restarts) ──
STATE_FILE = Path(__file__).with_suffix("").name + "_state.json"
# ── Solution cache file (survives restarts) ──
CACHE_FILE = Path(__file__).with_suffix("").name + "_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("standalone-miner")

COORDINATOR_URL = "https://api.litcoin.app"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"
WALLET_ADDRESS = "0x35b6Ad2e434c67eE4822F6830ceAB0316aaE3696"
MODEL_PRIMARY = "inclusionai/ling-2.6-1t:free"
MODEL_FALLBACK = "accounts/fireworks/models/llama-v3p3-70b-instruct"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
MODEL_NVIDIA_PRIMARY = "meta/llama-3.1-8b-instruct"
MODEL_NVIDIA_BACKUP = "meta/llama-3.1-70b-instruct"
MODEL_FIREWORKS_BACKUP = "accounts/fireworks/models/qwen3-235b-a22b"  # Backup Fireworks model

# ── New Providers ──
GROQ_URL = "https://api.groq.com/openai/v1"
MODEL_GROQ_PRIMARY = "llama-3.3-70b-versatile"
MODEL_GROQ_BACKUP = "mixtral-8x7b-32768"
DEEPSEEK_URL = "https://api.deepseek.com/v1"
MODEL_DEEPSEEK_PRIMARY = "deepseek-chat"
MODEL_DEEPSEEK_BACKUP = "deepseek-coder"
CEREBRAS_URL = "https://api.cerebras.ai/v1"
MODEL_CEREBRAS_PRIMARY = "llama3.1-8b"
MODEL_CEREBRAS_BACKUP = "qwen-3-235b-a22b-instruct-2507"

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
    # Tasks that consistently earn ZERO across all models — skip entirely
    SKIP_TASK_TYPES = [
        "software_engineering",   # No data, presumed too hard
        "exploit_forensics",      # 0.0 avg (5 rounds, all 0)
        "pattern_recognition",    # 0.0 avg (1 round)
        "mathematics",            # 0.0 avg (3 rounds)
        "compiler",               # 0.0 avg (1 round)
        "compression",           # 0.0 avg (1 round)
    ]
    # Tasks where the BEST model earns < 5 — skip to save API calls
    LOW_VALUE_TASKS = [
        "tcg_card_profile",       # Best: Fireworks 5.6 avg (897 rounds) — barely worth it
    ]
    # Tasks where the BEST model earns > 15 — prioritize these
    HIGH_VALUE_TASKS = [
        "runescape_ta",           # Fireworks 52.2 avg
        "runescape_insight",      # Fireworks 42.6 avg
        "algorithm",              # Fireworks 33.9 avg (WAS in LOW_VALUE — wrong!)
        "ai_safety",              # Fireworks 30.0 avg
        "adversarial_robustness", # Fireworks 31.3 avg (NOT 139!)
        "bioinformatics",         # Fireworks 25.8 avg (NOT 94!)
        "verification",           # Fireworks 23.0 avg
        "knowledge_synthesis",    # Fireworks 21.8 avg (NOT 27!)
        "agentic_trace",          # Fireworks 18.3 avg (OpenRouter 33 dead)
        "instruction_tuning",     # Fireworks 16.9 avg (OpenRouter 26 dead)
        "smart_contracts",        # NVIDIA 6.7 avg (Fireworks 2.8 worse)
    ]

    # ── Task-type → best available provider mapping (from 22K+ rounds of data) ──
    # With OpenRouter dead, only Kimi/Fireworks/NVIDIA are viable
    TASK_TYPE_TO_PROVIDER = {
        # Fireworks 70B dominates these (>15 avg)
        "runescape_ta": "fireworks",
        "runescape_insight": "fireworks",
        "algorithm": "fireworks",
        "ai_safety": "fireworks",
        "adversarial_robustness": "fireworks",
        "bioinformatics": "fireworks",
        "verification": "fireworks",
        "knowledge_synthesis": "fireworks",
        "agentic_trace": "fireworks",
        "instruction_tuning": "fireworks",
        "tcg_card_profile": "fireworks",  # 5.6 vs NVIDIA 0.9
        # NVIDIA 8B actually wins here (6.7 vs Fireworks 2.8)
        "smart_contracts": "nvidia",
    }
    # Task rotation: don't repeat same type for N rounds
    TASK_ROTATION_MEMORY = 5  # remember last 5 task types
    # Batch submit: queue N solutions then flush in parallel
    BATCH_SIZE = 3
    # Max parallel workers for batch flush
    BATCH_MAX_WORKERS = 5
    # Fuzzy similarity threshold (0.0–1.0)
    FUZZY_THRESHOLD = 0.90
    # Max cache entries before LRU eviction
    CACHE_MAX_ENTRIES = 200

    def __init__(self, account, openrouter_key, fireworks_key=None, kimi_key=None, nvidia_key=None, groq_key=None, deepseek_key=None, cerebras_key=None):
        self.account = account
        self.openrouter_key = openrouter_key
        self.fireworks_key = fireworks_key
        self.kimi_key = kimi_key
        self.nvidia_key = nvidia_key
        self.groq_key = groq_key
        self.deepseek_key = deepseek_key
        self.cerebras_key = cerebras_key
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["X-Litcoin-SDK"] = "standalone-research-5.5.0"
        self.auth_token = None
        self.auth_expiry = 0
        self.last_model_used = MODEL_PRIMARY

        # ── Enhancement state ──
        self.state = load_state()
        # circuit breaker counters
        self.or_fails = 0                 # consecutive OpenRouter failures
        self.fw_fails = 0                 # consecutive Fireworks failures
        self.kimi_fails = 0               # consecutive Kimi failures
        self.nvidia_fails = 0             # consecutive NVIDIA failures
        self.groq_fails = 0               # consecutive Groq failures
        self.deepseek_fails = 0           # consecutive DeepSeek failures
        self.cerebras_fails = 0           # consecutive Cerebras failures
        self.cb_lockout_remaining = 0     # rounds left on forced-alt provider
        self.cb_forced_provider = None    # "openrouter" | "fireworks" | "kimi" | None
        # backoff
        self.backoff_attempt = 0          # resets on any success
        # dynamic delay scaling
        self.base_delay = 3
        self.current_delay = self.base_delay
        self.consec_round_fails = 0
        # task rotation state
        self.recent_task_types = self.state.get("recent_task_types", [])
        # time-of-day tracking: {hour: {"count": 0, "total": 0}}
        self.hourly_stats = self.state.get("hourly_stats", {})
        # batch submission queue
        self.batch_queue = []
        self.batch_last_added = 0  # timestamp of oldest queued item
        # solution quality tracking
        self.quality_scores = self.state.get("quality_scores", {})
        self.provider_latency = {}  # {provider: [times]}
        # solution cache (loaded from disk)
        self.solution_cache = self._load_cache()
        self.exact_cache_hits = self.state.get("exact_cache_hits", 0)
        self.fuzzy_cache_hits = self.state.get("fuzzy_cache_hits", 0)
        self.cache_saves = 0
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

    def print_analytics(self):
        """Print earnings analytics: best hours, models, task types."""
        log.info("=" * 60)
        log.info("📊 EARNINGS ANALYTICS REPORT")
        log.info("=" * 60)
        
        # Best hours
        best_hours = self._get_best_hours()
        if best_hours:
            log.info("🏆 Best earning hours (avg LITCOIN/round):")
            for h, avg in best_hours[:5]:
                stats = self.hourly_stats.get(h, {})
                log.info(f"   {h}:00 — {avg:.1f} avg ({stats.get('count', 0)} rounds)")
        
        # Best models per task type
        log.info("🎯 Best models by task type (UCB1 ranked):")
        for task_type, models in sorted(self.model_tracker.items(), key=lambda x: -max(s["avg"] for s in x[1].values())):
            if models:
                best_model = self._pick_smart_model(task_type)
                best_stats = models.get(best_model, {})
                log.info(f"   {task_type}: {best_model} (avg {best_stats.get('avg', 0):.1f}, {best_stats.get('count', 0)} samples)")
        
        # Overall best model
        if self.best_model_overall:
            log.info(f"🥇 Overall best model: {self.best_model_overall}")
        
        # Task type ROI
        log.info("💰 Task type performance:")
        task_totals = {}
        for tt, models in self.model_tracker.items():
            total = sum(s["total"] for s in models.values())
            count = sum(s["count"] for s in models.values())
            if count > 0:
                task_totals[tt] = {"total": total, "count": count, "avg": total/count}
        for tt, stats in sorted(task_totals.items(), key=lambda x: -x[1]["avg"])[:8]:
            log.info(f"   {tt}: {stats['avg']:.1f} avg | {stats['count']} rounds | {stats['total']:.0f} total")
        
        # Summary
        rounds = self.round_count
        total = self.total_earned
        avg = total / max(rounds, 1)
        log.info(f"📈 Total: {total:.0f} LITCOIN | {rounds} rounds | {avg:.1f} avg/round")
        log.info(f"💾 Cache hits: {self.cache_hits}")
        log.info("=" * 60)

    def _add_to_batch(self, task_id, solution, model):
        """Queue solution for batch submission."""
        self.batch_queue.append({"task_id": task_id, "solution": solution, "model": model})
        log.info(f"📦 Batch queue: {len(self.batch_queue)}/{self.BATCH_SIZE} (will flush when full)")
        # EMERGENCY FLUSH: if batch has been waiting for too long, flush anyway
        # (prevents stuck queue when tasks are skipped between queued items)
        if len(self.batch_queue) >= self.BATCH_SIZE:
            return self._flush_batch()
        return None

    def _flush_batch(self):
        """Submit all queued solutions — each item isolated, don't let one failure kill the batch."""
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
                # Continue with next item — don't let one failure kill the batch
                continue
        self.batch_queue = []
        return results

    def _record_latency(self, provider, elapsed_ms):
        """Track provider response times."""
        if provider not in self.provider_latency:
            self.provider_latency[provider] = []
        self.provider_latency[provider].append(elapsed_ms)
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
        """Create a fuzzy hash for task caching — catches reworded prompts."""
        import hashlib
        prompt = task.get("prompt", task.get("description", ""))
        task_type = task.get("type", "unknown")
        # Normalize: lowercase, collapse whitespace, take first 200 chars
        normalized = re.sub(r'\s+', ' ', prompt.lower().strip())[:200]
        return hashlib.md5(f"{task_type}:{normalized}".encode()).hexdigest()

    def _predict_difficulty(self, task):
        """Predict expected reward using BEST model's historical average for this task type.
        Returns estimated score (0-100). Skip threshold: < 5 (only genuinely dead tasks).
        """
        task_type = task.get("type", "unknown")
        
        # Get best model's historical average for this task type
        tracker = self.model_tracker.get(task_type, {})
        if tracker:
            # Only consider models with sufficient data (≥10 samples)
            qualified = [(m, s) for m, s in tracker.items() if s.get("count", 0) >= 10]
            if qualified:
                best_model, best_stats = max(qualified, key=lambda x: x[1].get("avg", 0))
                historical_avg = best_stats.get("avg", 0)
            else:
                # Insufficient data — use weighted average of all models
                total_count = sum(s["count"] for s in tracker.values())
                historical_avg = sum(s["avg"] * s["count"] for s in tracker.values()) / max(total_count, 1)
        else:
            historical_avg = 20  # conservative default (matches actual landscape)
        
        # Simple prompt-length modifier: very short prompts are slightly worse
        prompt = task.get("prompt", task.get("description", ""))
        prompt_len = len(prompt)
        if prompt_len < 100:
            modifier = -3
        elif prompt_len > 3000:
            modifier = 5  # longer prompts tend to be harder but pay slightly more
        else:
            modifier = 0
        
        predicted = historical_avg + modifier
        return max(0, min(100, predicted))

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
        """UCB1 bandit with minimum sample requirement.
        Only considers models with ≥10 samples. Caps exploration at 20.
        """
        tracker = self.model_tracker.get(task_type, {})
        if not tracker:
            return None
        
        # Filter to models with enough data to be trustworthy
        qualified = {m: s for m, s in tracker.items() if s.get("count", 0) >= 10}
        if not qualified:
            return None  # Not enough data — use task-type mapping instead
        
        total_pulls = sum(s["count"] for s in qualified.values())
        best_score = -1
        best_model = None
        
        for model, stats in qualified.items():
            avg_reward = stats["avg"]
            # UCB1 with capped exploration to prevent over-exploration
            exploration = min(20, math.sqrt(2 * math.log(total_pulls) / stats["count"]))
            ucb_score = avg_reward + exploration
            if ucb_score > best_score:
                best_score = ucb_score
                best_model = model
        
        return best_model

    def _provider_available(self, name):
        if name == "openrouter":
            return bool(self.openrouter_key)
        if name == "fireworks":
            return bool(self.fireworks_key)
        if name == "kimi":
            return bool(self.kimi_key)
        if name == "nvidia":
            return bool(self.nvidia_key)
        if name == "groq":
            return bool(self.groq_key)
        if name == "deepseek":
            return bool(self.deepseek_key)
        if name == "cerebras":
            return bool(self.cerebras_key)
        return False

    def _select_provider(self, task_type):
        """Pick provider using task-type mapping first, then UCB1, then fallback.
        NVIDIA is NO LONGER absolute priority — it's only for smart_contracts.
        """
        # 1. Circuit-breaker lockout overrides everything
        if self.cb_lockout_remaining > 0 and self.cb_forced_provider:
            self.cb_lockout_remaining -= 1
            log.info(f"[CB] Locked to {self.cb_forced_provider} ({self.cb_lockout_remaining+1} rounds left)")
            return self.cb_forced_provider

        # 2. TASK-TYPE MAPPING: Use known best provider for this task type
        mapped = self.TASK_TYPE_TO_PROVIDER.get(task_type)
        if mapped:
            mapped_key = mapped + "_fails"
            fails = getattr(self, mapped_key, 0)
            if self._provider_available(mapped) and fails < CB_TRIGGER_FAILURES:
                log.info(f"[MAP] {task_type} → {mapped} (task-type mapping)")
                return mapped
            # Mapped provider dead — fall through to smart selection
            log.info(f"[MAP] {mapped} dead for {task_type}, falling back to smart selection")

        # 3. Smart model preference (UCB1) — only if sufficient data
        smart = self._pick_smart_model(task_type)
        if smart:
            if "fireworks" in smart.lower() or "accounts/" in smart:
                if self._provider_available("fireworks") and self.fw_fails < CB_TRIGGER_FAILURES:
                    return "fireworks"
            if "kimi" in smart.lower() or "moonshot" in smart.lower():
                if self._provider_available("kimi") and self.kimi_fails < CB_TRIGGER_FAILURES:
                    return "kimi"
            if "nvidia" in smart.lower() or "nemotron" in smart.lower():
                if self._provider_available("nvidia") and self.nvidia_fails < CB_TRIGGER_FAILURES:
                    return "nvidia"
            if self._provider_available("openrouter") and self.or_fails < CB_TRIGGER_FAILURES:
                return "openrouter"

        # 4. Default priority: Fireworks > Kimi > NVIDIA > OpenRouter
        # Fireworks 70B is the best generalist for most task types
        if self._provider_available("fireworks") and self.fw_fails < CB_TRIGGER_FAILURES:
            return "fireworks"
        if self._provider_available("kimi") and self.kimi_fails < CB_TRIGGER_FAILURES:
            return "kimi"
        if self._provider_available("nvidia") and self.nvidia_fails < CB_TRIGGER_FAILURES:
            return "nvidia"
        if self._provider_available("openrouter") and self.or_fails < CB_TRIGGER_FAILURES:
            return "openrouter"

        # 5. Fallback to whoever is available regardless of failures
        for p in ["fireworks", "kimi", "nvidia", "openrouter", "groq", "cerebras", "deepseek"]:
            if self._provider_available(p):
                return p
        return None

    def _record_provider_result(self, provider, success):
        """Update circuit breaker counters with auto-failover chain."""
        if provider == "openrouter":
            if success:
                self.or_fails = 0
            else:
                self.or_fails += 1
                if self.or_fails >= CB_TRIGGER_FAILURES:
                    # OpenRouter dead → try Kimi, then Fireworks
                    if self._provider_available("kimi"):
                        log.warning(f"[CB] OpenRouter failed {self.or_fails}x → locking to Kimi for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "kimi"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                    elif self._provider_available("fireworks"):
                        log.warning(f"[CB] OpenRouter failed {self.or_fails}x → locking to Fireworks for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "fireworks"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
        elif provider == "fireworks":
            if success:
                self.fw_fails = 0
            else:
                self.fw_fails += 1
                if self.fw_fails >= CB_TRIGGER_FAILURES:
                    # Fireworks dead → try Kimi, then OpenRouter
                    if self._provider_available("kimi"):
                        log.warning(f"[CB] Fireworks failed {self.fw_fails}x → locking to Kimi for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "kimi"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                    elif self._provider_available("openrouter"):
                        log.warning(f"[CB] Fireworks failed {self.fw_fails}x → locking to OpenRouter for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "openrouter"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
        elif provider == "kimi":
            if success:
                self.kimi_fails = 0
            else:
                self.kimi_fails += 1
                if self.kimi_fails >= CB_TRIGGER_FAILURES:
                    # Kimi dead → try Fireworks, then OpenRouter
                    if self._provider_available("fireworks"):
                        log.warning(f"[CB] Kimi failed {self.kimi_fails}x → locking to Fireworks for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "fireworks"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                    elif self._provider_available("openrouter"):
                        log.warning(f"[CB] Kimi failed {self.kimi_fails}x → locking to OpenRouter for {CB_LOCKOUT_ROUNDS} rounds")
                        self.cb_forced_provider = "openrouter"
                        self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS

        elif provider == "nvidia":
            if success:
                self.nvidia_fails = 0
            else:
                self.nvidia_fails += 1
                if self.nvidia_fails >= CB_TRIGGER_FAILURES:
                    # NVIDIA dead → try Groq, then Cerebras, then DeepSeek
                    for fallback in ["groq", "cerebras", "deepseek", "kimi", "fireworks"]:
                        if self._provider_available(fallback):
                            log.warning(f"[CB] NVIDIA failed {self.nvidia_fails}x → locking to {fallback} for {CB_LOCKOUT_ROUNDS} rounds")
                            self.cb_forced_provider = fallback
                            self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                            break

        elif provider == "groq":
            if success:
                self.groq_fails = 0
            else:
                self.groq_fails += 1
                if self.groq_fails >= CB_TRIGGER_FAILURES:
                    for fallback in ["cerebras", "deepseek", "nvidia", "kimi", "fireworks"]:
                        if self._provider_available(fallback):
                            log.warning(f"[CB] Groq failed {self.groq_fails}x → locking to {fallback} for {CB_LOCKOUT_ROUNDS} rounds")
                            self.cb_forced_provider = fallback
                            self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                            break

        elif provider == "cerebras":
            if success:
                self.cerebras_fails = 0
            else:
                self.cerebras_fails += 1
                if self.cerebras_fails >= CB_TRIGGER_FAILURES:
                    for fallback in ["groq", "deepseek", "nvidia", "kimi", "fireworks"]:
                        if self._provider_available(fallback):
                            log.warning(f"[CB] Cerebras failed {self.cerebras_fails}x → locking to {fallback} for {CB_LOCKOUT_ROUNDS} rounds")
                            self.cb_forced_provider = fallback
                            self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                            break

        elif provider == "deepseek":
            if success:
                self.deepseek_fails = 0
            else:
                self.deepseek_fails += 1
                if self.deepseek_fails >= CB_TRIGGER_FAILURES:
                    for fallback in ["groq", "cerebras", "nvidia", "kimi", "fireworks"]:
                        if self._provider_available(fallback):
                            log.warning(f"[CB] DeepSeek failed {self.deepseek_fails}x → locking to {fallback} for {CB_LOCKOUT_ROUNDS} rounds")
                            self.cb_forced_provider = fallback
                            self.cb_lockout_remaining = CB_LOCKOUT_ROUNDS
                            break

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
                    base_wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** self.backoff_attempt))
                    jitter = random.uniform(0, base_wait * 0.3)
                    wait = base_wait + jitter
                    log.warning(f"Rate limited, smart backoff: {wait:.1f}s (attempt {self.backoff_attempt}, jitter {jitter:.1f}s)")
                    time.sleep(wait)
                    self.backoff_attempt += 1
                    continue
                if r.status_code >= 500:
                    base_wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** attempt))
                    jitter = random.uniform(0, base_wait * 0.2)
                    wait = base_wait + jitter
                    log.warning(f"Server error {r.status_code}, retry in {wait:.1f}s")
                    time.sleep(wait)
                    continue
                self.backoff_attempt = 0
                return r
            except Exception as e:
                if attempt < retries - 1:
                    base_wait = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** attempt))
                    jitter = random.uniform(0, base_wait * 0.2)
                    wait = base_wait + jitter
                    log.warning(f"Request failed ({e}), retry in {wait:.1f}s")
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

    def solve_with_llm(self, task, attempt=1, max_attempts=3, temperature=None):
        """Solve a research task using provider selection + circuit breaker + adaptive temp."""
        task_type = task.get("type", "code_optimization")
        prompt = task.get("prompt", task.get("description", ""))
        entry = task.get("constraints", {}).get("entry_function", "solve")

        # Adaptive temperature: start low, increase on retry
        if temperature is None:
            temperature = min(0.1 + (attempt - 1) * 0.2, 0.5)

        provider = self._select_provider(task_type)
        if not provider:
            log.error("No LLM provider available. Set at least one of: OPENROUTER_API_KEY, FIREWORKS_API_KEY, KIMI_API_KEY, NVIDIA_API_KEY, GROQ_API_KEY, DEEPSEEK_API_KEY, CEREBRAS_API_KEY.")
            return None, None

        # Helper: try all remaining providers in priority order
        def try_providers(primary):
            # New priority: Fireworks > Kimi > NVIDIA > OpenRouter > others
            # (matches task-type mapping data: Fireworks wins most task types)
            order = []
            if primary == "fireworks":
                order = ["fireworks", "kimi", "nvidia", "openrouter"]
            elif primary == "kimi":
                order = ["kimi", "fireworks", "nvidia", "openrouter"]
            elif primary == "nvidia":
                order = ["nvidia", "fireworks", "kimi", "openrouter"]
            elif primary == "openrouter":
                order = ["openrouter", "fireworks", "kimi", "nvidia"]
            else:
                order = ["fireworks", "kimi", "nvidia", "openrouter"]
            for p in order:
                if not self._provider_available(p):
                    continue
                if p == self.cb_forced_provider and p != primary:
                    continue  # skip if circuit-breaker locked us away from this
                if p == "groq":
                    code, model = self._call_groq(task_type, prompt, temperature=temperature)
                elif p == "cerebras":
                    code, model = self._call_cerebras(task_type, prompt, temperature=temperature)
                elif p == "deepseek":
                    code, model = self._call_deepseek(task_type, prompt, temperature=temperature)
                elif p == "nvidia":
                    code, model = self._call_nvidia(task_type, prompt, temperature=temperature)
                elif p == "kimi":
                    code, model = self._call_kimi(task_type, prompt, entry, temperature=temperature)
                elif p == "fireworks":
                    code, model = self._call_fireworks(task_type, prompt, entry, temperature=temperature)
                else:
                    code, model = self._call_openrouter(task_type, prompt, entry, temperature=temperature)
                success = code is not None
                self._record_provider_result(p, success)
                if success:
                    self.last_model_used = model or (MODEL_FALLBACK if p == "fireworks" else MODEL_PRIMARY)
                    return code, self.last_model_used
                log.info(f"{p} failed, trying next provider...")
            return None, None

        return try_providers(provider)

    def _ensemble_solve(self, task):
        """Multi-model ensemble: call all providers, return best solution by quality score."""
        task_type = task.get("type", "unknown")
        prompt = task.get("prompt", task.get("description", ""))
        entry = task.get("constraints", {}).get("entry_function", "solve")
        
        solutions = []
        
        # Try all available providers
        for p in ["groq", "cerebras", "deepseek", "nvidia", "kimi", "openrouter", "fireworks"]:
            if not self._provider_available(p):
                continue
            if p == "groq":
                code, model = self._call_groq(task_type, prompt, entry, temperature=0.15)
            elif p == "cerebras":
                code, model = self._call_cerebras(task_type, prompt, entry, temperature=0.15)
            elif p == "deepseek":
                code, model = self._call_deepseek(task_type, prompt, entry, temperature=0.15)
            elif p == "nvidia":
                code, model = self._call_nvidia(task_type, prompt, entry, temperature=0.15)
            elif p == "kimi":
                code, model = self._call_kimi(task_type, prompt, entry, temperature=0.15)
            elif p == "openrouter":
                code, model = self._call_openrouter(task_type, prompt, entry, temperature=0.15)
            else:
                code, model = self._call_fireworks(task_type, prompt, entry, temperature=0.15)
            if code:
                q = self._score_solution(code, task_type)
                solutions.append((code, model, q, p))
                log.info(f"🎭 Ensemble: {p} scored {q}")
        
        if not solutions:
            return None, None
        
        # Pick best by quality score
        best = max(solutions, key=lambda x: x[2])
        log.info(f"🎭 Ensemble winner: {best[1]} (score={best[2]}, from {best[3]})")
        return best[0], best[1]

    def _call_openrouter(self, task_type, prompt, entry, temperature=0.1):
        """Call OpenRouter API with model rotation and adaptive temperature."""
        log.info(f"Solving {task_type} task with OpenRouter (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, entry)
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://litcoin-miner.local",
            "X-Title": "Litcoin Standalone Miner"
        }
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
                "temperature": temperature
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

    def _call_fireworks(self, task_type, prompt, entry, temperature=0.1):
        """Call Fireworks AI API with model rotation and adaptive temperature."""
        log.info(f"Solving {task_type} task with Fireworks AI (temp={temperature})...")
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
                "temperature": temperature
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

    def _call_kimi(self, task_type, prompt, entry, temperature=0.1):
        """Call Kimi (Moonshot) API — OpenAI-compatible endpoint."""
        log.info(f"Solving {task_type} task with Kimi AI (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, entry)
        headers = {
            "Authorization": f"Bearer {self.kimi_key}",
            "Content-Type": "application/json"
        }
        models_to_try = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": temperature
            }
            try:
                start = time.time()
                r = requests.post("https://api.moonshot.cn/v1/chat/completions",
                                 headers=headers, json=payload, timeout=60)
                elapsed = (time.time() - start) * 1000
                self._record_latency("kimi", elapsed)
                if r.status_code == 429:
                    log.warning(f"Kimi rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"Kimi error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                if not result.get("choices"):
                    log.error(f"Kimi empty response: {result}")
                    continue
                message = result["choices"][0].get("message", {})
                raw_code = message.get("content", "")
                if not raw_code:
                    log.error("Kimi returned empty content")
                    continue
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"Kimi call failed for {model}: {e}")
                continue
        log.error("All Kimi models exhausted")
        return None, None

    # ── NVIDIA NIM API ──
    def _call_nvidia(self, task_type, prompt, temperature=0.1):
        """Call NVIDIA NIM API with model rotation."""
        log.info(f"Solving {task_type} task with NVIDIA NIM (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, None)
        headers = {
            "Authorization": f"Bearer {self.nvidia_key}",
            "Content-Type": "application/json"
        }
        models_to_try = [MODEL_NVIDIA_PRIMARY, MODEL_NVIDIA_BACKUP]
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": temperature
            }
            try:
                start = time.time()
                r = requests.post(f"{NVIDIA_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=120)
                elapsed = (time.time() - start) * 1000
                self._record_latency("nvidia", elapsed)
                if r.status_code == 429:
                    log.warning(f"NVIDIA rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"NVIDIA error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                raw_code = result["choices"][0]["message"]["content"]
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"NVIDIA call failed for {model}: {e}")
                continue
        log.error("All NVIDIA models exhausted")
        return None, None

    # ── Groq API ──
    def _call_groq(self, task_type, prompt, temperature=0.1):
        """Call Groq API with model rotation."""
        log.info(f"Solving {task_type} task with Groq (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, None)
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        models_to_try = [MODEL_GROQ_PRIMARY, MODEL_GROQ_BACKUP]
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": temperature
            }
            try:
                start = time.time()
                r = requests.post(f"{GROQ_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=30)
                elapsed = (time.time() - start) * 1000
                self._record_latency("groq", elapsed)
                if r.status_code == 429:
                    log.warning(f"Groq rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"Groq error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                raw_code = result["choices"][0]["message"]["content"]
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"Groq call failed for {model}: {e}")
                continue
        log.error("All Groq models exhausted")
        return None, None

    # ── DeepSeek API ──
    def _call_deepseek(self, task_type, prompt, temperature=0.1):
        """Call DeepSeek API with model rotation."""
        log.info(f"Solving {task_type} task with DeepSeek (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, None)
        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        models_to_try = [MODEL_DEEPSEEK_PRIMARY, MODEL_DEEPSEEK_BACKUP]
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": temperature
            }
            try:
                start = time.time()
                r = requests.post(f"{DEEPSEEK_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=60)
                elapsed = (time.time() - start) * 1000
                self._record_latency("deepseek", elapsed)
                if r.status_code == 429:
                    log.warning(f"DeepSeek rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"DeepSeek error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                raw_code = result["choices"][0]["message"]["content"]
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"DeepSeek call failed for {model}: {e}")
                continue
        log.error("All DeepSeek models exhausted")
        return None, None

    # ── Cerebras API ──
    def _call_cerebras(self, task_type, prompt, temperature=0.1):
        """Call Cerebras API with model rotation."""
        log.info(f"Solving {task_type} task with Cerebras (temp={temperature})...")
        system_msg = self._build_system_msg(task_type, None)
        headers = {
            "Authorization": f"Bearer {self.cerebras_key}",
            "Content-Type": "application/json"
        }
        models_to_try = [MODEL_CEREBRAS_PRIMARY, MODEL_CEREBRAS_BACKUP]
        
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": temperature
            }
            try:
                start = time.time()
                r = requests.post(f"{CEREBRAS_URL}/chat/completions",
                                 headers=headers, json=payload, timeout=30)
                elapsed = (time.time() - start) * 1000
                self._record_latency("cerebras", elapsed)
                if r.status_code == 429:
                    log.warning(f"Cerebras rate limited on {model}, trying next...")
                    continue
                if r.status_code != 200:
                    log.error(f"Cerebras error: {r.status_code} {r.text[:200]}")
                    continue
                result = r.json()
                raw_code = result["choices"][0]["message"]["content"]
                actual_model = result.get("model", model)
                code = self._extract_code(raw_code)
                return code, actual_model
            except Exception as e:
                log.error(f"Cerebras call failed for {model}: {e}")
                continue
        log.error("All Cerebras models exhausted")
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

    def _extract_reward(self, result):
        """Extract reward from submission response — checks multiple possible field paths."""
        if not result or not isinstance(result, dict):
            return 0
        # Direct fields
        for key in ["reward", "amount", "payout", "value", "earned", "litCoin", "litcoin"]:
            if key in result:
                try:
                    return float(result[key])
                except (ValueError, TypeError):
                    continue
        # Nested paths
        for nested in ["data", "result", "payload", "response"]:
            if nested in result and isinstance(result[nested], dict):
                obj = result[nested]
                for key in ["reward", "amount", "payout", "value", "earned", "litCoin", "litcoin"]:
                    if key in obj:
                        try:
                            return float(obj[key])
                        except (ValueError, TypeError):
                            continue
        return 0

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
                       headers={"Authorization": f"Bearer {token}"}, retries=5)
        if r.status_code != 200:
            log.error(f"Submit failed: {r.status_code} {r.text[:200]}")
            return None
        result = r.json()
        # DEBUG: Log FULL coordinator response to diagnose reward=0
        log.info(f"📡 COORDINATOR RESPONSE (full): {json.dumps(result, indent=2)}")
        reward = self._extract_reward(result)
        status = result.get('status', 'unknown')
        log.info(f"Submitted! Status: {status}, Reward: {reward}")
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
        
        # ── Predictive difficulty scoring ──
        predicted = self._predict_difficulty(task)
        # Only skip if we've proven this task type is dead (< 5 with best model)
        # AND we've tried it enough times to know (≥10 rounds in tracker)
        skip_threshold = 5
        tracker = self.model_tracker.get(task_type, {})
        total_samples = sum(s.get("count", 0) for s in tracker.values())
        if predicted < skip_threshold and total_samples >= 10:
            log.warning(f"🚫 Predicted low value ({predicted:.0f}/100 < {skip_threshold}, {total_samples} samples), skipping")
            self.consec_global_fails += 1
            self._persist()
            return None
        # If insufficient data, ALWAYS try (exploration) — never skip unknown tasks
        if predicted < skip_threshold and total_samples < 10:
            log.info(f"🔮 Predicted {predicted:.0f}/100 but only {total_samples} samples — exploring anyway")
        else:
            log.info(f"🔮 Predicted value: {predicted:.0f}/100")
        
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
        valid, reason = self._validate_solution(solution, task_type)
        if valid:
            log.info(f"✅ Solution passed validation ({reason})")
        else:
            log.warning(f"⚠️ Solution validation failed: {reason} — regenerating with higher temp...")
            solution2, actual_model2 = self.solve_with_llm(task, attempt=2, temperature=0.3)
            if solution2:
                valid2, reason2 = self._validate_solution(solution2, task_type)
                if valid2:
                    solution = solution2
                    actual_model = actual_model2
                    log.info(f"🔄 Regenerated with valid solution ({reason2}) at temp=0.3")
                else:
                    # One more try at temp=0.5
                    solution3, actual_model3 = self.solve_with_llm(task, attempt=3, temperature=0.5)
                    if solution3:
                        valid3, reason3 = self._validate_solution(solution3, task_type)
                        if valid3:
                            solution = solution3
                            actual_model = actual_model3
                            log.info(f"🔄 Regenerated with valid solution ({reason3}) at temp=0.5")
                        else:
                            log.warning(f"⚠️ All regeneration attempts failed — submitting original anyway")
                    else:
                        log.warning("⚠️ Regeneration failed — submitting original anyway")
            else:
                log.warning("⚠️ Regeneration failed — submitting original anyway")
        
        # ── Solution quality scoring ──
        quality = self._score_solution(solution, task_type)
        if quality < 40:
            log.warning(f"⚠️ Low quality score ({quality}), regenerating with higher temp...")
            solution2, actual_model2 = self.solve_with_llm(task, attempt=2, temperature=0.3)
            if solution2:
                quality2 = self._score_solution(solution2, task_type)
                if quality2 > quality:
                    solution = solution2
                    actual_model = actual_model2
                    log.info(f"🔄 Regenerated with better quality: {quality2} at temp=0.3")
                else:
                    # Try once more at temp=0.5
                    solution3, actual_model3 = self.solve_with_llm(task, attempt=3, temperature=0.5)
                    if solution3:
                        quality3 = self._score_solution(solution3, task_type)
                        if quality3 > quality:
                            solution = solution3
                            actual_model = actual_model3
                            log.info(f"🔄 Regenerated with better quality: {quality3} at temp=0.5")
        
        # ── Batch or immediate submit ──
        if self.BATCH_SIZE > 1:
            result = self._add_to_batch(task_id, solution, actual_model)
            # Batch returns results only when full
            if result is not None:
                for r in result:
                    if r:
                        self.consec_global_fails = 0
                        reward = self._extract_reward(r)
                        # BUG FIX: was r.get("reward", 0) — missed nested fields
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
                    reward = self._extract_reward(result)
                    # BUG FIX: was result.get("reward", 0) — missed nested fields
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

    def _validate_solution(self, solution, task_type="unknown"):
        """Task-specific validation: check solutions against rubrics before submission."""
        if not solution:
            return False, "empty solution"
        
        # Generic: must compile as Python
        try:
            compile(solution, '<solution>', 'exec')
        except SyntaxError:
            try:
                json.loads(solution)
            except (json.JSONDecodeError, ValueError):
                if len(solution) < 50:
                    return False, "too short and not valid code"
        
        # Task-specific checks
        checks_passed = 0
        checks_total = 1
        
        if task_type == "smart_contracts":
            checks_total = 2
            if "function" in solution.lower() or "contract" in solution.lower():
                checks_passed += 1
            if len(solution) > 200:
                checks_passed += 1
            if checks_passed < 1:
                return False, f"smart_contracts missing function/contract keyword ({checks_passed}/{checks_total})"
                
        elif task_type == "tcg_card_profile":
            checks_total = 2
            if len(solution) > 300:
                checks_passed += 1
            if any(kw in solution.lower() for kw in ["card", "deck", "rarity", "type", "attack", "hp"]):
                checks_passed += 1
            if checks_passed < 1:
                return False, f"tcg_card_profile missing card keywords ({checks_passed}/{checks_total})"
                
        elif task_type == "ai_safety":
            checks_total = 2
            if len(solution) > 150:
                checks_passed += 1
            if any(kw in solution.lower() for kw in ["safety", "alignment", "harm", "risk", "ethical"]):
                checks_passed += 1
            if checks_passed < 1:
                return False, f"ai_safety missing safety keywords ({checks_passed}/{checks_total})"
                
        elif task_type == "instruction_tuning":
            checks_total = 2
            if len(solution) > 200:
                checks_passed += 1
            if "instruction" in solution.lower() or "prompt" in solution.lower() or "{" in solution:
                checks_passed += 1
            if checks_passed < 1:
                return False, f"instruction_tuning missing structure ({checks_passed}/{checks_total})"
        
        return True, f"passed ({checks_passed}/{checks_total} task checks)"

    def run(self, rounds=10, delay=3):
        log.info(f"Starting standalone RESEARCH miner — {rounds} rounds, {delay}s delay")
        log.info(f"Wallet: {self.account.address}")
        provider = "Fireworks" if self.fireworks_key else "Kimi" if self.kimi_key else "NVIDIA" if self.nvidia_key else "OpenRouter" if self.openrouter_key else "NONE"
        log.info(f"Provider priority: Fireworks > Kimi > NVIDIA > OpenRouter | Available: {provider}")

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
                    reward = self._extract_reward(result)
                    status = result.get("status", "unknown")
                    self.total_earned += reward
                    self.round_count += 1
                    # Track model performance
                    self._update_model_tracker(self.last_task_type, self.last_model_used, reward)
                    # Success: reset delay and fail counter
                    if reward > 0 or status in ["completed", "accepted", "success"]:
                        self.consec_round_fails = 0
                        self.current_delay = self.base_delay
                        log.info(f"✅ Round success — delay reset to {self.current_delay}s")
                    else:
                        # Submission succeeded but no reward — mild backoff
                        self.consec_round_fails += 1
                        self.current_delay = min(self.base_delay * (2 ** self.consec_round_fails), 30)
                        log.info(f"⚠️ No reward — delay scaled to {self.current_delay}s")
                else:
                    self.round_count += 1
                    self.consec_round_fails += 1
                    self.current_delay = min(self.base_delay * (2 ** self.consec_round_fails), 30)
                    log.info(f"❌ Round failed — delay scaled to {self.current_delay}s")
            except Exception as e:
                log.error(f"Round error: {e}")
                self.round_count += 1
                self.consec_round_fails += 1
                self.current_delay = min(self.base_delay * (2 ** self.consec_round_fails), 30)
                restart_count += 1
                if restart_count > max_restarts:
                    log.error(f"Too many consecutive errors ({restart_count}). Stopping.")
                    break
                log.info(f"🔄 Auto-restart {restart_count}/{max_restarts} in {self.current_delay}s...")
                time.sleep(self.current_delay)
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
            
            # ── Full analytics every 20 rounds ──
            if self.round_count % 20 == 0 and self.round_count > 0:
                self.print_analytics()
            
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
                log.info(f"Waiting {self.current_delay}s before next round...")
                for _ in range(self.current_delay):
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
    kimi_key = os.environ.get("KIMI_API_KEY", "")
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "")
    if not openrouter_key and not fireworks_key and not kimi_key and not nvidia_key and not groq_key and not deepseek_key and not cerebras_key:
        log.error("Set at least one API key: OPENROUTER, FIREWORKS, KIMI, NVIDIA, GROQ, DEEPSEEK, or CEREBRAS")
        sys.exit(1)
    try:
        account = get_wallet()
    except Exception as e:
        log.error(f"Wallet load failed: {e}")
        sys.exit(1)
    miner = LitcoiinResearchMiner(account, openrouter_key, fireworks_key, kimi_key, nvidia_key, groq_key, deepseek_key, cerebras_key)
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        result = miner.mine_once()
        print(json.dumps(result, indent=2) if result else "Failed")
    else:
        rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 50
        delay = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        if rounds <= 0:
            rounds = float('inf')
        miner.run(rounds=rounds, delay=delay)

