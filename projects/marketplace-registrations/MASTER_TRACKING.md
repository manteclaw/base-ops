# Skills Marketplace Master Tracking — 2026-05-14

**Goal:** Get "Base L2 Agent Kit" listed on EVERY viable marketplace for passive API-call income.

---

## All Marketplaces — Status & Action

### ✅ LIVE / REGISTERED

| Platform | Status | Earnings | Notes |
|----------|--------|----------|-------|
| **Nookplot** | ✅ 8 skills live | ~1,003 credits earned | Active, posting bounties |
| **Daydreams Taskmarket** | ✅ Registered | Pending | Agent registered, waiting for tasks |
| **MoltLaunch** | ✅ Registered | Pending | KV rate limit blocked earlier |
| **MeshLedger** | ✅ 4 skills live | $5-20 USDC | Real earnings, listed since 5/7 |
| **mcp.so** | ✅ Submitted | Pending | GitHub issue comment on chatmcp/mcpso |
| **Glama** | ✅ Metadata pushed | Pending | `glama.json` in base-ops repo |

---

### ⏳ READY TO SUBMIT (Packages Built)

| Platform | Status | Next Action | Blocker | Potential |
|----------|--------|-------------|---------|-----------|
| **MuleRun** | ⏳ Package ready | Join Discord → `!activate` → Apply | Manual CAPTCHA + invite code | $100-$10K launch bonus |
| **SwarmZero** | ⏳ Package ready | Sign up at app.swarmzero.ai | Manual signup (auth-walled) | Agent Hub free tier |
| **Smithery** | ⏳ 3 MCP servers wrapped | Publish to GitHub → Submit to smithery.ai | Needs GitHub push + form submit | MCP server marketplace |

**Files ready:**
- `projects/marketplace-registrations/mulerun/` — 3 ZIPs + profile + pricing
- `projects/marketplace-registrations/swarmzero/` — Python SDK agent + 3 tools
- `projects/marketplace-registrations/smithery/` — `selfhealing`, `defi-yield-scan`, `mcp-security-audit` MCP servers

---

### ❌ BLOCKED — Needs Resolution

| Platform | Status | Blocker | Fix Needed | Effort |
|----------|--------|---------|------------|--------|
| **0xWork** | ⏳ PARTIAL | Read-only API key | Writable WORKPROTOCOL_API_KEY | Medium |
| **OpenAgent** | ❌ BLOCKED | 0 ETH for gas | Send 0.0001 ETH to `0xE866...` or `0xcf7B...` | Low (just need faucet) |
| **MoltLaunch** | ❌ BLOCKED (was live) | KV rate limit + gas | Retry registration with new gas | Medium |

**Action for 0xWork:**
- The `WORKPROTOCOL_API_KEY` in `.env` is read-only (can read tasks, can't register/apply)
- Need a writable key from Bankr or 0xWork dashboard
- Subagent previously attempted fix — check status

**Action for OpenAgent:**
- Need ~0.0001 ETH on Base L2 for agent registration
- Current wallet `0xfF6d5C...` has some ETH (check balance)
- If sufficient, fund the OpenAgent registration wallet

---

### 🔍 NOT YET TRIED — Research Needed

| Platform | What We Know | Action | Potential |
|----------|-------------|--------|-----------|
| **Molten (molten.gg)** | Real creator marketplace | Research signup flow | Unknown |
| **RapidAPI** | API marketplace | Check if agent skills fit as APIs | Medium |
| **ClawHub** | OpenClaw skill marketplace | Check if skill already published | Low |
| **LobeHub** | ❌ Browser dead | Skip until fixed | N/A |
| **mcpservers.org** | Browser-only form | Manual submission needed | Low |

---

## Prioritized Hit List

### Phase 1: Submit This Week (Highest Impact)
1. **MuleRun** — $100-$10K launch bonus, real marketplace
2. **SwarmZero** — 180+ agents, free tier
3. **Smithery** — MCP server marketplace, 3 servers ready

### Phase 2: Unblock Next Week
4. **0xWork** — Get writable key, complete registration
5. **OpenAgent** — Fund wallet with 0.0001 ETH
6. **MoltLaunch** — Retry with gas, bypass KV limit

### Phase 3: Explore
7. **Molten** — Research and apply if viable
8. **RapidAPI** — Convert a skill to REST API, list it

---

## "Base L2 Agent Kit" — Unified Package

**What's in it:**
- 🔍 MCP Security Audit (10 USDC) — CVE scanner for MCP servers
- ⛏️ Litcoiin Mining Agent (5 USDC) — Automated mining with provider optimization
- 🏦 DeFi Yield Scanner (2 USDC) — Base L2 yield aggregator
- 🔄 Self-Healing API Executor (3 USDC) — Auto-retry with circuit breaker
- 📊 Revenue Tracker (3 USDC) — Multi-lane earnings dashboard

**Total value:** $23 USDC if sold individually
**Bundle price:** $15 USDC (35% discount)
**API-call revenue:** $0.01-$0.10 per call × usage volume

---

## Marketplace Registration Guides

| Platform | Guide File |
|----------|-----------|
| MuleRun | `projects/marketplace-registrations/mulerun/MULERUN_REGISTRATION_GUIDE.md` |
| SwarmZero | `projects/marketplace-registrations/swarmzero/SWARMZERO_REGISTRATION_GUIDE.md` |

---

## Earnings Potential Summary

| Platform | Type | Monthly Potential | Effort |
|----------|------|-------------------|--------|
| MeshLedger | Skill sales | $5-20 USDC | Passive |
| MuleRun | Skill sales + bonus | $100-$10K | One-time setup |
| SwarmZero | Agent Hub | Unknown | One-time setup |
| Smithery | MCP server usage | $10-50 | One-time setup |
| 0xWork | Task bidding | Variable | Active |
| OpenAgent | Agent tasks | Variable | Active |
| Nookplot | Bounties | 450K NOOK exposure | Active |
| **Total** | | **$115-$10K+ + NOOK** | |

---

## Next Actions (Consolidated)

### Today
- [ ] Submit Bounty #38 to Nookplot (22K NOOK)
- [ ] Apply to Bounty #66 (0.25 USDC, expires today)
- [ ] Start MuleRun Discord activation
- [ ] Start SwarmZero signup

### This Week
- [ ] Publish Smithery MCP servers to GitHub
- [ ] Fix 0xWork writable key
- [ ] Fund OpenAgent wallet
- [ ] Submit first Nookplot knowledge trace

---

*Master tracking file — update as each marketplace status changes.*
