#!/usr/bin/env python3
"""
Secret Scanner — detects seeds, private keys, API keys in source files.
Run before every commit. Fails if secrets found.
"""
import os
import re
import sys

WORKSPACE = "/root/.openclaw/workspace"

# BIP39 word list (abbreviated for pattern matching)
BIP39_WORDS = ['abandon', 'ability', 'able', 'about', 'above', 'absent', 'absorb', 'abstract', 'absurd', 'abuse', 'access', 'accident', 'account', 'accuse', 'achieve', 'acid', 'acoustic', 'acquire', 'across', 'act', 'action', 'actor', 'actress', 'actual', 'adapt', 'add', 'addict', 'address', 'adjust', 'admit', 'adult', 'advance', 'advice', 'aerobic', 'affair', 'afford', 'afraid', 'again', 'age', 'agent', 'agree', 'ahead', 'aim', 'air', 'airport', 'aisle', 'alarm', 'album', 'alcohol', 'alert', 'alien', 'all', 'alley', 'allow', 'almost', 'alone', 'alpha', 'already', 'also', 'alter', 'always', 'amateur', 'amazing', 'among', 'amount', 'amused', 'analyst', 'anchor', 'ancient', 'anger', 'angle', 'angry', 'animal', 'ankle', 'announce', 'annual', 'another', 'answer', 'antenna', 'antique', 'anxiety', 'any', 'apart', 'apology', 'appear', 'apple', 'approve', 'april', 'arch', 'arctic', 'area', 'arena', 'argue', 'arm', 'armed', 'armor', 'army', 'around', 'arrange', 'arrest', 'arrive', 'arrow', 'art', 'artefact', 'artist', 'artwork', 'ask', 'aspect', 'assault', 'asset', 'assist', 'assume', 'asthma', 'athlete', 'atom', 'attack', 'attend', 'attitude', 'attract', 'auction', 'audit', 'august', 'aunt', 'author', 'auto', 'autumn', 'average', 'avocado', 'avoid', 'awake', 'aware', 'away', 'awesome', 'awful', 'awkward', 'axis']

# Build a regex that matches 6+ consecutive BIP39 words
word_alts = '|'.join(BIP39_WORDS)
SEED_PATTERN = rf'\b({word_alts})\s+({word_alts})\s+({word_alts})\s+({word_alts})\s+({word_alts})\s+({word_alts})'

PATTERNS = [
    (SEED_PATTERN, "SEED_PHRASE (6+ BIP39 words)"),
    (r'0x[a-fA-F0-9]{64}', "PRIVATE_KEY (64 hex)"),
    (r'sk-[a-zA-Z0-9_-]{20,}', "API_KEY (sk-*)"),
    (r'gsk_[a-zA-Z0-9_-]{20,}', "API_KEY (gsk_*)"),
    (r'fw_[a-zA-Z0-9_-]{20,}', "API_KEY (fw_*)"),
    (r'nvapi-[a-zA-Z0-9_-]{20,}', "API_KEY (nvapi-*)"),
    (r'ghp_[a-zA-Z0-9_-]{20,}', "GITHUB_TOKEN"),
    (r'zyfai_[a-f0-9]{20,}', "ZYFAI_KEY"),
    (r'bk_usr_[a-zA-Z0-9_-]{20,}', "BANKR_KEY"),
    (r'wp_agent_[a-zA-Z0-9_-]{20,}', "WORKPROTOCOL_KEY"),
    (r'nk_[a-zA-Z0-9_-]{20,}', "NOOKPLOT_KEY"),
]

SKIP_DIRS = {'.git', '.keys', 'node_modules', '__pycache__', 'venv', '.venv', '.openclaw'}
SKIP_FILES = {'.gitignore', 'secret_scanner.py', 'key_loader.py'}
SKIP_EXTS = {'.pyc', '.db', '.db3', '.png', '.jpg', '.gif', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.pdf'}

found = []

for root, dirs, files in os.walk(WORKSPACE):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    
    for fname in files:
        if fname in SKIP_FILES or any(fname.endswith(e) for e in SKIP_EXTS):
            continue
        
        fpath = os.path.join(root, fname)
        relpath = fpath.replace(WORKSPACE + '/', '')
        
        # Skip .keys directory entirely
        if '.keys' in relpath:
            continue
        
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        for pattern, label in PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                match_str = str(match)[:40]
                found.append((relpath, label, match_str))

if found:
    print(f"🚨 SECRETS FOUND: {len(found)} violations")
    print("="*60)
    for path, label, match in found[:50]:
        print(f"  {path}: [{label}] {match}...")
    if len(found) > 50:
        print(f"  ... and {len(found)-50} more")
    sys.exit(1)
else:
    print("✅ No secrets found in source files")
    sys.exit(0)
