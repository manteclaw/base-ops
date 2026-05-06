# Task: cmp-english-prose-long
# Type: compression
# Model: qwen/qwen-2.5-7b-instruct
# Score: 0 LITCOIN
# Timestamp: 2026-05-04T20:31:15.938Z
# ---

def compress(data: bytes) -> bytes:
    if not data:
        return data
    
    result = bytearray()
    count = 1
    prev = data[0]
    
    for i in range(1, len(data)):
        if data[i] == prev:
            count += 1
        else:
            result.append(prev)
            result.append(count & 0xFF)
            prev = data[i]
            count = 1
    result.append(prev)
    result.append(count & 0xFF)
    
    # Ensure round-trip is lossless
    if len(result) >= len(data):
        return data
    
    return bytes(result)

def decompress(data: bytes) -> bytes:
    if not data:
        return data
    
    result = bytearray()
    i = 0
    while i < len(data):
        value = data[i]
        count = data[i + 1]
        result.extend([value] * count)
        i += 2
    
    return bytes(result)