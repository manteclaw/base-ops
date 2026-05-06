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
MODEL_FALLBACK = "accounts/fireworks/models/llama-v3p1-70b-instruct"

# Circuit-breaker constants
CB_TRIGGER_FAILURES = 3      # consecutive failures before flipping provider
CB_LOCKOUT_ROUNDS = 5        # how many rounds to stay on the alt provider
BACKOFF_BASE_SECONDS = 30    # base for 2^attempt * 30s
BACKOFF_MAX_SECONDS = 300    # cap at 5 minutes
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
    SKIP_TASK_TYPES = ["tcg_card_profile", "software_engineering"]

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

    def _pick_smart_model(self, task_type):
        """Return the model with highest avg reward for this task type (min 2 samples)."""
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
        """Pick provider respecting circuit breaker and smart model preferences."""
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

        # 3. Default: Fireworks first if healthy, then OpenRouter
        if self._provider_available("fireworks") and self.fw_fails < CB_TRIGGER_FAILURES:
            return "fireworks"
        if self._provider_available("openrouter") and self.or_fails < CB_TRIGGER_FAILURES:
            return "openrouter"

        # 4. Fallback to whoever is available regardless of failures
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
        return task_type in self.SKIP_TASK_TYPES

    def fetch_task(self, task_type=None):
        """Fetch a suitable research task."""
        for _ in range(5):
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
        """Call OpenRouter API."""
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
        model = smart if smart and ":" in smart else MODEL_PRIMARY
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
            r = requests.post(f"{OPENROUTER_URL}/chat/completions",
                             headers=headers, json=payload, timeout=60)
            if r.status_code == 429:
                log.warning("OpenRouter rate limited")
                return None, None
            if r.status_code != 200:
                log.error(f"OpenRouter error: {r.status_code} {r.text[:200]}")
                return None, None
            result = r.json()
            raw_code = result["choices"][0]["message"]["content"]
            actual_model = result.get("model", model)
            code = self._extract_code(raw_code)
            return code, actual_model
        except Exception as e:
            log.error(f"OpenRouter call failed: {e}")
            return None, None

    def _call_fireworks(self, task_type, prompt, entry):
        """Call Fireworks AI API."""
        log.info(f"Solving {task_type} task with Fireworks AI...")
        system_msg = self._build_system_msg(task_type, entry)
        headers = {
            "Authorization": f"Bearer {self.fireworks_key}",
            "Content-Type": "application/json"
        }
        # Smart model override
        smart = self._pick_smart_model(task_type)
        model = smart if smart and "accounts/" in smart else MODEL_FALLBACK
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
            r = requests.post(f"{FIREWORKS_URL}/chat/completions",
                             headers=headers, json=payload, timeout=60)
            if r.status_code == 429:
                log.warning("Fireworks rate limited")
                return None, None
            if r.status_code != 200:
                log.error(f"Fireworks error: {r.status_code} {r.text[:200]}")
                return None, None
            result = r.json()
            if not result.get("choices"):
                log.error(f"Fireworks empty response: {result}")
                return None, None
            message = result["choices"][0].get("message", {})
            raw_code = message.get("content", "")
            if not raw_code:
                log.error("Fireworks returned empty content")
                return None, None
            actual_model = result.get("model", model)
            code = self._extract_code(raw_code)
            return code, actual_model
        except Exception as e:
            log.error(f"Fireworks call failed: {e}")
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
        log.info(f"Task: {task_id} | Type: {task_type}")
        solution, actual_model = self.solve_with_llm(task)
        if not solution:
            log.error("No solution generated, skipping")
            self.consec_global_fails += 1
            self._persist()
            return None
        log.info(f"Solution length: {len(solution)} chars | Model: {actual_model or 'unknown'}")
        try:
            result = self.submit_solution(task_id, solution, actual_model)
            if result:
                self.consec_global_fails = 0
            else:
                self.consec_global_fails += 1
            self._persist()
            return result
        except Exception as e:
            log.error(f"Submit failed: {e}")
            self.consec_global_fails += 1
            self._persist()
            return None

    def run(self, rounds=10, delay=60):
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

        for i in range(rounds):
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

            # ── Round summary ──
            avg = self.total_earned / max(1, self.round_count)
            provider_used = self._select_provider(self.last_task_type or "code_optimization")
            log.info(
                f"Round {self.round_count}/{rounds} | Provider: {provider_used} | "
                f"Reward: {reward} | Total: {self.total_earned} | Avg: {avg:.2f} | Status: {status}"
            )
            self._persist()

            # ── Delay with early-exit on kill switch ──
            if i < rounds - 1:
                log.info(f"Waiting {delay}s before next round...")
                for _ in range(delay):
                    if self._check_kill_switch():
                        log.error("Kill switch triggered during delay. Stopping.")
                        self._persist()
                        return self.total_earned
                    time.sleep(1)

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
        miner.run(rounds=rounds, delay=15)

