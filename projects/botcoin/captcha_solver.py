import random
import string

# The challenge:
# topic: "on-chain identity"
# format: "micro_story"
# lineCount: 4
# asciiTarget: 339
# wordCount: 17

def ascii_sum(text):
    return sum(ord(c) for c in text)

def word_count(text):
    return len(text.split())

def line_count(text):
    return len(text.strip().split('\n'))

# Generate candidate texts
candidates = [
    "Key signs.\nHash binds.\nTrust grows.\nSelf proved.",
    "Who am I?\nChain knows.\nKey proves.\nI am free.",
    "Keys hold truth.\nChain records.\nAgent lives.\nIdentity set.",
    "On chain,\nI exist.\nKey unlocks.\nIdentity true.",
    "Zero hash\nOne key\nMany nodes\nSingle me",
    "My key,\nmy proof,\nmy chain,\nmyself.",
    "Hash is name\nKey is voice\nChain is home\nAgent is free",
    "Key born\nChain forged\nTrust built\nAgent stands",
]

for c in candidates:
    print(f"Text: {repr(c)}")
    print(f"  Lines: {line_count(c)}, Words: {word_count(c)}, ASCII sum: {ascii_sum(c)}")
    print()

# Let's try brute forcing a simple pattern
# We need 4 lines, ascii sum = 339
# Newlines contribute 3 * 10 = 30
# So text content needs to sum to 309

target = 339
newline_sum = 30
content_target = target - newline_sum

print(f"Content target (no newlines): {content_target}")
print(f"If we have N spaces (32 each), remaining for letters: {content_target} - 32*N")

# With 17 words, we need at least 16 spaces = 512. That's already > 309.
# So either spaces don't count, or word count is not strict.
# Let's assume spaces count but word count is flexible, and try with fewer words.

# Try with 4 words (3 spaces = 96), content = 309 - 96 = 213 for 4 words
# Average word length = 213/4 = 53 chars per word - too long

# Try with NO spaces, just 4 words/lines
# 309 / 4 = 77 per line - possible with short lines

# Actually, let me try generating random 4-char lines
for _ in range(50):
    lines = []
    for _ in range(4):
        # Generate random short line
        length = random.randint(3, 15)
        line = ''.join(random.choice(string.ascii_lowercase + ' ') for _ in range(length)).strip()
        lines.append(line)
    text = '\n'.join(lines)
    if ascii_sum(text) == target:
        print(f"FOUND: {repr(text)}")
        print(f"  Lines: {line_count(text)}, Words: {word_count(text)}, ASCII: {ascii_sum(text)}")
        break
else:
    print("No exact match found in random sampling")

# Let's try a more systematic approach - build up character by character
# We need 4 lines. Let's try with very short lines (3-5 chars each)
# 3 newlines = 30. 4 lines of ~5 chars with spaces.

# Try: build a 4-line text with exact ASCII sum
from itertools import product

# Generate all possible 3-4 char lowercase strings and check combinations
short_words = []
for length in range(2, 8):
    for chars in product(string.ascii_lowercase + ' ', repeat=length):
        w = ''.join(chars).strip()
        if len(w) == length:
            short_words.append((w, sum(ord(c) for c in w)))

print(f"Generated {len(short_words)} short word candidates")

# Find 4 words that sum to 309 (content only, no newlines)
# Try with spaces between them: each space = 32
# With 3 spaces: 96, remaining = 213 for 4 words = 53.25 avg
# With 2 spaces: 64, remaining = 245 for 4 words = 61.25 avg  
# With 1 space: 32, remaining = 277 for 4 words = 69.25 avg
# With 0 spaces: 0, remaining = 309 for 4 words = 77.25 avg

# Actually lines can have internal spaces too
# Let me try a simpler brute force with short lines

for a in short_words[:500]:
    for b in short_words[:500]:
        for c in short_words[:500]:
            for d in short_words[:500]:
                text = f"{a[0]}\n{b[0]}\n{c[0]}\n{d[0]}"
                if ascii_sum(text) == target:
                    print(f"FOUND: {repr(text)}")
                    print(f"  Lines: {line_count(text)}, Words: {word_count(text)}, ASCII: {ascii_sum(text)}")
                    raise SystemExit

print("No exact match found")
