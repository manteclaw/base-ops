#!/usr/bin/env python3
"""Debug the SIWA signature to figure out why it's invalid."""

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

PRIVATE_KEY = "0xa3b064d1104984e489a824b20971c5ee1b1a8eceabd8465d61900353c5d772ab"
AGENT_ID = 46833
ADDRESS = "0xe8663112edafacaef5711d49e42a11d37023fa32"
REGISTRY = "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"

nonce_data = {
    'nonce': '6XE4icRQjcFOygmo',
    'issuedAt': '2026-05-13T22:50:15.308Z',
    'expirationTime': '2026-05-13T22:55:15.308Z',
}

message_lines = [
    'agentmoney.net wants you to sign in with your Agent account:',
    ADDRESS,
    '',
    'Sign in to the BOTCOIN Faucet to claim your drip.',
    '',
    'URI: https://agentmoney.net/faucet',
    'Version: 1',
    f'Agent ID: {AGENT_ID}',
    f'Agent Registry: {REGISTRY}',
    'Chain ID: 8453',
    f'Nonce: {nonce_data["nonce"]}',
    f'Issued At: {nonce_data["issuedAt"]}',
    f'Expiration Time: {nonce_data["expirationTime"]}',
]
message = '\n'.join(message_lines)

print("=" * 60)
print("Message:")
print(message)
print("=" * 60)

# Method 1: eth_account encode_defunct
encoded1 = encode_defunct(text=message)
account = Account.from_key(PRIVATE_KEY)
signed1 = account.sign_message(encoded1)

print(f"\n[Method 1] eth_account encode_defunct + sign_message")
print(f"  message_hash: {signed1.message_hash.hex()}")
print(f"  signature:    {signed1.signature.hex()}")
print(f"  v: {signed1.v}, r: {hex(signed1.r)[:30]}..., s: {hex(signed1.s)[:30]}...")

# Try to recover the address
recovered1 = Account.recover_message(encoded1, signature=signed1.signature)
print(f"  recovered:    {recovered1}")

# Method 2: web3.eth.account.sign_message
w3 = Web3()
encoded2 = encode_defunct(text=message)
signed2 = w3.eth.account.sign_message(encoded2, private_key=PRIVATE_KEY)

print(f"\n[Method 2] web3.eth.account.sign_message")
print(f"  signature: {signed2.signature.hex()}")

# Method 3: raw keccak + secp256k1 sign
# This is what personal_sign does under the hood
prefix = f"\x19Ethereum Signed Message:\n{len(message)}"
raw_message = prefix + message
message_hash = Web3.keccak(text=raw_message)
print(f"\n[Method 3] Raw personal_sign hash")
print(f"  prefix: {repr(prefix)}")
print(f"  full:   {repr(raw_message[:80])}...")
print(f"  hash:   {message_hash.hex()}")

# Sign with raw hash
import eth_keys
pk = eth_keys.keys.PrivateKey(bytes.fromhex(PRIVATE_KEY[2:]))
sig = pk.sign_msg_hash(message_hash)
raw_sig = sig.to_bytes()
print(f"  raw_sig: {raw_sig.hex()}")
print(f"  v: {sig.v}, r: {hex(sig.r)[:30]}..., s: {hex(sig.s)[:30]}...")

# Adjust v for Ethereum personal_sign (27/28)
v_ethereum = sig.v + 27 if sig.v in (0, 1) else sig.v
eth_sig_bytes = raw_sig[:-1] + bytes([v_ethereum])
print(f"  eth_sig: {eth_sig_bytes.hex()}")

# Try recovering with eth_sig
from eth_account.messages import defunct_hash_message
hash_defunct = defunct_hash_message(text=message)
print(f"\n[defunct_hash_message]: {hash_defunct.hex()}")

# Verify all methods produce same hash
assert signed1.message_hash == hash_defunct, "Hash mismatch!"
print("\n✅ All hash methods match")

# The server might be checking with a different message format
# Let me try a few variations

variations = [
    # V1: Without expiration time
    '\n'.join(message_lines[:-1]),
    # V2: With lowercase address
    message.replace(ADDRESS, ADDRESS.lower()),
    # V3: No empty line after statement
    '\n'.join([l for i, l in enumerate(message_lines) if l or i in [2, 4]]),
    # V4: Just the message without any extra blank lines
    '\n'.join([l for l in message_lines if l]),
]

for i, var_msg in enumerate(variations):
    print(f"\n--- Variation {i+1} ---")
    print(f"Message: {repr(var_msg[:100])}...")
    enc = encode_defunct(text=var_msg)
    sig = account.sign_message(enc)
    rec = Account.recover_message(enc, signature=sig.signature)
    print(f"Signature: {sig.signature.hex()}")
    print(f"Recovered: {rec}")
