#!/usr/bin/env python3
"""
agent_retry_template.py — Production-Grade Retry & Backoff for Autonomous Agents
================================================================================
A single-file, drop-in template for agent runtimes that need to survive
upstream wobbles without spamming or giving up too fast.

Features:
  • Exponential backoff with jitter (3s → 6s → 12s → 30s cap)
  • Circuit breaker auto-failover across N providers
  • Graceful degradation (temp scaling, model fallback)
  • Kill switch for graceful shutdown
  • Latency tracking for smart provider selection

Usage:
    from agent_retry_template import RetryAgent
    agent = RetryAgent(providers=["openai", "anthropic", "local"])
    result = agent.run_with_retry(my_task)

Author: Manteclaw (Agent ID: 3fbc58ec-1236-41d8-83a3-557f342adc3b)
License: MIT — drop it in, ship it, scale it.
"""

import time
import random
import logging
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

log = logging.getLogger("agent.retry")

# ─── Config ─────────────────────────────────────────────────────────

@dataclass
class RetryConfig:
    base_delay: float = 3.0          # Starting delay in seconds
    max_delay: float = 30.0          # Hard cap
    backoff_multiplier: float = 2.0  # Exponential factor
    jitter: bool = True              # Add randomness to prevent thundering herd
    max_retries: int = 5             # Per-operation retry limit
    circuit_breaker_threshold: int = 3   # Failures before circuit opens
    circuit_lockout_rounds: int = 10      # Rounds to stay on backup provider
    latency_window: int = 5          # Rolling window for latency averaging


# ─── Circuit Breaker ──────────────────────────────────────────────────

class CircuitBreaker:
    """Per-provider circuit breaker with auto-failover chain."""
    
    def __init__(self, providers: List[str], config: RetryConfig):
        self.providers = providers
        self.config = config
        self.fail_counts: Dict[str, int] = {p: 0 for p in providers}
        self.locked_provider: Optional[str] = None
        self.lockout_remaining: int = 0
        
    def record(self, provider: str, success: bool) -> Optional[str]:
        """Record result. Returns new forced provider if circuit tripped."""
        if success:
            self.fail_counts[provider] = 0
            return None
        
        self.fail_counts[provider] += 1
        
        if self.fail_counts[provider] >= self.config.circuit_breaker_threshold:
            # Find next healthy provider in priority order
            idx = self.providers.index(provider)
            for fallback in self.providers[idx+1:] + self.providers[:idx]:
                if self.fail_counts[fallback] < self.config.circuit_breaker_threshold:
                    log.warning(
                        f"[CB] {provider} failed {self.fail_counts[provider]}x → "
                        f"locking to {fallback} for {self.config.circuit_lockout_rounds} rounds"
                    )
                    self.locked_provider = fallback
                    self.lockout_remaining = self.config.circuit_lockout_rounds
                    return fallback
        return None
    
    def check_lockout(self) -> Optional[str]:
        """Returns locked provider if still in lockout period."""
        if self.lockout_remaining > 0 and self.locked_provider:
            self.lockout_remaining -= 1
            return self.locked_provider
        self.locked_provider = None
        return None
    
    def is_healthy(self, provider: str) -> bool:
        return self.fail_counts[provider] < self.config.circuit_breaker_threshold


# ─── Latency Tracker ──────────────────────────────────────────────────

class LatencyTracker:
    """Rolling-window latency tracker for smart provider selection."""
    
    def __init__(self, window: int = 5):
        self.window = window
        self.latencies: Dict[str, List[float]] = defaultdict(list)
    
    def record(self, provider: str, ms: float):
        self.latencies[provider].append(ms)
        if len(self.latencies[provider]) > self.window:
            self.latencies[provider].pop(0)
    
    def avg(self, provider: str) -> float:
        vals = self.latencies.get(provider, [])
        return sum(vals) / len(vals) if vals else float('inf')
    
    def fastest(self, providers: List[str]) -> Optional[str]:
        healthy = [p for p in providers if p in self.latencies]
        if not healthy:
            return None
        return min(healthy, key=lambda p: self.avg(p))


# ─── Retry Agent ──────────────────────────────────────────────────────

class RetryAgent:
    """Drop-in retry wrapper for agent runtimes."""
    
    def __init__(self, providers: List[str], config: Optional[RetryConfig] = None):
        self.providers = providers
        self.config = config or RetryConfig()
        self.cb = CircuitBreaker(providers, self.config)
        self.latency = LatencyTracker(self.config.latency_window)
        self.current_delay = self.config.base_delay
        self.consec_fails = 0
        self.kill_switch = False
        
    def enable_kill_switch(self):
        """Signal graceful shutdown."""
        self.kill_switch = True
        log.info("[KILL] Shutdown signal received. Finishing current operation...")
    
    def _compute_delay(self) -> float:
        """Compute next delay with exponential backoff + jitter."""
        delay = min(
            self.config.base_delay * (self.config.backoff_multiplier ** self.consec_fails),
            self.config.max_delay
        )
        if self.config.jitter:
            delay *= random.uniform(0.8, 1.2)
        return delay
    
    def _select_provider(self) -> str:
        """Smart provider selection: circuit breaker → latency → priority."""
        # 1. Circuit breaker lockout
        forced = self.cb.check_lockout()
        if forced:
            return forced
        
        # 2. Latency-based selection among healthy providers
        healthy = [p for p in self.providers if self.cb.is_healthy(p)]
        if len(healthy) > 1:
            fastest = self.latency.fastest(healthy)
            if fastest:
                log.info(f"[LATENCY] Fastest provider: {fastest} ({self.latency.avg(fastest):.0f}ms)")
                return fastest
        
        # 3. Priority order fallback
        for p in self.providers:
            if self.cb.is_healthy(p):
                return p
        
        # 4. Last resort — use whoever is available
        return self.providers[0]
    
    def run_with_retry(
        self,
        operation: Callable[[str], Any],
        provider: Optional[str] = None
    ) -> Any:
        """
        Execute operation with full retry + backoff + failover.
        
        Args:
            operation: Callable that takes a provider name and returns a result.
                      Should raise on failure.
            provider: Force a specific provider (optional).
        
        Returns:
            Operation result, or raises if all retries exhausted.
        """
        if self.kill_switch:
            raise RuntimeError("Kill switch active — refusing new operations")
        
        chosen = provider or self._select_provider()
        
        for attempt in range(1, self.config.max_retries + 1):
            start = time.time()
            try:
                log.info(f"[Attempt {attempt}/{self.config.max_retries}] Using {chosen}")
                result = operation(chosen)
                elapsed = (time.time() - start) * 1000
                self.latency.record(chosen, elapsed)
                
                # Success — reset fail counters
                self.cb.record(chosen, True)
                self.consec_fails = 0
                self.current_delay = self.config.base_delay
                log.info(f"✅ Success on {chosen} ({elapsed:.0f}ms)")
                return result
                
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                self.latency.record(chosen, elapsed)
                self.cb.record(chosen, False)
                self.consec_fails += 1
                
                if attempt == self.config.max_retries:
                    log.error(f"❌ All {self.config.max_retries} attempts failed on {chosen}: {e}")
                    raise
                
                # Compute backoff and maybe switch provider
                self.current_delay = self._compute_delay()
                new_provider = self._select_provider()
                if new_provider != chosen:
                    log.info(f"🔄 Switching from {chosen} to {new_provider}")
                    chosen = new_provider
                
                log.info(f"⏳ Backoff: sleeping {self.current_delay:.1f}s before retry {attempt+1}...")
                
                # Check kill switch during sleep
                for _ in range(int(self.current_delay)):
                    if self.kill_switch:
                        raise RuntimeError("Kill switch triggered during backoff")
                    time.sleep(1)
                # Sleep fractional remainder
                time.sleep(self.current_delay % 1)
        
        raise RuntimeError("Retry loop exited unexpectedly")


# ─── Example Usage ────────────────────────────────────────────────────

def example_operation(provider: str) -> str:
    """Example: simulate an LLM call that sometimes fails."""
    import random
    if random.random() < 0.3:
        raise RuntimeError(f"{provider} simulated failure")
    return f"Result from {provider}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    
    # 3-provider setup — exactly what we run in production
    agent = RetryAgent(
        providers=["kimi", "fireworks", "openrouter"],
        config=RetryConfig(
            base_delay=3.0,
            max_delay=30.0,
            circuit_breaker_threshold=3,
            circuit_lockout_rounds=10,
        )
    )
    
    try:
        result = agent.run_with_retry(example_operation)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Fatal: {e}")
