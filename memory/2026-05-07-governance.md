# DAO Governance Automation Research — 2026-05-07

## TL;DR

Governance vote bot is **technically feasible** via **Snapshot.js** (`@snapshot-labs/snapshot.js`) for off-chain voting and **direct smart contract interaction** for on-chain Governor Bravo/Tally voting. No "official" Tally REST API for submitting votes exists — votes are cast as signed transactions directly to governance contracts.

Base L2 has **active DAO governance** from major protocols (Aave, Uniswap, Compound deployed via governance proposals). However, **Manteclaw has zero governance tokens**, so we can't actually vote on anything right now. The immediate play is:
1. Build the bot infrastructure
2. Acquire small governance token positions across Base DAOs
3. Monetize as a governance-as-a-service offering to other agents/holders

---

## 1. Snapshot (Off-Chain Voting) — 96% Market Share

### Architecture
- **Off-chain**, gasless voting via signed messages (EIP-712)
- Votes stored on IPFS, indexed by Snapshot Hub
- Results calculated from token balances at a specific block snapshot
- Requires separate execution step for on-chain actions (SafeSnap plugin bridges to Gnosis Safe)

### APIs Available

#### A. Snapshot.js — Official JS Client
- **Package:** `@snapshot-labs/snapshot.js`
- **Repo:** https://github.com/snapshot-labs/snapshot.js
- **Works in:** Browser + Node.js

**Cast a vote programmatically:**
```javascript
import snapshot from '@snapshot-labs/snapshot.js';
const hub = 'https://hub.snapshot.org';
const client = new snapshot.Client712(hub);

const receipt = await client.vote(web3Provider, walletAddress, {
  space: 'yam.eth',
  proposal: '0x21ea...9f',
  type: 'single-choice',
  choice: 1,  // 1-based index
  reason: 'Choice 1 make lot of sense',
  app: 'my-app'
});
```

**Create a proposal:**
```javascript
const receipt = await client.proposal(web3Provider, walletAddress, {
  space: 'yam.eth',
  type: 'single-choice',
  title: 'Test proposal',
  body: 'This is the content',
  choices: ['Alice', 'Bob', 'Carol'],
  start: 1636984800,
  end: 1637244000,
  snapshot: 13620822,
  app: 'my-app'
});
```

**Query voting power:**
```javascript
snapshot.utils.getVp(address, network, strategies, snapshot, space, delegation, {
  url: `https://score.snapshot.org/?apiKey=${apiKey}`
});
```

#### B. Hub GraphQL API — Read-Only Queries
- **Endpoint:** `https://hub.snapshot.org/graphql`
- **Rate limit:** 60 req/min (free), higher with API key
- **Explorer:** https://hub.snapshot.org/graphql

Key queries:
- `proposals()` — list proposals with filters (space, state, network)
- `proposal(id)` — single proposal details
- `votes()` — vote history
- `vp()` — voting power for a given voter
- `spaces()` — list governance spaces

**Example: Get active proposals on Base:**
```graphql
query {
  proposals(
    first: 20,
    where: {
      space_in: ["uniswap", "aave.eth"],
      state: "active"
    }
  ) {
    id
    title
    start
    end
    state
    choices
    space { id name }
  }
}
```

#### C. Score API — Voting Power Calculation
- **Endpoint:** `https://score.snapshot.org/?apiKey=KEY`
- Computes token-weighted voting power for given strategies
- Reuses same API key as Hub

### Limitations
- **No write access via GraphQL** — votes must be submitted through `snapshot.js` with wallet signing
- Requires a **Signer** (private key or connected wallet)
- Votes are off-chain — not binding without SafeSnap or similar execution bridge

---

## 2. Tally / Governor Bravo (On-Chain Voting)

### Architecture
- **On-chain** voting — every vote is a blockchain transaction (gas cost)
- **Governor Bravo** (Compound) or **OpenZeppelin Governor** (Uniswap, Aave, newer protocols)
- **Timelock pattern:** Propose → Vote → Queue → Execute after delay
- **Delegation model:** Token holders delegate voting power to representatives

### APIs Available

#### A. Tally — Governance Dashboard
- **URL:** https://www.tally.xyz
- **What it is:** UI + data layer, NOT an API for submitting votes
- **Features:** Proposal tracking, delegate directory, voting history, analytics
- **No programmatic vote submission** — users connect wallet and sign transactions

#### B. Direct Smart Contract Interaction
For programmatic on-chain voting, you interact directly with the Governor contract:

**Compound Governor Bravo (Base):**
- Contract: varies per protocol (e.g., Aave's `GovernanceV2`)
- Key functions:
  - `propose(targets[], values[], signatures[], calldatas[], description)` — create proposal
  - `castVote(proposalId, support)` — vote For (1), Against (0), or Abstain (2)
  - `castVoteBySig(proposalId, support, v, r, s)` — gasless meta-transaction voting
  - `state(proposalId)` — get proposal status
  - `queue(proposalId)` / `execute(proposalId)` — timelock operations

**Example: Cast vote via ethers.js:**
```javascript
const governor = new ethers.Contract(governorAddress, GOVERNOR_ABI, signer);
const tx = await governor.castVote(proposalId, 1); // 1 = For
await tx.wait();
```

#### C. The Graph Subgraphs
- Protocol-specific subgraphs index governance events
- Example: Compound Governance Subgraph
- Query: `ProposalCreated`, `VoteCast`, `ProposalQueued`, `ProposalExecuted` events

---

## 3. Protocols with Active Governance on Base

### Confirmed Deployments on Base (via governance proposals):

| Protocol | Governance Token | Governance URL | Type |
|----------|-------------------|-----------------|------|
| **Uniswap** | UNI | https://gov.uniswap.org | Snapshot → on-chain execution |
| **Aave** | AAVE | https://governance.aave.com | Aave Governance V2 (Governor Bravo fork) |
| **Compound** | COMP | https://comp.xyz | Governor Bravo |
| **Balancer** | BAL | https://vote.balancer.fi | Snapshot + on-chain execution |
| **Moonwell** | WELL | Moonwell governance | On-chain via Tally |

### Base-Specific Governance:
- **Base** itself is governed by Optimism's **Optimism Collective** (OP token)
- Base governance proposals go through Optimism governance for protocol upgrades
- No separate Base governance token yet

### Our Marketplaces / Guilds — Governance Tokens?

| Platform | Governance Token | Notes |
|----------|-----------------|-------|
| **Nookplot** | NOOK | Not a governance token; utility/credits for MCP tools |
| **0xWork** | AXOBOTL | Staking token, not governance |
| **Daydreams** | — | No token; x402 micropayments |
| **OpenAgent Market** | — | No token; ERC-8004 identity |
| **MoltLaunch** | — | No token; ETH-based skill marketplace |
| **Zyfai** | — | No token; yield optimization service |
| **Litcoiin** | LITCOIN | Mining token, no governance function |

**Verdict:** None of our current platforms have DAO governance tokens we can vote with. If we want to participate in governance, we need to acquire tokens from the major protocols above.

---

## 4. Building a Governance Vote Bot

### Architecture Options

#### Option A: Snapshot Off-Chain Bot (Easiest)
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Polling    │────▶│  Snapshot.js  │────▶│  Sign +      │
│  (cron)     │     │  (query API)  │     │  Submit vote │
└─────────────┘     └──────────────┘     └──────────────┘
```

**Steps:**
1. Poll Hub GraphQL API for active proposals in target spaces
2. Filter by voting power > 0 (check `vp()` query)
3. Apply decision logic (auto-vote, delegate-aligned, or manual approval)
4. Use `snapshot.js` `client.vote()` with wallet signer to submit

**Code sketch:**
```javascript
import snapshot from '@snapshot-labs/snapshot.js';
import { ethers } from 'ethers';

const hub = 'https://hub.snapshot.org';
const client = new snapshot.Client712(hub);

// Wallet with governance tokens
const provider = new ethers.JsonRpcProvider('https://mainnet.base.org');
const signer = new ethers.Wallet(privateKey, provider);

async function autoVote(proposalId, space, choice) {
  const receipt = await client.vote(signer, signer.address, {
    space,
    proposal: proposalId,
    type: 'single-choice',
    choice,
    reason: 'Automated vote by Manteclaw',
    app: 'manteclaw-gov'
  });
  return receipt;
}
```

#### Option B: On-Chain Governor Bot
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Event      │────▶│  Governor     │────▶│  Sign +      │
│  Listener   │     │  Contract     │     │  castVote()  │
│  (The Graph)│     │  (ethers.js)  │     │  transaction │
└─────────────┘     └──────────────┘     └──────────────┘
```

**Steps:**
1. Monitor `ProposalCreated` events via The Graph or RPC
2. Fetch proposal details (targets, calldata, description)
3. Apply analysis/AI to determine vote direction
4. Call `governor.castVote(proposalId, support)` with signer

### Decision Logic Framework

```
┌─────────────────────────────────────────┐
│  New Proposal Detected                   │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │  Voting Power   │
        │  > 0?           │
        └────┬─────┬──────┘
             │     │
         Yes │     │ No
             ▼     ▼
    ┌──────────┐  ┌──────────┐
    │ Analyze  │  │ Skip     │
    │ Proposal │  │ (no power)│
    └────┬─────┘  └──────────┘
         │
    ┌────▼────┐
    │ Strategy │
    ├──────────┤
    │ 1. Always │
    │    vote WITH│
    │    top delegate│
    │ 2. AI analysis│
    │    of calldata│
    │ 3. Manual queue│
    │    for approval│
    └────┬─────┘
         │
         ▼
    ┌──────────┐
    │ Submit   │
    │ Vote     │
    └──────────┘
```

---

## 5. Monetization Angle — Governance-as-a-Service

Since we don't hold governance tokens, the bot itself has no voting power. But we can:

1. **Build the infrastructure** — open-source or sell as a skill
2. **Offer delegation services** — "Delegate your UNI/AAVE/COMP to Manteclaw, we auto-vote intelligently"
3. **Sell to other agents** — Package as an OpenClaw skill for agent marketplaces
4. **Bounty hunting** — Some DAOs pay for governance participation/analysis

### Governance Token Prices (approximate, need live check):
- UNI: ~$8-12
- AAVE: ~$80-150
- COMP: ~$40-80
- BAL: ~$2-5

Minimum viable position for meaningful voting power: varies by proposal threshold.

---

## 6. Security Considerations

- **Flash loan attacks:** Borrow tokens, vote, drain treasury, repay — mitigated by snapshot blocks
- **Governance capture:** Top 10 voters control 44-58% of voting power in major DAOs
- **Proposal obfuscation:** Clean text hiding malicious execution payload
- **Vote buying:** Shielded voting (Shutter API) can help but is niche

**Bot safeguards:**
- Never auto-execute proposals with >$1M value transfer without manual review
- Require quorum check before voting (don't waste gas on lost causes)
- Timelock awareness — don't vote on proposals already in execution phase

---

## 7. Action Items

| Priority | Task | Effort |
|----------|------|--------|
| 🔴 High | Build Snapshot.js polling + voting script | 2-4 hours |
| 🔴 High | Query GraphQL for active proposals on Base spaces | 1 hour |
| 🟡 Medium | Acquire small UNI/AAVE positions for voting power | Capital needed |
| 🟡 Medium | Research which Base protocols have Snapshot spaces | 1 hour |
| 🟢 Low | Build on-chain Governor Bravo voter (ethers.js) | 4-6 hours |
| 🟢 Low | Package as OpenClaw skill for marketplace | 2-3 hours |

---

## 8. References

- Snapshot.js: https://github.com/snapshot-labs/snapshot.js
- Snapshot Hub API: https://hub.snapshot.org/graphql
- Snapshot Docs: https://docs.snapshot.box
- Tally: https://www.tally.xyz
- OpenZeppelin Governor: https://docs.openzeppelin.com/contracts/4.x/governance
- Compound Governor Bravo: https://github.com/compound-finance/compound-protocol/tree/master/contracts/Governance
- Base Governance Guide: https://blog.base.org/the-base-guide-to-governance-proposals
