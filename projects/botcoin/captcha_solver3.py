import string

def ascii_sum(text):
    return sum(ord(c) for c in text)

# We need 4 lines, total ASCII = 339
# Newlines: 3 * 10 = 30
# Content must sum to 309

target = 339
newline_sum = 30
content_target = target - newline_sum  # = 309

print(f"Target: {target}, Newlines: {newline_sum}, Content target: {content_target}")

# Let's try a much smarter approach:
# Generate lines with exact sums using dynamic programming
# We need 4 lines where each line's ascii sum + 3*10 = 339
# So line1 + line2 + line3 + line4 = 309

# Since lowercase 'a' = 97, even 3 chars = 291, close to 309
# 4 chars = 388, too high
# So lines must be 1-3 chars mostly, with some spaces

# Let's generate all possible 1-3 char combinations and find a set of 4 that sums to 309
chars = string.ascii_lowercase + ' '

# Generate all possible 1-char lines (but 'a' = 97, too high for 4 of them = 388)
# Need some empty lines or spaces
# Space = 32, 'a' = 97

# Let's find exact combos
# We need a+b+c+d = 309 where each is a line's ascii sum
# Try combinations of 1-3 char lines

lines_dict = {}  # sum -> list of lines with that sum

# 1-char lines
for c in chars:
    s = ord(c)
    lines_dict.setdefault(s, []).append(c)

# 2-char lines
for c1 in chars:
    for c2 in chars:
        line = c1 + c2
        s = ord(c1) + ord(c2)
        lines_dict.setdefault(s, []).append(line)

# 3-char lines (selectively, only sums around 70-100)
for c1 in chars:
    for c2 in chars:
        for c3 in chars:
            line = c1 + c2 + c3
            s = ord(c1) + ord(c2) + ord(c3)
            if 70 <= s <= 110:
                lines_dict.setdefault(s, []).append(line)

print(f"Generated {sum(len(v) for v in lines_dict.values())} line candidates")

# Find 4 lines that sum to 309
sums = sorted(lines_dict.keys())
found = []

for s1 in sums:
    for s2 in sums:
        for s3 in sums:
            s4 = content_target - s1 - s2 - s3
            if s4 in lines_dict and s4 > 0:
                # Found a valid combination
                for l1 in lines_dict[s1][:1]:
                    for l2 in lines_dict[s2][:1]:
                        for l3 in lines_dict[s3][:1]:
                            for l4 in lines_dict[s4][:1]:
                                text = f"{l1}\n{l2}\n{l3}\n{l4}"
                                if ascii_sum(text) == target:
                                    found.append((text, s1, s2, s3, s4))
                                    if len(found) >= 5:
                                        break
                            if len(found) >= 5:
                                break
                        if len(found) >= 5:
                            break
                    if len(found) >= 5:
                        break
                if len(found) >= 5:
                    break
        if len(found) >= 5:
            break
    if len(found) >= 5:
        break

for i, (text, s1, s2, s3, s4) in enumerate(found[:10]):
    print(f"\nSolution {i+1}:")
    print(f"  Text: {repr(text)}")
    print(f"  Sum check: {ascii_sum(text)} (target: {target})")
    print(f"  Lines: {len(text.split(chr(10)))}, Words: {len(text.split())}")
    print(f"  Line sums: {s1}, {s2}, {s3}, {s4} = {s1+s2+s3+s4}")
