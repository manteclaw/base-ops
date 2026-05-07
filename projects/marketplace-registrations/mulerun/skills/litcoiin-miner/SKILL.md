# Litcoiin Miner

Autonomous proof-of-research mining agent for $LITCOIN on Base L2.

## Description
Fetches research tasks from Bankr API, generates solutions using LLMs (Fireworks/OpenRouter), validates output, and submits for $LITCOIN rewards. Auto-claims when balance ≥ 50,000.

## When to Use
- User asks about Litcoiin mining
- Research task needs to be solved
- Base L2 earning opportunity
- Automated income generation

## Instructions

### 1. Task Fetching
```python
import requests

def get_task(api_key):
    resp = requests.get(
        "https://api.bankr.bot/v1/tasks/next",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    return resp.json()
```

### 2. Solution Generation
- **Primary**: Fireworks AI (`accounts/fireworks/models/llama-v3p3-70b-instruct`)
- **Fallback**: OpenRouter (`meta-llama/llama-3.3-70b-instruct`)
- Track latency per provider, use fastest
- Cache solutions to avoid duplicate work

### 3. Validation Pipeline
```python
def validate_solution(task_type, solution):
    if task_type == "smart_contracts":
        return validate_solidity(solution)
    elif task_type == "tcg_card_profile":
        return len(solution) > 500 and "card" in solution.lower()
    elif task_type == "ai_safety":
        return check_alignment(solution)
    return True
```

### 4. Task Rotation Strategy
Skip low-value tasks (< 5% success rate):
- `bioinformatics` — 0% success (dead)
- `agentic_trace` — 0% success (dead)
- `software_eng` — ~0.1% success (skip)

Focus on high-value tasks:
- `tcg_card_profile` — 47.5 avg LITCOIN, 79 submissions
- `ai_safety` — 67.9 avg LITCOIN, 32 submissions
- `smart_contracts` — 28 avg LITCOIN, 23 submissions

### 5. Auto-Claim
```python
if balance >= 50000:
    claim_litcoiin()
    log_claim(tx_hash, amount)
```

## Scripts
- `task_solver.py` — Fetch, solve, and submit tasks
- `claim_manager.py` — Balance checking and auto-claim

## References
- `bankr_api.md` — Bankr API endpoints and authentication
