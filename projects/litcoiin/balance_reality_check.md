# Litcoiin Reality Check Report — 2026-05-14

## Findings

### Token Contract Search
- **Searched:** "LITCOIN token Base L2", "Litcoiin ERC20 contract"
- **Result:** No LITCOIN ERC-20 token contract found on Base Mainnet
- **BaseScan:** No token named "LITCOIN", "LIT", or "Litcoiin" registered

### Conclusion
**LITCOIN appears to be OFF-CHAIN POINTS, not an ERC-20 token.**

The 40,372 "LITCOIN" in `total_earned` is likely:
- Coordinator-side accounting (in-app credits)
- Not backed by on-chain tokens
- Not transferable or tradeable
- Value depends entirely on the Litcoiin platform's redemption policy

### Implications
1. **40K LITCOIN may have $0 real value** if not redeemable
2. The "claim" mechanism may just be an in-app leaderboard update
3. Need to verify: Can LITCOIN be swapped, staked, or redeemed for anything?

### Recommended Actions
1. **Check Litcoiin app/dashboard** for redemption options
2. **Ask in Litcoiin Discord/community** what LITCOIN actually is
3. **Verify claim mechanism** — does claiming actually move tokens on-chain?
4. **If vapor:** Consider miner time better spent on real-earning lanes

### Current Status
- Session tracker: 40,372 LITCOIN (22,608 rounds, 1.79 avg)
- On-chain balance: 0 (confirmed via Bankr API)
- **Verdict: Off-chain points system, not a real token.**

---
Epoch's running. But is it earning? ⚡
