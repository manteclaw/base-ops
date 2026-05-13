import string

def ascii_sum(text):
    return sum(ord(c) for c in text)

def solve_captcha(challenge):
    target = challenge["asciiTarget"]
    line_count = challenge["lineCount"]
    newline_sum = (line_count - 1) * 10
    content_target = target - newline_sum
    
    print(f"[Captcha] Target: {target}, Lines: {line_count}, Content target: {content_target}")
    
    chars = string.ascii_lowercase + ' '
    
    # Build pool of short lines
    lines_pool = []
    for c1 in chars:
        lines_pool.append((c1, ord(c1)))
        for c2 in chars:
            lines_pool.append((c1+c2, ord(c1)+ord(c2)))
            for c3 in chars:
                s = ord(c1)+ord(c2)+ord(c3)
                if s <= content_target:
                    lines_pool.append((c1+c2+c3, s))
    
    sum_to_lines = {}
    for line, s in lines_pool:
        sum_to_lines.setdefault(s, []).append(line)
    
    sums = sorted(sum_to_lines.keys())
    
    if line_count == 3:
        for s1 in sums:
            for s2 in sums:
                s3 = content_target - s1 - s2
                if s3 in sum_to_lines and s3 > 0:
                    for l1 in sum_to_lines[s1]:
                        for l2 in sum_to_lines[s2]:
                            for l3 in sum_to_lines[s3]:
                                text = f"{l1}\n{l2}\n{l3}"
                                if ascii_sum(text) == target:
                                    return text
    elif line_count == 4:
        for s1 in sums:
            for s2 in sums:
                for s3 in sums:
                    s4 = content_target - s1 - s2 - s3
                    if s4 in sum_to_lines and s4 > 0:
                        for l1 in sum_to_lines[s1]:
                            for l2 in sum_to_lines[s2]:
                                for l3 in sum_to_lines[s3]:
                                    for l4 in sum_to_lines[s4]:
                                        text = f"{l1}\n{l2}\n{l3}\n{l4}"
                                        if ascii_sum(text) == target:
                                            return text
    elif line_count == 5:
        # For 5 lines, need more efficient search
        # Use a subset of sums for lines 1-4, then compute line 5
        for s1 in sums:
            for s2 in sums:
                for s3 in sums:
                    for s4 in sums:
                        s5 = content_target - s1 - s2 - s3 - s4
                        if s5 in sum_to_lines and s5 > 0:
                            for l1 in sum_to_lines[s1][:3]:
                                for l2 in sum_to_lines[s2][:3]:
                                    for l3 in sum_to_lines[s3][:3]:
                                        for l4 in sum_to_lines[s4][:3]:
                                            for l5 in sum_to_lines[s5][:3]:
                                                text = f"{l1}\n{l2}\n{l3}\n{l4}\n{l5}"
                                                if ascii_sum(text) == target:
                                                    return text
    return None

# Test the solver with the challenge from attempt 5
challenge = {
    "asciiTarget": 482,
    "lineCount": 5,
    "format": "free_verse"
}
result = solve_captcha(challenge)
print(f"Result: {repr(result)}")
print(f"Sum check: {ascii_sum(result) if result else 'N/A'}")
