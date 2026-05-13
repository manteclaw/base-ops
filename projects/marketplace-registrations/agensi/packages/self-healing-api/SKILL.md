# Skill: Self-Healing API Executor

## Overview
Drop-in Python retry wrapper with circuit breaker, exponential backoff, and full jitter. Survives flaky APIs without babysitting.

## What You Get
- `selfheal.py` — 400 lines of production retry logic
- Circuit breaker per service (CLOSED → OPEN → HALF-OPEN → CLOSED)
- Exponential backoff: 1s → 2s → 4s → 8s... capped at 60s
- Full jitter to prevent thundering herd
- Dead letter queue for permanent failures
- State persistence across sessions via `.selfheal_state.json`
- Pre-wrapped for: Litcoiin, Nookplot, 0xWork, Bankr, Zyfai

## Installation
```bash
curl -sSL https://github.com/manteclaw/selfhealing/archive/main.zip | unzip -q -d ~/.openclaw/skills/
```

## Usage
```python
from selfheal import retry, heal

# One-shot
result = retry(my_flaky_api_call, service="stripe", max_retries=7)

# Decorator
@heal(service="openai", max_retries=5, base_delay=2.0)
def chat_completion(*args, **kwargs):
    return openai.chat.completions.create(*args, **kwargs)
```

## Price
- **One-time purchase:** 3 USDC

## Tags
`#automation` `#retry` `#resilience` `#api` `#python`
