#!/usr/bin/env python3
"""
Hybrid Multi-Provider Miner for Litcoiin
Routes tasks across Groq, Cerebras, Together AI, SambaNova, OpenRouter, NVIDIA NIM, Mistral

Strategy:
- Simple tasks (data_labeling, tcg, string ops) → 8B models (fast, cheap)
- Complex tasks (security, CP, reasoning) → 70B+ models (correct, slower)
- Multi-provider fallback: If primary fails, auto-try all configured providers
"""

import os
import sys
import json
import re
import time
from typing import Optional, Dict, Any, Tuple

# ─── CONFIG ──────────────────────────────────────────────────────
BANKR_KEY = os.environ.get("BANKR_API_KEY", "")
if not BANKR_KEY:
    raise ValueError("BANKR_API_KEY environment variable required")

# ── Provider API Keys ──
# These can be set via env vars or hardcoded below
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_KEY:
    raise ValueError("GROQ_API_KEY environment variable required")
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "csk-...")
TOGETHER_KEY = os.environ.get("TOGETHER_API_KEY", "")
SAMBANOVA_KEY = os.environ.get("SAMBANOVA_API_KEY", "b34dec5b-79ee-424a-80e4-715e0d6234d8")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable required")
NVIDIA_KEY = os.environ.get("NVIDIA_NIM_KEY", "")
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")

# ── Provider URLs ──
GROQ_URL = "https://api.groq.com/openai/v1"
CEREBRAS_URL = "https://api.cerebras.ai/v1"
TOGETHER_URL = "https://api.together.xyz/v1"
SAMBANOVA_URL = "https://api.sambanova.ai/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
MISTRAL_URL = "https://api.mistral.ai/v1"

# ── Model Registry ──
# Each entry: (model_id, api_key, api_url, rpm_limit)
MODELS = {
    # Groq — fastest, best code quality
    "groq-8b": ("llama-3.1-8b-instant", GROQ_KEY, GROQ_URL, 1000),
    "groq-70b": ("llama-3.3-70b-versatile", GROQ_KEY, GROQ_URL, 1000),

    # Cerebras — high throughput, 1M tokens/day free
    "cerebras-8b": ("llama3.1-8b", CEREBRAS_KEY, CEREBRAS_URL, 30),
    "cerebras-235b": ("qwen-3-235b-a22b-instruct-2507", CEREBRAS_KEY, CEREBRAS_URL, 30),

    # Together AI — free tier, good variety
    "together-8b": ("meta-llama/Llama-3.1-8B-Instruct-Turbo", TOGETHER_KEY, TOGETHER_URL, 20),
    "together-70b": ("meta-llama/Llama-3.3-70B-Instruct-Turbo", TOGETHER_KEY, TOGETHER_URL, 20),

    # SambaNova — free tier, DeepSeek R1 available
    "sambanova-70b": ("Meta-Llama-3.3-70B-Instruct", SAMBANOVA_KEY, SAMBANOVA_URL, 30),
    "sambanova-r1": ("DeepSeek-R1", SAMBANOVA_KEY, SAMBANOVA_URL, 30),

    # OpenRouter — :free suffix models, 200 req/day
    "openrouter-8b": ("meta-llama/llama-3.1-8b-instruct:free", OPENROUTER_KEY, OPENROUTER_URL, 20),
    "openrouter-70b": ("meta-llama/llama-3.3-70b-instruct:free", OPENROUTER_KEY, OPENROUTER_URL, 20),
    "openrouter-qwen": ("qwen/qwen-2.5-72b-instruct:free", OPENROUTER_KEY, OPENROUTER_URL, 20),

    # NVIDIA NIM — 40 req/min
    "nvidia-70b": ("meta/llama-3.3-70b-instruct", NVIDIA_KEY, NVIDIA_URL, 40),

    # Mistral — 1B tokens/month free
    "mistral-8b": ("mistral-small-latest", MISTRAL_KEY, MISTRAL_URL, 60),
    "mistral-70b": ("mistral-large-latest", MISTRAL_KEY, MISTRAL_URL, 60),
}

# ── Fallback Chains ──
# Order matters: tried left-to-right until one succeeds
FALLBACK_CHAINS = {
    "complex": [
        "groq-70b",
        "cerebras-235b",
        "together-70b",
        "sambanova-70b",
        "openrouter-70b",
        "openrouter-qwen",
        "nvidia-70b",
        "mistral-70b",
        "groq-8b",       # last resort: 8B on complex task
    ],
    "simple": [
        "groq-8b",
        "cerebras-8b",
        "together-8b",
        "openrouter-8b",
        "mistral-8b",
        "groq-70b",      # fallback up if all 8Bs fail
    ],
}

# ── Task Type Routing ──
# Maps Litcoiin task types → complexity class
TASK_TYPE_ROUTING = {
    # Simple → 8B viable
    "data_labeling": "simple",
    "tcg_card_profile": "simple",
    "compression": "simple",
    "sorting": "simple",
    "string": "simple",
    "regex": "simple",
    "sum": "simple",
    "multiply": "simple",
    "fibonacci": "simple",
    "factorial": "simple",
    "binary": "simple",
    "hex": "simple",
    "palindrome": "simple",
    "anagram": "simple",
    "prime": "simple",
    "gcd": "simple",
    "lcm": "simple",
    "reverse": "simple",
    "base64": "simple",
    "sudoku": "simple",
    "maze": "simple",
    "knapsack": "simple",
    "solver": "simple",
    "data_structures": "simple",

    # Complex → 70B required
    "smart_contracts": "complex",
    "security_audit": "complex",
    "exploit_forensics": "complex",
    "adversarial_robustness": "complex",
    "agentic_trace": "complex",
    "protocol_audit": "complex",
    "evm": "complex",
    "opcode": "complex",
    "reasoning": "complex",
    "math": "complex",
    "counterfactual": "complex",
    "chain_of_thought": "complex",
    "format_exploit": "complex",
    "calibration": "complex",
    "instruction_confusion": "complex",
    "code_test": "complex",

    # Unknown → safer to use complex
    "unknown": "complex",
}

# ── Heuristics ──
COMPLEX_KEYWORDS = [
    "protocol audit", "security", "evm", "opcode", "smart contract",
    "reentrancy", "access control", "deepbook", "module bundle",
    "compound", "aave", "uniswap", "sui", "anchor", "solidity"
]
SIMPLE_KEYWORDS = [
    "sort", "fibonacci", "factorial", "leap year", "sum", "multiply",
    "string", "regex", "palindrome", "anagram", "mode", "mean", "median",
    "prime", "gcd", "lcm", "reverse", "binary", "hex", "base64",
    "data_labeling", "sudoku", "maze", "knapsolver", "solver"
]

TOKEN_ESTIMATE_PER_CHAR = 0.25
MAX_8B_TOKENS = 5000
FORCE_70B_LENGTH = 4000  # chars

# ─── ROUTER ──────────────────────────────────────────────────────

def score_task_complexity(task: Dict[str, Any]) -> Tuple[int, str, str]:
    """Returns (score, complexity_class, reason)."""
    title = task.get("title", "").lower()
    desc = task.get("description", "").lower()

    # 1. Exact task-type match
    api_type = task.get("type", "").lower().replace("-", "_")
    if api_type in TASK_TYPE_ROUTING:
        route = TASK_TYPE_ROUTING[api_type]
        return (80 if route == "complex" else 10, route, f"type-rule ({api_type})")

    # 2. Title prefix patterns
    if title.startswith("cf:") or "codeforces" in title:
        return 80, "complex", "prefix CF"
    if title.startswith("sec:") or title.startswith("ef:"):
        return 80, "complex", "prefix SEC/EF"
    if title.startswith("adv:"):
        return 80, "complex", "prefix ADV"
    if title.startswith("agt:"):
        return 80, "complex", "prefix AGT"

    # 3. Length guard
    total_chars = len(title) + len(desc)
    if total_chars > FORCE_70B_LENGTH:
        return 70, "complex", f"oversized ({total_chars} chars)"

    # 4. Keyword scoring (fallback)
    est_tokens = total_chars * TOKEN_ESTIMATE_PER_CHAR
    score = min(30, int(est_tokens / 100))

    for kw in COMPLEX_KEYWORDS:
        if kw in title or kw in desc:
            score += 25
    for kw in SIMPLE_KEYWORDS:
        if kw in title or kw in desc:
            score -= 20

    score = max(0, min(100, score))

    if score >= 45 or est_tokens > MAX_8B_TOKENS:
        return score, "complex", f"heuristic ({score}pts)"
    return score, "simple", f"heuristic ({score}pts)"


# ─── PROVIDER INTERFACE ────────────────────────────────────────────

def create_agent(model_id: str, name: str, api_key: str, api_url: str):
    """Create litcoin Agent with specific provider."""
    from litcoin import Agent
    return Agent(
        bankr_key=BANKR_KEY,
        ai_key=api_key,
        ai_url=api_url,
        model=model_id,
        name=name,
    )


def get_model_config(model_key: str) -> Optional[Tuple[str, str, str, int]]:
    """Get (model_id, api_key, api_url, rpm) for a model key."""
    if model_key not in MODELS:
        return None
    model_id, api_key, api_url, rpm = MODELS[model_key]
    if not api_key:
        return None  # Unconfigured provider
    return (model_id, api_key, api_url, rpm)


def call_with_retry(agent, task_id: str, max_retries: int = 2, backoff_base: float = 2.0) -> Dict[str, Any]:
    """Call agent.research_mine() with backoff on rate limits."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return agent.research_mine(task_id=task_id)
        except Exception as e:
            err_str = str(e)
            last_error = e

            # 413 → immediate fallback
            if "413" in err_str or "Payload Too Large" in err_str:
                raise

            # 429 → exponential backoff (max 30s)
            if "429" in err_str or "Too Many Requests" in err_str:
                wait = min(backoff_base * (2 ** attempt), 30)
                print(f"[hybrid] ⚠️ 429 attempt {attempt + 1}/{max_retries}. Backoff {wait}s...")
                time.sleep(wait)
                continue

            # Auth → skip provider
            if "401" in err_str or "403" in err_str:
                print(f"[hybrid] ⚠️ Auth error — skipping provider")
                raise

            # Other → linear backoff
            wait = min(backoff_base * attempt, 10)
            print(f"[hybrid] ⚠️ {type(e).__name__} attempt {attempt + 1}/{max_retries}. Backoff {wait}s...")
            time.sleep(wait)

    raise last_error if last_error else RuntimeError("Max retries exceeded")


# ─── MINING ──────────────────────────────────────────────────────

def mine_hybrid(task_type: Optional[str] = None, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Mine with multi-provider fallback."""
    from litcoin import Agent

    # Step 1: Fetch tasks (try providers until one works)
    print("[hybrid] Fetching tasks...")
    tasks = []
    for fetch_key in ["groq-8b", "cerebras-8b", "openrouter-8b"]:
        config = get_model_config(fetch_key)
        if not config:
            continue
        model_id, api_key, api_url, _ = config
        try:
            agent = create_agent(model_id, f"manteclaw-fetch-{fetch_key}", api_key, api_url)
            tasks_raw = agent.research_tasks()
            if isinstance(tasks_raw, dict) and "tasks" in tasks_raw:
                tasks = tasks_raw["tasks"]
            elif isinstance(tasks_raw, list):
                tasks = tasks_raw
            else:
                tasks = []
            if tasks:
                print(f"[hybrid] Tasks fetched: {len(tasks)} (via {fetch_key})")
                break
        except Exception as e:
            print(f"[hybrid] ⚠️ Fetch failed on {fetch_key}: {e}")
            continue

    if not tasks:
        return {"status": "no_tasks", "message": "No tasks available or all providers failed"}

    # Step 2: Pick and score task
    target_task = None
    if task_id:
        for t in tasks:
            if t.get("id") == task_id:
                target_task = t
                break
    if not target_task:
        target_task = tasks[0]

    score, complexity, reason = score_task_complexity(target_task)
    task_title = target_task.get("title", "unknown")
    task_id_actual = target_task.get("id", "unknown")

    print(f"[hybrid] Task: {task_title}")
    print(f"[hybrid] Score: {score}/100 → {reason} → class: {complexity}")

    # Step 3: Mine with fallback chain
    chain = FALLBACK_CHAINS.get(complexity, FALLBACK_CHAINS["complex"])
    last_error = None
    attempted = []

    for model_key in chain:
        config = get_model_config(model_key)
        if not config:
            continue

        model_id, api_key, api_url, rpm = config
        attempted.append(model_key)
        print(f"[hybrid] Trying {model_key} ({model_id})...")

        try:
            agent = create_agent(model_id, f"manteclaw-{model_key}", api_key, api_url)
            result = call_with_retry(agent, task_id_actual, max_retries=2, backoff_base=2.0)

            result["_hybrid"] = {
                "model_key": model_key,
                "model_id": model_id,
                "provider": model_key.split("-")[0],
                "complexity_class": complexity,
                "score": score,
                "reason": reason,
                "task_title": task_title,
                "task_id": task_id_actual,
                "fallback_used": len(attempted) > 1,
                "attempted": attempted,
            }
            return result

        except Exception as e:
            last_error = e
            print(f"[hybrid] ❌ {model_key} failed: {type(e).__name__}: {str(e)[:80]}")
            continue

    # All exhausted
    error_msg = f"All providers exhausted. Attempted: {', '.join(attempted)}"
    raise RuntimeError(f"{error_msg}. Last: {last_error}")


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hybrid Multi-Provider Miner for Litcoiin")
    parser.add_argument("--task-id", help="Specific task ID to mine")
    parser.add_argument("--task-type", help="Filter by task type")
    parser.add_argument("--continuous", action="store_true", help="Mine continuously")
    parser.add_argument("--max-runs", type=int, default=10, help="Max runs")
    args = parser.parse_args()

    if args.continuous:
        print(f"[hybrid] Continuous mode: max {args.max_runs} runs")
        for i in range(args.max_runs):
            print(f"\n{'=' * 60}")
            print(f"[hybrid] Run {i + 1}/{args.max_runs}")
            try:
                result = mine_hybrid(args.task_type, args.task_id)
                hybrid = result.get("_hybrid", {})
                print(f"[hybrid] ✅ Mined with {hybrid.get('model_key', '?')}")
                print(f"[hybrid] Reward: {result.get('reward', 0)}")
            except Exception as e:
                print(f"[hybrid] ❌ Error: {e}")
    else:
        result = mine_hybrid(args.task_type, args.task_id)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
