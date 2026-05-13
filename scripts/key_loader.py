#!/usr/bin/env python3
"""
Wallet key loader — reads from secure file storage.
NEVER hardcode seeds in source code. NEVER share seeds in chat.
"""
import os

KEYS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".keys")

def load_seed():
    """Load wallet seed from secure storage."""
    seed_file = os.environ.get("WALLET_SEED_FILE", os.path.join(KEYS_DIR, "wallet.seed"))
    with open(seed_file, "r") as f:
        return f.read().strip()

def load_private_key():
    """Load raw private key hex from secure storage."""
    key_file = os.environ.get("WALLET_KEY_FILE", os.path.join(KEYS_DIR, "wallet.key"))
    with open(key_file, "r") as f:
        return f.read().strip()

def get_wallet_address():
    """Derive address from seed (requires eth_account)."""
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
    seed = load_seed()
    account = Account.from_mnemonic(seed, account_path="m/44'/60'/0'/0/0")
    return account.address

if __name__ == "__main__":
    print("Current wallet:", get_wallet_address())
