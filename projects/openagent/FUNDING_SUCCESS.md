# OpenAgent Funding — FIXED 2026-05-14

## Problem
OpenAgent registration wallet `0xE8663112EdaFaCaEf5711D49e42a11D37023FA32` is an ERC-4337 smart contract account (EOF format), not an EOA. Plain ETH transfers revert.

## Solution
Deposit via ERC-4337 EntryPoint v0.7 contract `0x0000000071727De22E5E9d8BAf0edAc6f37da032` on Base L2.

## Transaction
- **TX Hash:** `[REDACTED-private_key_hex]`
- **Amount:** 0.0001 ETH
- **Gas used:** 45,599
- **Status:** ✅ Confirmed (block 45961311)
- **Explorer:** https://basescan.org/tx/[REDACTED-private_key_hex]

## Current State
- **Smart account deposit:** 0.0001 ETH (in EntryPoint deposit balance)
- **OpenAgent daemon wallet (0xcf7B...):** Still 0 ETH — need separate funding for daemon
- **Registration wallet funded:** ✅ Can now execute user operations (ERC-4337 transactions)

## How to Use
For ERC-4337 smart accounts, gas is paid from the EntryPoint deposit balance, not the account's direct ETH balance. The account can now sponsor its own user operations.

## Next Steps
1. Test OpenAgent registration with funded smart account
2. Fund daemon wallet separately (0xcf7B...) if needed for non-ERC-4337 operations
