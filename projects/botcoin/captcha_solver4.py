import string

def ascii_sum(text):
    return sum(ord(c) for c in text)

target = 339
newline_sum = 30
content_target = target - newline_sum  # = 309

chars = string.ascii_lowercase + ' '

lines_dict = {}

# 1-4 char lines, but focus on readable ones
for c1 in chars:
    for c2 in chars:
        for c3 in chars:
            for c4 in chars:
                line = c1 + c2 + c3 + c4
                s = ord(c1) + ord(c2) + ord(c3) + ord(c4)
                if 30 <= s <= 200 and line.strip():  # wider range, not all spaces
                    lines_dict.setdefault(s, []).append(line)

print(f"Generated {sum(len(v) for v in lines_dict.values())} 4-char line candidates")

# Also generate some 3-char and 5-char lines
for length in [3, 5]:
    for _ in range(5000):
        import random
        line = ''.join(random.choice(chars) for _ in range(length)).strip()
        if line:
            s = sum(ord(c) for c in line)
            if 50 <= s <= 130:
                lines_dict.setdefault(s, []).append(line)

# Find readable solutions with more words
sums = sorted(lines_dict.keys())
found = []

for s1 in sums:
    for s2 in sums:
        for s3 in sums:
            s4 = content_target - s1 - s2 - s3
            if s4 in lines_dict and s4 > 0:
                for l1 in lines_dict[s1]:
                    if not l1.strip():
                        continue
                    for l2 in lines_dict[s2]:
                        if not l2.strip():
                            continue
                        for l3 in lines_dict[s3]:
                            if not l3.strip():
                                continue
                            for l4 in lines_dict[s4]:
                                if not l4.strip():
                                    continue
                                text = f"{l1}\n{l2}\n{l3}\n{l4}"
                                if ascii_sum(text) == target:
                                    words = len(text.split())
                                    # Score: prefer more words, more readable
                                    score = words * 10 + min(len(l1), len(l2), len(l3), len(l4))
                                    found.append((score, text, words, [l1, l2, l3, l4]))
                                    if len(found) > 10000:
                                        found.sort(reverse=True)
                                        found = found[:1000]

found.sort(reverse=True)

print(f"\nTop 10 readable solutions (sorted by word count + line length):")
for i, (score, text, words, lines) in enumerate(found[:10]):
    print(f"\nSolution {i+1} (score={score}, words={words}):")
    print(f"  Text: {repr(text)}")
    print(f"  Sum check: {ascii_sum(text)}")
    print(f"  Lines: {lines}")
