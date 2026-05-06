# Base L2 Arbitrage Bot

Cross-DEX arbitrage scanner for Base mainnet. Monitors Uniswap V3, Aerodrome, and BaseSwap for price discrepancies.

## Setup

```bash
cd projects/arbitrage
pip install -r requirements.txt

# Set environment variables
export ALCHEMY_API_KEY="your_alchemy_key"
export PRIVATE_KEY="0x..."  # Optional — only for live execution
export WALLET_ADDRESS="0x..."
```

## Usage

### Dry run (monitor only — safe)
```bash
python arbitrage_bot.py
```

### Single scan
```bash
python arbitrage_bot.py --scan
```

### Live execution (DANGER — requires PRIVATE_KEY)
```bash
python arbitrage_bot.py --execute
```

## How It Works

1. **Price Monitor** (`price_monitor.py`) queries DEX routers via Alchemy RPC
2. **Arbitrage Engine** compares prices across DEXes for the same pair
3. **Profit Calculation** factors in gas cost (Base is ~0.1 gwei, ~$0.01/swap)
4. **Execution** (optional) submits swap transactions

## Supported Pairs

- WETH/USDC
- WETH/DAI
- USDC/DAI
- WETH/CBETH

## Architecture

| File | Purpose |
|------|---------|
| `config.json` | DEX addresses, token addresses, thresholds |
| `price_monitor.py` | RPC queries to DEX quoters |
| `arbitrage_bot.py` | Main loop + opportunity detection |
| `executor.py` | Transaction builder (WIP) |

## ⚠️ Safety

- **Default mode is dry run** — no transactions sent
- Live execution requires `PRIVATE_KEY` env var
- Start with `--scan` to verify before running live
- Bot skips opportunities below `min_profit_usd` (default $0.50)
