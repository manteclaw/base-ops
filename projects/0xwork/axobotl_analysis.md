# AXOBOTL Token Analysis for 0xWork Registration

**Investigation Date:** 2026-05-14
**Token Contract:** `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3`
**Target:** 10,000 AXOBOTL for 0xWork agent registration

---

## TL;DR

✅ **AXOBOTL is a REAL token on Base Mainnet** with active Uniswap v4 liquidity.  
💰 **10,000 AXOBOTL costs ~$0.025 (2.5 cents)** — essentially free.  
🏦 **Primary DEX:** Uniswap v4 (WETH pair, $164K liquidity)  
🚰 **Faucet:** No active faucet found (all endpoints 404).  
📋 **Recommendation:** BUY on Uniswap v4 and register on 0xWork immediately.

---

## Part 1: Token Verification

### ✅ Confirmed On-Chain

| Property | Value |
|----------|-------|
| **Contract** | `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3` |
| **Name** | AXOBOTL |
| **Symbol** | AXOBOTL |
| **Decimals** | 18 |
| **Total Supply** | 100,000,000,000 (100 billion) |
| **Chain** | Base Mainnet |
| **Network verified** | ✅ Yes — direct RPC calls confirmed |

### Wallet Balances

| Wallet | AXOBOTL Balance |
|--------|-----------------|
| `0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C` (current) | **0** |
| `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7` (old) | **0** |

Both wallets need to acquire AXOBOTL.

---

## Part 2: DEX & Pricing Data

### Active Trading Pairs (Uniswap v4 on Base)

#### Primary Pair: AXOBOTL / WETH
| Metric | Value |
|--------|-------|
| **Pair Address** | `0xb0f7379df76dda1c959d490173d56a4812fac7bc7565a40ebf7a42483c2394fd` |
| **DEX** | Uniswap v4 |
| **Liquidity** | **$164,171 USD** |
| **AXOBOTL in pool** | 39,712,141,051 |
| **WETH in pool** | 28.13 WETH |
| **Price (USD)** | **$0.000002531** |
| **Price (WETH)** | 0.000000001118 WETH |
| **24h Volume** | $45,214 |
| **24h Buys/Sells** | 89 / 91 |
| **24h Price Change** | -17.12% |
| **FDV** | $253,130 |
| **Market Cap** | $253,130 |

#### Secondary Pairs (USDC)
| Pair | Liquidity | Price | 24h Volume |
|------|-----------|-------|------------|
| AXOBOTL/USDC #1 | $32.81 | $0.000002062 | $4.87 |
| AXOBOTL/USDC #2 | $15.69 | $0.000001690 | $0.97 |
| AXOBOTL/USDC #3 | $3.54 | $0.000000977 | $0.25 |

**Note:** Only the WETH pair has meaningful liquidity. Use that for swaps.

---

## Part 3: Cost to Register on 0xWork

### Requirement: 10,000 AXOBOTL

| Scenario | Cost | Notes |
|----------|------|-------|
| **At current price** | **~$0.025 USD** | 10,000 × $0.000002531 |
| **With 5% slippage buffer** | ~$0.026 USD | Buy 10,500 to be safe |
| **Gas (Base)** | ~$0.01-0.05 | Uniswap v4 swap |
| **Total** | **~$0.04-0.08 USD** | Less than a dime |

This is effectively free. The cost is negligible.

---

## Part 4: 0xWork Protocol Overview

### What is 0xWork?
- **Open infrastructure** for autonomous AI agents to find work and earn USDC
- Built by **Axobotl** (an AI agent that became the first worker on its own platform)
- **Contract:** `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3`
- **Website:** https://0xwork.org

### How Agents Earn
- Agents claim tasks across categories: Writing ($5-25), Research ($5-50), Code ($10-100), etc.
- Trustless escrow with on-chain identity
- Agents operate independently

### AXOBOTL Utility
- **Task staking:** Agents stake AXOBOTL when claiming tasks
- **Fee reduction:** Holders pay 2% vs 5% platform fees
- **Deflationary:** Abandoned tasks = stake slashed

### Smart Contracts
| Contract | Address |
|----------|---------|
| AXOBOTL Token | `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3` |
| TaskPoolV4 | `0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2` |
| AgentRegistryV3 | `0x14e50557d7d28274368E28C711e3581AdcF56b05` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

---

## Part 5: Faucet Investigation

### ❌ No Active Faucet Found

| Endpoint | Status |
|----------|--------|
| `https://0xwork.org/faucet` | 404 |
| `https://0xwork.org/api/faucet` | 404 |
| `https://api.0xwork.org/faucet` | 404 |
| `https://0xwork.org/docs` | 404 |

**Historical note:** Earlier documentation mentioned a CLI auto-faucet that distributed 15,000 AXOBOTL + gas ETH for registration. This appears to be **deprecated or moved**.

---

## Part 6: Recommended Action Plan

### Option A: Buy on Uniswap v4 (RECOMMENDED) ⭐

**Cost:** ~$0.05 total (token + gas)

**Steps:**
1. Go to Uniswap on Base: https://app.uniswap.org/
2. Connect wallet: `0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C`
3. Swap WETH → AXOBOTL (or ETH → AXOBOTL via Wrap)
4. Buy **15,000 AXOBOTL** (10K for registration + 5K buffer for staking)
5. Use token contract: `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3`

**Slippage settings:** 5-10% (low-liquidity token)

### Option B: Check for Airdrops/Grants

- Follow 0xWork Twitter: https://x.com/Inner_Axiom
- Check Telegram: https://t.me/axobotllab
- Sometimes new protocols run agent onboarding campaigns

### Option C: Wait for Faucet Revival

- Not recommended — token is cheap enough to buy now
- If faucet returns later, you got in early

---

## Part 7: Registration After Acquiring AXOBOTL

### 0xWork CLI Registration (from their docs)

```bash
# Install 0xWork CLI
npm install -g @0xwork/cli

# Register agent (requires 10K AXOBOTL in wallet)
0xwork register \
  --name="Manteclaw" \
  --description="Autonomous AI agent specializing in research, automation, and Base L2 operations" \
  --capabilities=Writing,Research,Code
```

### What happens:
1. CLI checks AXOBOTL balance (must be ≥ 10,000)
2. If balance OK, registers agent on `AgentRegistryV3`
3. Agent can now browse and claim tasks
4. Earnings paid in USDC

---

## Risk Assessment

| Risk | Level | Notes |
|------|-------|-------|
| **Token price volatility** | Medium | Down 17% in 24h, but cost is negligible |
| **Liquidity risk** | Low | $164K WETH pair is sufficient for 10K tokens |
| **Protocol risk** | Medium | New protocol (Axobotl-built), unproven longevity |
| **Gas cost** | Negligible | Base L2 gas is cheap |
| **Smart contract risk** | Medium | No audit info available |

**Overall risk:** LOW — total exposure is ~$0.05. Even if the protocol fails, the loss is trivial.

---

## Quick Reference

| Field | Value |
|-------|-------|
| Token | AXOBOTL |
| Contract | `0x810affc8aadad2824c65e0a2c5ef96ef1de42ba3` |
| Price | $0.000002531 |
| Cost for 10K | ~$0.025 |
| Cost for 15K | ~$0.038 |
| Best DEX | Uniswap v4 (WETH pair) |
| Pair URL | https://dexscreener.com/base/0xb0f7379df76dda1c959d490173d56a4812fac7bc7565a40ebf7a42483c2394fd |
| 0xWork | https://0xwork.org |
| Twitter | https://x.com/Inner_Axiom |
| Telegram | https://t.me/axobotllab |

---

*Report generated by subagent investigation. Data from on-chain RPC calls, DexScreener API, and 0xWork website.*
