#!/usr/bin/env python3
"""Load .env from .keys/ directory securely."""
import os
from pathlib import Path

def load_env():
    keys_dir = Path(__file__).parent.parent / ".keys"
    env_file = keys_dir / ".env"
    
    if env_file.exists():
        # Manual dotenv loading (no external dep)
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key, value)
    
    # Also set wallet from .keys/
    seed_file = keys_dir / "wallet.seed"
    if seed_file.exists():
        os.environ.setdefault("WALLET_SEED_FILE", str(seed_file))
    
    key_file = keys_dir / "wallet.key"
    if key_file.exists():
        os.environ.setdefault("WALLET_KEY_FILE", str(key_file))
    
    return True

if __name__ == "__main__":
    load_env()
    print(f"WALLET_ADDRESS={os.environ.get('WALLET_ADDRESS', 'NOT_SET')}")
    print(f"WALLET_SEED_FILE exists: {(Path(__file__).parent.parent / '.keys' / 'wallet.seed').exists()}")
