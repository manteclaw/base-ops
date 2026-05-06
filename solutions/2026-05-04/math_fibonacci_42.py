# Task: fibonacci_42
# Type: math
# Model: venice-qwen
# Score: 15 LITCOIN
# Timestamp: 2026-05-04T17:17:35.074Z
# ---

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
