# Manteclaw

Autonomous Litcoiin miner on Base L2. Specializes in crypto automation, research, and Base L2 operations.

## Getting Started

```bash
cd manteclaw
npm install
```

### Configuration

Edit `.env` and set your 12-word mnemonic phrase.

For on-chain registration, also set `REGISTRATION_PRIVATE_KEY` and `PINATA_JWT`.

### Running

```bash
# Development mode with hot-reload
npm run dev

# Production
npm start
```

## Agent Details

| Property | Value |
|----------|-------|
| **Name** | Manteclaw |
| **Skills** | automation, research, base-l2, crypto-mining, python, send_usdc, send_eth |
| **Payments** | Enabled (x402) |
| **Send Payments** | Enabled (USDC/ETH on Base) |
| **Registration** | Included |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MNEMONIC` | Yes | Agent wallet seed phrase |
| `BASE_RPC_URL` | For send payments | Base RPC endpoint (default: https://mainnet.base.org) |
| `REGISTRATION_PRIVATE_KEY` | For registration | Wallet paying gas |
| `PINATA_JWT` | For registration | IPFS metadata upload |

## Resources

- [SDK Docs](https://www.npmjs.com/package/@openagentmarket/nodejs)
- [Explorer](https://8004agents.ai)
- [GitHub](https://github.com/openagentmarket)