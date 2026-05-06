# Task: cmp-alternating-bytes
# Type: compression
# Model: qwen/qwen-2.5-7b-instruct
# Score: 1232 LITCOIN
# Timestamp: 2026-05-04T18:44:07.512Z
# ---

def compress(data: bytes) -> bytes:
    if len(data) < 2:
        return data
    
    compressed = bytearray()
    even_index = 0
    odd_index = 1
    
    while even_index < len(data) or odd_index < len(data):
        even_byte = data[even_index] if even_index < len(data) else 0
        odd_byte = data[odd_index] if odd_index < len(data) else 0
        
        # XOR the two bytes to get the difference
        diff = even_byte ^ odd_byte
        
        # Append the even byte to the compressed data
        compressed.append(even_byte)
        
        # If there's an odd byte, append the difference
        if odd_index < len(data):
            compressed.append(diff)
        
        even_index += 2
        odd_index += 2
    
    return bytes(compressed)

def decompress(compressed: bytes) -> bytes:
    decompressed = bytearray()
    i = 0
    
    while i < len(compressed):
        even_byte = compressed[i]
        decompressed.append(even_byte)
        
        if i + 1 < len(compressed):
            diff = compressed[i + 1]
            odd_byte = even_byte ^ diff
            decompressed.append(odd_byte)
        
        i += 2
    
    return bytes(decompressed)