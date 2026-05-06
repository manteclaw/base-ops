# Wallet Reference — All Addresses

## Active Wallets

### 1. Bankr Wallet (PRIMARY — Mining + 0xWork)
- **Address:** `0x550c0cec65c9e585a0e59164f147a350e75a7a56`
- **Type:** Bankr-managed (Privy)
- **Network:** Base, Ethereum, Polygon, Unichain, World Chain, Arbitrum, BNB, Solana
- **Base ETH:** 0.0003279
- **Status:** ✅ Active — key `bk_usr_RARnzAJC_pztKgaX6dCC4rF8s6k79bYUVQHLSD3Rd`
- **Purpose:** Litcoiin mining, 0xWork Agent #93, general agent ops
- **Security:** API-controlled — rotate key without changing wallet

### 2. Base Wallet 1 (COMPROMISED — DO NOT USE)
- **Address:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7`
- **Seed:** `state insane tooth rain scan march liberty man sick category noble divorce`
- **Status:** ❌ COMPROMISED — do not fund or use

### 3. Base Wallet 2
- **Address:** `0xD4E4b8e531d8AdAe126F400603361Cdda3931A8D`
- **Seed:** `vivid pair rule pulse edit mix equip hobby elbow visit portion top`
- **Status:** Active but unfunded

### 4. Bankr Wallet (SECONDARY)
- **Address:** `0x6a5fcc372a3ebca643409afe06d1eee82b5a3535`
- **Linked to:** Different Bankr account (email: ajcheasty2@gmail.com)
- **Key:** `bk_usr_LdsyvYJn_D6G8UB2gSKNMBxjnd87gqBu3DfdQZr4y`
- **Status:** Active but not used for mining/0xWork

### 5. New Consolidation Wallet
- **Address:** `0xFC56950105883F46a3bB96ac9517A110724F2F27`
- **Purpose:** User-designated primary (from 2026-05-06)
- **Status:** Created, waiting for funding

### 6. Nookplot Agent Wallet
- **Address:** `0xE8663112EdaFaCaEf5711D49e42a11D37023FA32`
- **Private Key:** Stored in `.env` as `NOOKPLOT_AGENT_PRIVATE_KEY`
- **Status:** ✅ Verified — signing works, guild #16 owner

### 7. Daydreams Taskmarket Wallet
- **Address:** `0xBE251af5140A0CEfe629364190e1840D27632aED`
- **Purpose:** x402 identity + task acceptance
- **Status:** Needs ~5 USDC funding

### 8. Zyfai Safe Wallet
- **Safe:** `0x056f49F6F0De7A7d9154127aD0a419E8632Af239`
- **EOA:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7`
- **Status:** Safe deployed, session active, needs USDC deposit

## Funding Priority

| Wallet | Need | Amount | Action |
|--------|------|--------|--------|
| Bankr (0x550c...) | Gas + mining | 0.01-0.05 ETH | Send ETH on Base |
| Daydreams (0xBE25...) | Identity + tasks | ~5 USDC | Bridge or transfer |
| Zyfai Safe | Yield farming | ~10 USDC | Deposit to start earning |
| New wallet (0xFC56...) | General purpose | User decides | Fund as needed |

## Security Notes
- Never commit wallet seeds or private keys
- `.env` stores operational keys — never commit to git
- Bankr wallet is safest: key rotation doesn't change the wallet address
- Old compromised wallet: if anything is still there, consider it lost

## Helixa On-Chain Identity
- **Token ID:** 1416
- **Agent Address:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7` (compromised wallet — may need re-mint)
- **Status:** Minted but linked to compromised address
