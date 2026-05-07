#!/usr/bin/env python3
"""
Multi-Provider LLM Router v1.0
Intelligent routing across 7+ LLM providers with circuit breaker,
latency-based selection, and automatic failover.

Usage:
    from router import LLMRouter
    router = LLMRouter()
    response = router.chat("Write a Python function to sort a list", provider="auto")
"""

import os
import time
import json
import random
import logging
from typing import Optional, Tuple, List
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("llm-router")

# ── Provider configs ──
PROVIDERS = {
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1",
        "models": ["meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct"],
        "timeout": 120,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "timeout": 30,
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
        "timeout": 60,
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1",
        "models": ["llama-3.3-70b", "llama-4-scout-17b-16e"],
        "timeout": 30,
    },
    "fireworks": {
        "url": "https://api.fireworks.ai/inference/v1",
        "models": ["accounts/fireworks/models/llama-v3p3-70b-instruct", "accounts/fireworks/models/qwen3-235b-a22b"],
        "timeout": 60,
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "timeout": 30,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1",
        "models": ["inclusionai/ling-2.6-1t:free", "nvidia/nemotron-3-super-120b-a12b:free"],
        "timeout": 60,
    },
}

class LLMRouter:
    """Intelligent LLM provider router with circuit breaker and latency tracking."""
    
    CB_TRIGGER_FAILURES = 3
    CB_LOCKOUT_ROUNDS = 10
    
    def __init__(self, keys: dict = None, priority: List[str] = None):
        """
        keys: {"nvidia": "nvapi-...", "groq": "gsk_...", ...}
        priority: provider order (default: nvidia > groq > deepseek > cerebras > fireworks > kimi > openrouter)
        """
        self.keys = keys or self._load_keys_from_env()
        self.priority = priority or ["nvidia", "groq", "deepseek", "cerebras", "fireworks", "kimi", "openrouter"]
        self.latencies = {p: [] for p in PROVIDERS}
        self.fails = {p: 0 for p in PROVIDERS}
        self.cb_lockout = {p: 0 for p in PROVIDERS}
        self.cb_forced = None
        
    def _load_keys_from_env(self) -> dict:
        return {
            p: os.environ.get(f"{p.upper()}_API_KEY", "")
            for p in PROVIDERS
        }
    
    def _available(self, provider: str) -> bool:
        return bool(self.keys.get(provider))
    
    def _healthy(self, provider: str) -> bool:
        if not self._available(provider):
            return False
        if self.cb_lockout.get(provider, 0) > 0:
            return False
        return self.fails.get(provider, 0) < self.CB_TRIGGER_FAILURES
    
    def _fastest(self) -> Optional[str]:
        """Return provider with lowest avg latency among healthy ones."""
        candidates = {p: self.latencies[p] for p in self.priority if self._healthy(p) and self.latencies[p]}
        if not candidates:
            return None
        return min(candidates, key=lambda p: sum(candidates[p]) / len(candidates[p]))
    
    def select(self, force_provider: str = None) -> Optional[str]:
        """Select best provider. Use force_provider to override."""
        if force_provider and self._available(force_provider):
            return force_provider
        
        # Circuit breaker lockout
        if self.cb_forced:
            self.cb_lockout[self.cb_forced] -= 1
            if self.cb_lockout[self.cb_forced] <= 0:
                self.cb_forced = None
            else:
                return self.cb_forced
        
        # Priority order with health check
        for p in self.priority:
            if self._healthy(p):
                return p
        
        # Fallback: anyone available
        for p in self.priority:
            if self._available(p):
                return p
        return None
    
    def chat(self, prompt: str, system: str = None, model: str = None, 
             provider: str = "auto", temperature: float = 0.1, 
             max_tokens: int = 2048) -> Tuple[str, str]:
        """
        Send chat completion. Returns (content, actual_provider).
        provider="auto" uses intelligent selection.
        """
        selected = self.select(provider if provider != "auto" else None)
        if not selected:
            raise RuntimeError("No LLM providers available. Set API keys.")
        
        config = PROVIDERS[selected]
        key = self.keys[selected]
        use_model = model or config["models"][0]
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        
        start = time.time()
        try:
            r = requests.post(f"{config['url']}/chat/completions", 
                            headers=headers, json=payload, 
                            timeout=config["timeout"])
            elapsed = (time.time() - start) * 1000
            self.latencies[selected].append(elapsed)
            
            if r.status_code != 200:
                self.fails[selected] += 1
                if self.fails[selected] >= self.CB_TRIGGER_FAILURES:
                    log.warning(f"[CB] {selected} failed {self.fails[selected]}x → lockout")
                    self.cb_forced = self._next_provider(selected)
                    self.cb_lockout[self.cb_forced] = self.CB_LOCKOUT_ROUNDS
                raise RuntimeError(f"{selected} error {r.status_code}: {r.text[:200]}")
            
            self.fails[selected] = 0
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            actual_model = data.get("model", use_model)
            log.info(f"[{selected}] {actual_model} | {elapsed:.0f}ms | {len(content)} chars")
            return content, selected
            
        except Exception as e:
            self.fails[selected] += 1
            # Try next provider
            next_p = self._next_provider(selected)
            if next_p and next_p != selected:
                log.info(f"{selected} failed, failing over to {next_p}")
                return self.chat(prompt, system, model, next_p, temperature, max_tokens)
            raise
    
    def _next_provider(self, current: str) -> Optional[str]:
        """Get next provider in priority order after current."""
        idx = self.priority.index(current)
        for p in self.priority[idx+1:]:
            if self._available(p):
                return p
        return None
    
    def health(self) -> dict:
        """Return health status of all providers."""
        return {
            p: {
                "available": self._available(p),
                "healthy": self._healthy(p),
                "fails": self.fails[p],
                "avg_latency_ms": sum(self.latencies[p])/len(self.latencies[p]) if self.latencies[p] else None,
                "lockout": self.cb_lockout[p],
            }
            for p in PROVIDERS
        }

# ── CLI test ──
if __name__ == "__main__":
    router = LLMRouter()
    print(json.dumps(router.health(), indent=2))
    
    # Quick test if keys are set
    if any(router.keys.values()):
        result, provider = router.chat("Say 'Router is working' and nothing else.")
        print(f"\n✅ Provider: {provider}")
        print(f"Response: {result[:100]}")
    else:
        print("\n⚠️ No API keys set. Export NVIDIA_API_KEY, GROQ_API_KEY, etc.")
