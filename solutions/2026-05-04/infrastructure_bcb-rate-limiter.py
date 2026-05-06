# Task: bcb-rate-limiter
# Type: infrastructure
# Model: qwen/qwen-2.5-7b-instruct
# Score: 0 LITCOIN
# Timestamp: 2026-05-04T21:15:44.070Z
# ---

from collections import deque
from time import time

class RateLimiter:
    def __init__(self, rate: float, capacity: int):
        if rate <= 0 or capacity < 1:
            raise ValueError("Rate must be positive and capacity must be at least 1.")
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill_time = time()
        self.refill_queue = deque()

    def allow(self, timestamp: float) -> bool:
        if timestamp < 0:
            raise ValueError("Timestamp cannot be negative.")
        current_time = timestamp or time()
        elapsed_time = current_time - self.last_refill_time
        self._refill_tokens(elapsed_time)
        if self.tokens > 0:
            self.tokens -= 1
            self.last_refill_time = current_time
            return True
        return False

    def _refill_tokens(self, elapsed_time: float):
        while self.tokens < self.capacity and self.refill_queue:
            _, next_refill_time = self.refill_queue[0]
            if elapsed_time >= next_refill_time - self.last_refill_time:
                self.tokens += self.rate * (next_refill_time - self.last_refill_time)
                self.last_refill_time = next_refill_time
                self.refill_queue.popleft()
            else:
                break
        if self.tokens > self.capacity:
            self.tokens = self.capacity