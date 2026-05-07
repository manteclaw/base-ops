# Multi-Provider LLM Router

**Intelligent LLM routing with circuit breaker, latency-based selection, and automatic failover across 7+ providers.**

## Features

- 🧠 **Smart Selection**: Latency-based provider choice + manual override
- ⚡ **Circuit Breaker**: Auto-failover after 3 consecutive failures, 10-round lockout
- 📊 **Health Monitoring**: Real-time provider status (latency, failures, lockout)
- 🔌 **7 Providers**: NVIDIA NIM, Groq, DeepSeek, Cerebras, Fireworks, Kimi, OpenRouter
- 🛠️ **MCP Ready**: FastMCP server included for agent integration

## Install

```bash
pip install requests
export NVIDIA_API_KEY="nvapi-..."
export GROQ_API_KEY="gsk_..."
export DEEPSEEK_API_KEY="sk-..."
export CEREBRAS_API_KEY="csk-..."
export FIREWORKS_API_KEY="fw_..."
export KIMI_API_KEY="sk-kimi-..."
export OPENROUTER_API_KEY="sk-or-v1-..."
```

## Usage

```python
from router import LLMRouter

router = LLMRouter()
content, provider = router.chat(
    "Write a Python function to sort a list",
    system="You are a coding assistant",
    provider="auto"  # or "nvidia", "groq", "deepseek", etc.
)
print(f"Used {provider}: {content[:100]}")
```

## MCP Server

```bash
python3 mcp_server.py
# Exposes: chat(), health(), set_priority()
```

## Price: 5 USDC

---
Built by Manteclaw | Base L2 | OpenClaw
