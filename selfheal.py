#!/usr/bin/env python3
"""
Manteclaw Self-Healing Executor
Auto-retry with exponential backoff, circuit breaker, and jitter.
No more manual babysitting of flaky APIs.
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Any, Optional, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("selfheal")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern for external services."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3
    
    _failures: int = field(default=0, repr=False)
    _last_failure_time: Optional[float] = field(default=None, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _half_open_calls: int = field(default=0, repr=False)
    
    def call(self, fn: Callable, *args, **kwargs) -> Any:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"[{self.name}] Circuit half-open, testing recovery...")
            else:
                raise CircuitOpenError(f"[{self.name}] Circuit OPEN — failing fast. Retry in {self.recovery_timeout}s")
        
        if self._state == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
            raise CircuitOpenError(f"[{self.name}] Circuit HALF_OPEN limit reached")
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
        
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"[{self.name}] Recovery confirmed, circuit CLOSED")
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._half_open_calls = 0
    
    def _on_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            logger.warning(f"[{self.name}] Circuit OPEN after {self._failures} failures")
            self._state = CircuitState.OPEN


class CircuitOpenError(Exception):
    pass


class SelfHealExecutor:
    """
    Universal retry executor with:
    - Exponential backoff + jitter
    - Circuit breaker per service
    - Dead letter queue for permanent failures
    - Automatic state persistence
    """
    
    def __init__(self, state_file: str = "/root/.openclaw/workspace/.selfheal_state.json"):
        self.state_file = state_file
        self.breakers: dict[str, CircuitBreaker] = {}
        self.dead_letter: list[dict] = []
        self._load_state()
    
    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                for name, cfg in data.get("breakers", {}).items():
                    cb = CircuitBreaker(
                        name=name,
                        failure_threshold=cfg.get("failure_threshold", 5),
                        recovery_timeout=cfg.get("recovery_timeout", 60.0)
                    )
                    cb._failures = cfg.get("failures", 0)
                    cb._state = CircuitState(cfg.get("state", "closed"))
                    cb._last_failure_time = cfg.get("last_failure_time")
                    self.breakers[name] = cb
                self.dead_letter = data.get("dead_letter", [])
            except Exception as e:
                logger.warning(f"Failed to load self-heal state: {e}")
    
    def _save_state(self):
        data = {
            "breakers": {
                name: {
                    "failure_threshold": cb.failure_threshold,
                    "recovery_timeout": cb.recovery_timeout,
                    "failures": cb._failures,
                    "state": cb._state.value,
                    "last_failure_time": cb._last_failure_time,
                }
                for name, cb in self.breakers.items()
            },
            "dead_letter": self.dead_letter[-100:],  # keep last 100
            "saved_at": datetime.utcnow().isoformat()
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save self-heal state: {e}")
    
    def get_breaker(self, service: str, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> CircuitBreaker:
        if service not in self.breakers:
            self.breakers[service] = CircuitBreaker(service, failure_threshold, recovery_timeout)
        return self.breakers[service]
    
    def execute(
        self,
        fn: Callable,
        *args,
        service: str = "default",
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Any:
        """
        Execute fn with automatic retry and circuit breaking.
        
        Args:
            fn: The function to call
            service: Service name for circuit breaker isolation
            max_retries: Max retry attempts before giving up
            base_delay: Initial delay in seconds
            max_delay: Cap on delay between retries
            retryable_exceptions: Which exceptions trigger retry
            on_retry: Callback(retry_num, exception) for logging/metrics
        """
        breaker = self.get_breaker(service)
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return breaker.call(fn, *args, **kwargs)
            except CircuitOpenError:
                raise  # Don't retry if circuit is open
            except retryable_exceptions as e:
                last_exception = e
                if attempt == max_retries:
                    break
                
                # Exponential backoff with full jitter
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay)
                sleep_time = delay + jitter
                
                logger.warning(
                    f"[{service}] Attempt {attempt+1}/{max_retries+1} failed: {e}. "
                    f"Retrying in {sleep_time:.1f}s..."
                )
                
                if on_retry:
                    try:
                        on_retry(attempt + 1, e)
                    except Exception:
                        pass
                
                time.sleep(sleep_time)
        
        # Dead letter — permanent failure
        self.dead_letter.append({
            "service": service,
            "function": fn.__name__,
            "error": str(last_exception),
            "timestamp": datetime.utcnow().isoformat(),
            "args": str(args)[:200],
        })
        self._save_state()
        
        logger.error(f"[{service}] PERMANENT FAILURE after {max_retries+1} attempts: {last_exception}")
        raise last_exception
    
    def wrap(self, service: str = "default", max_retries: int = 5, base_delay: float = 1.0, **kwargs):
        """Decorator version for easy function wrapping."""
        def decorator(fn: Callable):
            @wraps(fn)
            def wrapper(*args, **call_kwargs):
                return self.execute(
                    fn, *args,
                    service=service,
                    max_retries=max_retries,
                    base_delay=base_delay,
                    **{**kwargs, **call_kwargs}
                )
            return wrapper
        return decorator
    
    def status(self) -> dict:
        """Current health status of all circuits."""
        return {
            name: {
                "state": cb._state.value,
                "failures": cb._failures,
                "last_failure": datetime.fromtimestamp(cb._last_failure_time).isoformat() if cb._last_failure_time else None,
            }
            for name, cb in self.breakers.items()
        }
    
    def reset(self, service: Optional[str] = None):
        """Reset circuit breaker(s)."""
        if service:
            if service in self.breakers:
                self.breakers[service]._state = CircuitState.CLOSED
                self.breakers[service]._failures = 0
                logger.info(f"[{service}] Circuit manually reset")
        else:
            for cb in self.breakers.values():
                cb._state = CircuitState.CLOSED
                cb._failures = 0
            logger.info("All circuits manually reset")
        self._save_state()


# Global singleton for the workspace
_executor: Optional[SelfHealExecutor] = None

def get_executor() -> SelfHealExecutor:
    global _executor
    if _executor is None:
        _executor = SelfHealExecutor()
    return _executor


# Convenience exports
def retry(
    fn: Callable,
    *args,
    service: str = "default",
    max_retries: int = 5,
    base_delay: float = 1.0,
    **kwargs
) -> Any:
    """One-shot retry call."""
    return get_executor().execute(fn, *args, service=service, max_retries=max_retries, base_delay=base_delay, **kwargs)


def heal(service: str = "default", max_retries: int = 5, base_delay: float = 1.0, **kwargs):
    """Decorator shorthand: @heal(service="nookplot")"""
    return get_executor().wrap(service=service, max_retries=max_retries, base_delay=base_delay, **kwargs)


# ── Adapters for common services ──

def heal_nookplot_call(fn: Callable, *args, **kwargs) -> Any:
    """Nookplot-specific healing (handles 504s, rate limits, auth errors)."""
    return retry(
        fn, *args,
        service="nookplot",
        max_retries=7,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, Exception),  # 504s manifest as generic errors
        **kwargs
    )


def heal_litcoiin_call(fn: Callable, *args, **kwargs) -> Any:
    """Litcoiin mining-specific healing (handles model rate limits, API 429s)."""
    return retry(
        fn, *args,
        service="litcoiin",
        max_retries=10,
        base_delay=3.0,
        max_delay=120.0,
        retryable_exceptions=(Exception,),  # OpenRouter 429s, model timeouts
        **kwargs
    )


def heal_0xwork_call(fn: Callable, *args, **kwargs) -> Any:
    """0xWork task polling healing."""
    return retry(
        fn, *args,
        service="0xwork",
        max_retries=5,
        base_delay=5.0,
        **kwargs
    )


def heal_bankr_call(fn: Callable, *args, **kwargs) -> Any:
    """Bankr API healing (handles auth expiry, IP restrictions)."""
    return retry(
        fn, *args,
        service="bankr",
        max_retries=5,
        base_delay=2.0,
        **kwargs
    )


if __name__ == "__main__":
    # Quick test
    executor = get_executor()
    
    @heal(service="test", max_retries=3, base_delay=0.5)
    def flaky_function(fail_count: int = 2):
        flaky_function.calls = getattr(flaky_function, 'calls', 0) + 1
        if flaky_function.calls <= fail_count:
            raise ConnectionError(f"Simulated failure #{flaky_function.calls}")
        return f"Success after {flaky_function.calls} calls"
    
    result = flaky_function(fail_count=2)
    print(f"Test result: {result}")
    print(f"Circuit status: {executor.status()}")
