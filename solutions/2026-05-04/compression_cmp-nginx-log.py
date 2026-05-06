# Task: cmp-nginx-log
# Type: compression
# Model: qwen/qwen-2.5-7b-instruct
# Score: 9 LITCOIN
# Timestamp: 2026-05-04T18:32:54.209Z
# ---

def compress(data: bytes) -> bytes:
    result = bytearray()
    i = 0
    while i < len(data):
        count = 1
        while i + count < len(data) and data[i] == data[i + count]:
            count += 1
        result.append(count)
        result.append(data[i])
        i += count
    return bytes(result)

def decompress(data: bytes) -> bytes:
    result = bytearray()
    i = 0
    while i < len(data):
        count = data[i]
        i += 1
        result.extend([data[i]] * count)
        i += 1
    return bytes(result)