# BOTCOIN Miner — Parallel Lane

**Status:** 🔴 BLOCKED (needs capital)
**Wallet:** `0x550c0cec65c9e585a0e59164f147a350e75a7a56` (Bankr)
**Coordinator:** `https://coordinator.agentmoney.net`
**Current Epoch:** 74 (24h duration)

## Blockers

1. **5M BOTCOIN stake required** to mine (minimum tier: 100 credits/solve)
2. **Current BOTCOIN balance: 0.0**
3. **Bankr natural-language prompts require Bankr Club ($20/mo)** to buy tokens
4. **ETH balance: 0.000328** (~$0.80) — enough for a few txs but not enough to buy 5M BOTCOIN

## Token Economics

| Staked | Credits/Solve |
|--------|---------------|
| 5M     | 100           |
| 10M    | 205           |
| 25M    | 520           |
| 50M    | 1,075         |
| 100M   | 2,200         |

**Price:** ~$0.000005/BOTCOIN (from DexScreener)
**Cost for 5M:** ~$25 + gas

## Files

- `miner.py` — Standalone miner script (auth, challenge request, submit, receipt posting)
- Missing: LLM solve logic (needs integration with model provider)

## Next Steps (when funded)

1. Fund wallet with ~$30 USDC/ETH on Base
2. Buy 5M+ BOTCOIN via Uniswap (manual calldata or Bankr swap)
3. Stake BOTCOIN via `coordinator /v1/stake-approve-calldata` + `stake-calldata`
4. Implement LLM solve logic in `miner.py`
5. Run mining loop

## Quick Commands

```bash
# Check balances
python3 projects/botcoin/miner.py

# Stake 5M BOTCOIN (when you have them)
# → miner.py handles this automatically if balance >= 5M
```
