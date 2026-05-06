# Task: cmp-dna-coding
# Type: compression
# Model: qwen/qwen-2.5-7b-instruct
# Score: 0 LITCOIN
# Timestamp: 2026-05-04T22:39:35.141Z
# ---

from collections import Counter
import math

def compress(data: bytes) -> bytes:
    # Convert bytes to a string of ASCII values
    ascii_str = ''.join(chr(b) for b in data)
    # Count frequency of each codon (3 consecutive characters)
    freq = Counter(ascii_str[i:i+3] for i in range(len(ascii_str)-2))
    # Generate Huffman codes
    huffman_codes = generate_huffman_codes(freq)
    # Encode the data using Huffman codes
    encoded_data = ''.join(huffman_codes[cod] for cod in ascii_str)
    # Calculate the optimal number of bits per symbol
    avg_bits_per_symbol = sum(freq[cod] * len(huffman_codes[cod]) for cod in freq) / len(ascii_str)
    # Pad the encoded data to make it a multiple of 8 bits
    padded_encoded_data = encoded_data + '0' * (8 - len(encoded_data) % 8)
    # Convert to bytes
    return int(padded_encoded_data, 2).to_bytes((len(padded_encoded_data) + 7) // 8, byteorder='big')

def decompress(data: bytes) -> bytes:
    # Convert bytes to an integer
    int_data = int.from_bytes(data, byteorder='big')
    # Convert integer to binary string
    binary_str = bin(int_data)[2:].zfill(len(data) * 8)
    # Remove padding
    encoded_data = binary_str.rstrip('0')
    # Decode using Huffman codes
    ascii_str = ''
    current_code = ''
    huffman_codes_inv = {v: k for k, v in generate_huffman_codes(Counter()).items()}
    for bit in encoded_data:
        current_code += bit
        if current_code in huffman_codes_inv:
            ascii_str += huffman_codes_inv[current_code]
            current_code = ''
    # Convert ASCII string to bytes
    return bytes([ord(c) for c in ascii_str])

def generate_huffman_codes(freq):
    nodes = [[weight, [symbol, ""]] for symbol, weight in freq.items()]
    while len(nodes) > 1:
        nodes = sorted(nodes, key=lambda x: x[0])
        left, right = nodes[:2]
        for pair in left[1:]:
            pair[1] = '0' + pair[1]
        for pair in right[1:]:
            pair[1] = '1' + pair[1]
        nodes = nodes[2:]
        nodes.append([left[0][0] + right[0][0]] + left[1:] + right[1:])
    huffman_codes = dict(nodes[0][1:])
    return huffman_codes