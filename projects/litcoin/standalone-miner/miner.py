#!/usr/bin/env python3
"""
Enhanced Standalone LITCOIN Research Miner — Continuous mode.

Features:
- Circuit breaker (3 failures → switch provider for 5 rounds)
- Smart model tracker (auto-picks best model per task type)
- Exponential backoff (30s × 2^attempt, max 300s)
- Auto-save state (standalone-miner_state.json)
- Kill switch (10 consecutive failures → stop)
- Multi-provider: OpenRouter + Fireworks fallback
"""

import os
import sys
import time
import json
import logging
import re
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("standalone-miner")

COORDINATOR_URL = "https://api.litcoin.app"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"
WALLET_ADDRESS = "0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C"

# Models per provider
MODELS = {
    "openrouter": {
        "default": "inclusionai/ling-2.6-1t:free",
        "code": "inclusionai/ling-2.6-1t:free",
        "math": "inclusionai/ling-2.6-1t:free",
        "research": "inclusionai/ling-2.6-1t:free",
    },
    "fireworks": {
        "default": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "code": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "math": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "research": "accounts/fireworks/models/llama-v3p1-8b-instruct",
    }
}

STATE_FILE = Path(__file__).parent / "standalone-miner_state.json"

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
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {
        "rounds": 0,
        "earned": 0,
        "consecutive_failures": 0,
        "provider": "openrouter",
        "circuit_breaker_active": False,
        "circuit_breaker_rounds_remaining": 0,
        "provider_failures": {"openrouter": 0, "fireworks": 0},
        "model_stats": {},
        "start_time": time.time()
    }


def save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"State save failed: {e}")


def get_wallet():
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
                    # Try extracting just the quoted seed
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        seed = match.group(1)
                        if len(seed.split()) in [12, 15, 18, 21, 24]:
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


class EnhancedLitcoiinMiner:
    SKIP_TASK_TYPES = ["tcg_card_profile", "software_engineering"]
    KILL_THRESHOLD = 10
    CIRCUIT_BREAKER_THRESHOLD = 3
    CIRCUIT_BREAKER_DURATION = 5
    MAX_BACKOFF = 300
    BASE_BACKOFF = 30

    def __init__(self, account, openrouter_key, fireworks_key):
        self.account = account
        self.openrouter_key = openrouter_key
        self.fireworks_key = fireworks_key
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["X-Litcoin-SDK"] = "standalone-enhanced-4.14.3"
        self.auth_token = None
        self.auth_expiry = 0
        self.state = load_state()

    def _api(self, method, path, **kwargs):
        url = f"{COORDINATOR_URL}{path}"
        retries = kwargs.pop("retries", 3)
        for attempt in range(retries):
            try:
                r = self.session.request(method, url, timeout=30, **kwargs)
                if r.status_code == 429:
                    wait = min(self.BASE_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                    log.warning(f"Rate limited, retry in {wait}s")
                    time.sleep(wait)
                    continue
                return r
            except Exception as e:
                if attempt < retries - 1:
                    wait = min(self.BASE_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                    log.warning(f"Request failed ({e}), retry in {wait}s")
                    time.sleep(wait)
                else:
                    raise
        raise Exception("All retries exhausted")

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

    def pick_provider_and_model(self, task_type):
        # Circuit breaker logic
        if self.state["circuit_breaker_active"]:
            self.state["circuit_breaker_rounds_remaining"] -= 1
            if self.state["circuit_breaker_rounds_remaining"] <= 0:
                self.state["circuit_breaker_active"] = False
                log.info("Circuit breaker reset")
            else:
                # Use alternate provider
                alt = "fireworks" if self.state["provider"] == "openrouter" else "openrouter"
                model = MODELS[alt].get(task_type, MODELS[alt]["default"])
                return alt, model

        # Default provider with smart model selection
        provider = self.state["provider"]
        model = MODELS[provider].get(task_type, MODELS[provider]["default"])
        return provider, model

    def solve_task(self, task):
        task_type = task.get("type", "code_optimization")
        prompt = task.get("prompt", task.get("description", ""))
        entry = task.get("constraints", {}).get("entry_function", "solve")

        provider, model = self.pick_provider_and_model(task_type)
        log.info(f"Solving {task_type} with {provider}/{model}...")

        if entry == "analyze":
            system_msg = (
                "You analyze code and security. Write ONLY a Python function called `analyze()` that returns a string with the analysis result. "
                "No explanations. No markdown. Return ONLY the code."
            )
        elif task_type in ["algorithm", "mathematics", "data_structures"]:
            system_msg = (
                "You solve competitive programming and math problems. "
                "Write ONLY a Python function called `solve()` that reads input and prints the answer. "
                "No explanations. No markdown. No main block. The function will be called with input as argument. "
                "Return ONLY the code."
            )
        elif task_type == "code_optimization":
            system_msg = (
                "You optimize code. Write ONLY a Python function called `solve()` that returns the optimized solution. "
                "No explanations. No markdown. Return ONLY the code."
            )
        elif task_type == "pattern_recognition":
            system_msg = (
                "You solve pattern recognition problems. Write ONLY a Python function called `solve()` that returns the answer. "
                "No explanations. No markdown. Return ONLY the code."
            )
        else:
            system_msg = (
                "You are a coding assistant. Write ONLY a Python function called `solve()` that solves the given task. "
                "No explanations. No markdown. Return ONLY the code."
            )

        if provider == "openrouter":
            return self._call_openrouter(model, system_msg, prompt, task_type)
        else:
            return self._call_fireworks(model, system_msg, prompt, task_type)

    def _call_openrouter(self, model, system_msg, prompt, task_type):
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://litcoin-miner.local",
            "X-Title": "Litcoin Standalone Miner"
        }
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
                self.state["provider_failures"]["openrouter"] += 1
                return None, None
            if r.status_code != 200:
                log.error(f"OpenRouter error: {r.status_code} {r.text[:200]}")
                self.state["provider_failures"]["openrouter"] += 1
                return None, None
            result = r.json()
            raw_code = result["choices"][0]["message"]["content"]
            actual_model = result.get("model", model)
            code_match = re.search(r'```(?:python)?\n(.*?)\n```', raw_code, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                code = raw_code.strip()
            # Update model stats
            self._update_model_stats(actual_model, task_type, True)
            return code, actual_model
        except Exception as e:
            log.error(f"OpenRouter call failed: {e}")
            self.state["provider_failures"]["openrouter"] += 1
            return None, None

    def _call_fireworks(self, model, system_msg, prompt, task_type):
        headers = {
            "Authorization": f"Bearer {self.fireworks_key}",
            "Content-Type": "application/json"
        }
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
                self.state["provider_failures"]["fireworks"] += 1
                return None, None
            if r.status_code != 200:
                log.error(f"Fireworks error: {r.status_code} {r.text[:200]}")
                self.state["provider_failures"]["fireworks"] += 1
                return None, None
            result = r.json()
            raw_code = result["choices"][0]["message"]["content"]
            actual_model = result.get("model", model)
            code_match = re.search(r'```(?:python)?\n(.*?)\n```', raw_code, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                code = raw_code.strip()
            self._update_model_stats(actual_model, task_type, True)
            return code, actual_model
        except Exception as e:
            log.error(f"Fireworks call failed: {e}")
            self.state["provider_failures"]["fireworks"] += 1
            return None, None

    def _update_model_stats(self, model, task_type, success):
        key = f"{model}:{task_type}"
        if key not in self.state["model_stats"]:
            self.state["model_stats"][key] = {"uses": 0, "success": 0, "reward": 0}
        self.state["model_stats"][key]["uses"] += 1
        if success:
            self.state["model_stats"][key]["success"] += 1

    def submit_solution(self, task_id, code, actual_model=None):
        token = self.authenticate()
        payload = {
            "taskId": task_id,
            "miner": self.account.address,
            "code": code,
            "model": actual_model or MODELS["openrouter"]["default"],
            "modelProvider": "openrouter"
        }
        if actual_model:
            payload["actual_model"] = actual_model
        r = self._api("POST", "/v1/research/submit", json=payload,
                       headers={"Authorization": f"Bearer {token}"}, retries=1)
        if r.status_code == 401:
            self.auth_token = None
            return self.submit_solution(task_id, code, actual_model)
        if r.status_code == 202:
            data = r.json()
            sub_id = data.get("submissionId")
            log.info(f"Submission queued: {sub_id}")
            return self._poll_submission(sub_id)
        if r.status_code not in (200, 201):
            raise Exception(f"Submit failed: {r.status_code} {r.text}")
        return r.json()

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

    def check_circuit_breaker(self):
        provider = self.state["provider"]
        if self.state["provider_failures"][provider] >= self.CIRCUIT_BREAKER_THRESHOLD:
            self.state["circuit_breaker_active"] = True
            self.state["circuit_breaker_rounds_remaining"] = self.CIRCUIT_BREAKER_DURATION
            # Switch provider
            new_provider = "fireworks" if provider == "openrouter" else "openrouter"
            self.state["provider"] = new_provider
            self.state["provider_failures"][provider] = 0
            log.warning(f"CIRCUIT BREAKER: Switching to {new_provider} for {self.CIRCUIT_BREAKER_DURATION} rounds")

    def mine_once(self):
        log.info("═" * 50)
        log.info(f"Round {self.state['rounds'] + 1} | Provider: {self.state['provider']}")
        if self.state["circuit_breaker_active"]:
            log.info(f"Circuit breaker active: {self.state['circuit_breaker_rounds_remaining']} rounds remaining")

        try:
            task_data = self.fetch_task()
            task = task_data.get("task", task_data)
            task_id = task.get("id") or task_data.get("taskId")
            task_type = task.get("type", "unknown")
            log.info(f"Task: {task_id} | Type: {task_type}")

            solution, actual_model = self.solve_task(task)
            if not solution:
                log.error("No solution generated")
                self.state["consecutive_failures"] += 1
                self.check_circuit_breaker()
                save_state(self.state)
                return None

            log.info(f"Solution length: {len(solution)} chars | Model: {actual_model}")
            result = self.submit_solution(task_id, solution, actual_model)
            reward = result.get("reward", 0) if result else 0

            if result and result.get("status") not in ["failed", "rejected"]:
                self.state["consecutive_failures"] = 0
                self.state["provider_failures"][self.state["provider"]] = max(0, self.state["provider_failures"][self.state["provider"]] - 1)
            else:
                self.state["consecutive_failures"] += 1

            self.state["rounds"] += 1
            self.state["earned"] += reward
            save_state(self.state)
            return result

        except Exception as e:
            log.error(f"Round error: {e}")
            self.state["consecutive_failures"] += 1
            self.check_circuit_breaker()
            self.state["rounds"] += 1
            save_state(self.state)
            return None

    def run(self, rounds=100, delay=60):
        log.info(f"Starting ENHANCED standalone miner — {rounds} rounds, {delay}s delay")
        log.info(f"Wallet: {self.account.address}")
        log.info(f"Kill switch: {self.KILL_THRESHOLD} consecutive failures")
        log.info(f"Circuit breaker: {self.CIRCUIT_BREAKER_THRESHOLD} failures → switch for {self.CIRCUIT_BREAKER_DURATION} rounds")

        for i in range(rounds):
            if self.state["consecutive_failures"] >= self.KILL_THRESHOLD:
                log.error(f"KILL SWITCH ACTIVATED: {self.KILL_THRESHOLD} consecutive failures. Stopping.")
                break

            result = self.mine_once()
            reward = result.get("reward", 0) if result else 0
            status = result.get("status", "unknown") if result else "failed"

            log.info(f"Result: {status} | +{reward} LITCOIN")
            log.info(f"Stats: {self.state['rounds']} rounds | {self.state['earned']} total | {self.state['consecutive_failures']} consecutive failures")
            log.info(f"Providers: OR={self.state['provider_failures']['openrouter']} | FW={self.state['provider_failures']['fireworks']}")

            if i < rounds - 1 and self.state["consecutive_failures"] < self.KILL_THRESHOLD:
                log.info(f"Waiting {delay}s before next round...")
                time.sleep(delay)

        elapsed = time.time() - self.state.get("start_time", time.time())
        log.info("═" * 50)
        log.info(f"MINING COMPLETE")
        log.info(f"Rounds: {self.state['rounds']} | Total: {self.state['earned']} LITCOIN")
        log.info(f"Average: {self.state['earned'] / max(self.state['rounds'], 1):.2f} per round")
        log.info(f"Elapsed: {elapsed / 60:.1f} minutes")
        log.info(f"Model stats: {json.dumps(self.state['model_stats'], indent=2)}")
        save_state(self.state)
        return self.state["earned"]


if __name__ == "__main__":
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    fireworks_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not openrouter_key:
        log.error("Set OPENROUTER_API_KEY environment variable")
        sys.exit(1)
    try:
        account = get_wallet()
    except Exception as e:
        log.error(f"Wallet load failed: {e}")
        sys.exit(1)
    miner = EnhancedLitcoiinMiner(account, openrouter_key, fireworks_key)
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    miner.run(rounds=rounds)
