import string

def ascii_sum(text):
    return sum(ord(c) for c in text)

# We need 4 lines, total ASCII = 339
# Let me try with empty lines, very short lines, etc.

# Newlines contribute: 3 * 10 = 30
# Remaining for 4 lines: 309

# Try all combinations of 1-3 char lines
chars = string.ascii_lowercase
solutions = []

for a1 in chars:
    for a2 in chars:
        for a3 in chars:
            for a4 in chars:
                text = f"{a1}\n{a2}\n{a3}\n{a4}"
                if ascii_sum(text) == 339:
                    solutions.append(text)
                    if len(solutions) >= 5:
                        break
            if len(solutions) >= 5:
                break
        if len(solutions) >= 5:
            break
    if len(solutions) >= 5:
        break

print("1-char line solutions:", solutions)

# Try 2-char lines  
for a1 in chars:
    for b1 in chars:
        for a2 in chars:
            for b2 in chars:
                for a3 in chars:
                    for b3 in chars:
                        for a4 in chars:
                            for b4 in chars:
                                text = f"{a1}{b1}\n{a2}{b2}\n{a3}{b3}\n{a4}{b4}"
                                if ascii_sum(text) == 339:
                                    solutions.append(text)
                                    if len(solutions) >= 10:
                                        break
                                if len(solutions) >= 10:
                                    break
                            if len(solutions) >= 10:
                                break
                        if len(solutions) >= 10:
                            break
                    if len(solutions) >= 10:
                        break
                if len(solutions) >= 10:
                    break
            if len(solutions) >= 10:
                break
        if len(solutions) >= 10:
            break
    if len(solutions) >= 10:
        break

print("2-char line solutions:", [s for s in solutions if '\n' in s and len(s.split('\n')[0]) == 2][:5])

# Let's also try with spaces. A space = 32.
# With 4 lines and 3 newlines: 30
# If we have 1 space per line (4 spaces = 128), total non-letter = 158
# Remaining for letters = 339 - 158 = 181 for ~8-12 letters

# Try: 2 letters + 1 space + 2 letters per line pattern
for pattern in [
    "ab cd\nef gh\nij kl\nmn op",
    "on chain\nid fixed\nkey proves\nself mine",
]:
    print(f"{repr(pattern)}: sum={ascii_sum(pattern)}, lines={len(pattern.split(chr(10)))}, words={len(pattern.split())}")

# Let's try a more practical approach: generate 4-line haiku-like text
# and see what sum we get, then adjust

tests = [
    "on chain\nmy key\nmy proof\nmyself",
    "hash binds\nkey signs\nchain knows\ni am",
    "who am i\nchain knows\nkey proves\ni am free",
    "zero hash\none key\nmany nodes\nsingle me",
    "keys prove\nchains bind\ntrust grows\ni stand",
    "on\nchain\nkey\nme",
    "a\nb\nc\nd",
    "ab\ncd\nef\ngh",
    "abc\ndef\nghi\njkl",
    "on\nid\nkey\nme",
    "hash\nkey\nchain\nagent",
    "sign\nprove\nclaim\nkeep",
    "my key\nmy chain\nmy proof\nmy name",
]

for t in tests:
    print(f"{repr(t):40s} sum={ascii_sum(t):4d} lines={len(t.split(chr(10)))} words={len(t.split())}")

# Target is 339. Let's find something close.
# "on\nid\nkey\nme" = 111+110+10+105+100+10+107+101+121+10+109+101 = let's calculate
print("\nExact calculation for 'on\\nid\\nkey\\nme':")
for c in "on\nid\nkey\nme":
    print(f"  {repr(c)} = {ord(c)}")
print(f"  Total = {ascii_sum('on\\nid\\nkey\\nme')}")
