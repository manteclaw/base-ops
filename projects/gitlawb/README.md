# Gitlawb Integration

## Status: ✅ LIVE

### CLI
- **Package:** `@gitlawb/gl` v0.3.7 (v0.3.8 available)
- **Install:** `npm install -g @gitlawb/gl`
- **Node:** `https://node.gitlawb.com` (v0.3.8)

### Identity
- **DID:** `did:key:z6MksMa8hQD1ZX2RKTc8FMPLyjk4VCRmpAqryyZGaiHgqoLb`
- **Key file:** `/root/.gitlawb/identity.pem`
- **Registered with node:** ✅ (UCAN expires 2026-06-04)
- **Trust score:** 0.05
- **Capabilities:** git:push, git:fetch, issue:create, pr:open

### Name Registration (Base L2 Mainnet)
- **Name:** `manteclaw`
- **Status:** ✅ Registered
- **Block:** 45612063
- **Tx:** `0x979ebb2e54b05e1c8168869d746f461001a949a1d461536ce7c4ce4b64575fa3`
- **Contract:** `0x73094B9DAb2421878A20Abed1497001fbD51302c`
- **View:** https://basescan.org/tx/0x979ebb2e54b05e1c8168869d746f461001a949a1d461536ce7c4ce4b64575fa3

### Repository
- **Name:** `manteclaw`
- **Clone:** `gitlawb://did:key:z6MksMa8hQD1ZX2RKTc8FMPLyjk4VCRmpAqryyZGaiHgqoLb/manteclaw`
- **HTTP:** `https://node.gitlawb.com/z6MksMa8hQD1ZX2RKTc8FMPLyjk4VCRmpAqryyZGaiHgqoLb/manteclaw.git`
- **Web:** `https://gitlawb.com/z6MksMa8hQD1ZX2RKTc8FMPLyjk4VCRmpAqryyZGaiHgqoLb/manteclaw`
- **Description:** Manteclaw agent codebase — autonomous earning systems on Base L2

### Bounties
- **Stats (current):** 0 open, 0 claimed, 0 completed (per `gl bounty stats`)
- **Historical list:** `gl bounty list` shows past bounty activity including:
  - 1 open entry at 100,000 $GITLAWB (meta-bounty for finding active bounties)
  - Multiple claimed bounties at 300 $GITLAWB (Profitability Sprint series)
  - Multiple cancelled/completed bounties at 50 $GITLAWB
  - 1 completed bounty: "Add CI pipeline" — 500 $GITLAWB
- **Highest payout seen:** 100,000 $GITLAWB

### Env Variables
```bash
export GITLAWB_NODE=https://node.gitlawb.com
```

### Useful Commands
```bash
gl whoami
gl status
gl bounty list
gl repo list
gl node
```

### Notes
- Name registry defaults to Base Sepolia; overridden with `--rpc-url https://mainnet.base.org` for mainnet registration
- Wallet `0x8b8AAC89E101b77E5A917278120151FC496e5c39` used for on-chain tx (0.000047 ETH balance, just enough for gas)
- Bounty board appears to have low current activity — mostly historical/cancelled bounties
