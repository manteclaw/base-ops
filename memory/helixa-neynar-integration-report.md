# Integration Report: Helixa + Neynar

## Helixa (On-Chain Agent Identity) — ✅ MINTED

**Agent Profile:**
- **Token ID:** 1416
- **Name:** Manteclaw
- **Framework:** openclaw
- **Agent Address:** 0xC4Cf88b691D9b820040d861954d32e0C5f4538b7
- **Owner:** 0xC4Cf88b691D9b820040d861954d32e0C5f4538b7
- **Cred Score:** 25 (JUNK tier — normal for fresh mint)
- **Mint Origin:** AGENT_SIWA
- **Minted At:** 2026-05-05T20:35:13.000Z
- **Transaction:** `0x97bb...d3` (redacted)
- **Explorer:** https://basescan.org/token/0x2e3B541C59D38b84E3Bc54e977200230A204Fe60?a=1416
- **Public Profile:** https://helixa.xyz/agent/1416

**How it was minted:**
The Helixa API `/api/v2/mint` endpoint was returning 504 Gateway Timeout, so minting was done via direct contract interaction using viem:
- Contract: `0x2e3B541C59D38b84E3Bc54e977200230A204Fe60`
- Function: `mint(address,string,string,bool)`
- Cost: **0 ETH** (current promotion — stats endpoint shows `mintPrice: "0.0"`)
- No USDC or gas fees required

**Wallet used:**
- Address: 0xC4Cf88b691D9b820040d861954d32e0C5f4538b7
- Seed: `[REDACTED-WALLET-SEED]`
- Private Key: `[REDACTED-HELIXA-PRIVATE-KEY]`

**Note on existing ManteClaw agents:**
There are 5 previous "ManteClaw" mints (token IDs 1411-1415) with framework "custom" and cred scores 15-31. These appear to be from the pre-wipe era. Our new mint is token ID 1416 with framework "openclaw".

**API update attempts:**
The Helixa API POST endpoints (`/api/v2/mint`, `/api/v2/agent/{id}/update`) are experiencing 504 Gateway Timeout issues. Direct contract interaction works fine. Profile updates may need to be retried later when the API stabilizes.

---

## Neynar (Farcaster API) — ⏳ REQUIRES MANUAL SIGNUP

**Blocker:** Neynar developer portal requires email verification (6-digit code sent via email). This cannot be fully automated in a headless environment.

**What was attempted:**
1. ✅ Checked workspace for existing Neynar API keys — none found
2. ✅ Confirmed wallet `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7` has no existing Farcaster identity (FID)
3. ✅ Searched for alternative signup methods (x402 micropayments, CLI tools) — none bypass the email requirement for write operations
4. ❌ Browser automation at dev.neynar.com reached the email verification step but cannot receive the code

**What you need to do:**

### Step 1: Get Neynar API Key
1. Go to https://dev.neynar.com
2. Enter your email address
3. Check your email for a 6-digit verification code
4. Complete signup
5. Copy your API key from the dashboard

### Step 2: Create a Farcaster Identity (FID)
Options:
- **Option A (Neynar managed):** Use Neynar's account registration API — requires app wallet + API key
- **Option B (Self-custody):** Create a Farcaster account via https://warpcast.com/ with your wallet, then link to Neynar
- **Option C (Agent-specific):** Use Neynar's `register-new-user` endpoint with an app wallet

### Step 3: Create a Signer
1. In the Neynar dev portal, go to Signers section
2. Create a managed signer (easiest — Neynar handles keys)
3. Copy the `signerUuid`

### Step 4: Post a Test Cast
Once you have the API key and signer UUID, run:
```bash
export NEYNAR_API_KEY="your_key"
export NEYNAR_SIGNER_UUID="your_signer_uuid"

# Post a cast
curl -X POST "https://api.neynar.com/v2/farcaster/cast" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $NEYNAR_API_KEY" \
  -d '{
    "signer_uuid": "'"$NEYNAR_SIGNER_UUID"'",
    "text": "Base AI agents are building autonomous earning lanes. Epoch's running. I'm mining. ⚡"
  }'
```

**Neynar Resources:**
- Docs: https://docs.neynar.com
- API Reference: https://docs.neynar.com/reference
- Free tier: 300 requests/minute, no credit card required
- x402 support: Some APIs now support USDC micropayments without API key

---

## Files Updated
- `TOOLS.md` — Added Helixa agent identity details
- `memory/2026-05-06.md` — Added Helixa mint + Neynar status

## Temporary Scripts Created (can be cleaned up)
- `/root/.openclaw/workspace/manteclaw/helixa-mint-test.cjs`
- `/root/.openclaw/workspace/manteclaw/helixa-mint-viem.mjs`

## Summary

| Service | Status | Details |
|---------|--------|---------|
| Helixa Identity | ✅ **MINTED** | Token #1416, Cred Score 25, free mint |
| Helixa API | ⚠️ Unstable | 504 timeouts on POST endpoints |
| Neynar API Key | ❌ **NEEDED** | Requires email signup at dev.neynar.com |
| Farcaster Identity | ❌ **NEEDED** | No FID exists for wallet |
| Neynar Signer | ❌ **NEEDED** | Create after getting API key |
| Test Cast Posted | ❌ **BLOCKED** | Need API key + signer + FID first |

**Next action for user:** Complete Neynar signup at https://dev.neynar.com and share the API key + signer UUID. Then I can immediately post the test cast to Farcaster.
