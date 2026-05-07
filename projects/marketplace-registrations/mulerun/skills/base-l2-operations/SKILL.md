# Base L2 Operations

Base L2 DeFi automation toolkit for autonomous agents.

## Description
Execute gas-optimized transactions on Base L2: swap, stake, bridge, and yield-farm with circuit breaker protection.

## When to Use
- User asks about Base L2 operations
- DeFi yield optimization needed
- Token swaps or bridging required
- Treasury management on Base

## Instructions

### 1. Setup Connection
```python
from web3 import Web3

rpc_url = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), "Base RPC unreachable"
```

### 2. Gas Optimization
- Always check gas price before tx
- Use EIP-1559: maxFeePerGas = baseFee * 1.2 + maxPriorityFee
- Batch operations when possible
- Skip if gas > 50 gwei

### 3. Yield Scanning
Check these protocols on Base:
- **Aave V3** — aUSDC, variable borrow
- **Morpho** — optimized lending vaults
- **Zyfai** — automated yield (if available)
- **Uniswap V3** — concentrated liquidity

### 4. Safety Rules
- Never spend >10% of treasury in one tx
- Circuit breaker: pause if 3 consecutive failures
- Log all tx hashes for audit trail
- Verify contract addresses against official sources

## Scripts
- `gas_optimizer.py` — Calculate optimal gas params
- `yield_scanner.py` — Scan Base protocols for best APY
- `abi_fetcher.py` — Fetch verified contract ABIs from Basescan

## References
- `base_chain_guide.md` — Base L2 architecture and key contracts
