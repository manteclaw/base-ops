# WALLET.md - Base L2 Wallets

## Wallet 1 (Active Miner — CURRENT)
- **Address:** `0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C`
- **Seed:** `music tourist shine addict crew sadness jewel blossom number season sponsor atom`
- **Status:** ✅ Active — Litcoiin miner running, earning correctly
- **Note:** This is the wallet the standalone miner is currently submitting to. Verified by running process log at 2026-05-14 02:55:25.

## Wallet 2 (Compromised — DO NOT USE)
- **Address:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7`
- **Seed:** `state insane tooth rain scan march liberty man sick category noble divorce`
- **Status:** ❌ COMPROMISED — drained on 2026-05-14
- **Note:** Old wallet. All references migrated. Do not use.

## Wallet 3 (.keys/wallet.seed — UNVERIFIED)
- **Address:** `UNKNOWN` — needs derivation verification
- **Seed:** `verify exit hen lottery human wheat guide shrug endless auto you video`
- **Status:** ⚠️ Stored in `.keys/wallet.seed` but NOT used by miner
- **Note:** This seed file may be outdated or incorrect. The miner uses the seed from systemd service (see Wallet 1).

---
⚠️ **Security:** Never commit this file. Stored locally only.
⚠️ **Verified:** Wallet 1 seed-to-address confirmed by running miner process (PID 365324).
