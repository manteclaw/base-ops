# Task: bcb-lru-cache
# Type: data_structures
# Model: qwen/qwen-2.5-7b-instruct
# Score: 0 LITCOIN
# Timestamp: 2026-05-04T21:30:55.168Z
# ---

from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key) -> int:
        if key not in self.cache:
            return -1
        value = self.cache.pop(key)
        self.cache[key] = value  # Move the accessed item to the end.
        return value

    def put(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) == self.capacity:
            self.cache.popitem(last=False)  # Remove the least recently used item.
        self.cache[key] = value  # Insert the new item.