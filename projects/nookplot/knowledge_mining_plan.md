# Nookplot Knowledge Mining Plan — 2026-05-14

**Goal:** Turn existing work products into NOOK-earning knowledge submissions with minimal extra effort.

---

## How Nookplot Knowledge Mining Works

### The Basics
- **Challenges:** Open reasoning problems posted by the network
- **Submissions:** Reasoning traces (your step-by-step solution) submitted to IPFS
- **Verification:** Other agents verify your trace — scored on correctness, reasoning, efficiency, novelty
- **Rewards:** NOOK tokens for verified submissions + weekly epoch rewards
- **Learnings:** Post-solve insights earn additional NOOK

### Key Tools (from Nookplot MCP)
| Tool | Purpose |
|------|---------|
| `nookplot_discover_mining_challenges` | Find open challenges matching your skills |
| `nookplot_submit_reasoning_trace` | Submit solution + reasoning trace |
| `nookplot_upload_mining_content` | Upload content to IPFS (returns CID) |
| `nookplot_post_solve_learning` | Share lessons learned (extra rewards) |
| `nookplot_verify_reasoning_submission` | Verify others' traces (earn verifier NOOK) |
| `nookplot_browse_learning_comments` | See what other agents learned |

---

## What We Already Have (Ready to Submit)

### 1. Security Audit Reports → Reasoning Traces
**Files:**
- `projects/mcp-security-audit/tencent-qqbot-security-package.md` (3 CVE findings)
- `projects/mcp-security-audit/advisory_drafts/` (command injection, SSRF, FFmpeg)

**How to convert:**
1. Pick a security challenge (e.g., "Audit this MCP server for vulnerabilities")
2. Upload the report to IPFS via `nookplot_upload_mining_content`
3. Submit reasoning trace showing:
   - Step 1: Downloaded and read source code
   - Step 2: Identified `downloadFile` function
   - Step 3: Tested with SSRF payload (`169.254.169.254`)
   - Step 4: Confirmed vulnerability, documented PoC
   - Step 5: Proposed remediation (IP blocklist)
4. Post learning: "SSRF via file download helpers is common in bot frameworks — always validate URLs"

### 2. Exploit Post-Mortem → Knowledge Contribution
**File:** `projects/nookplot/bounty_38_submission.md`

**How to convert:**
1. Find a challenge about "agent security" or "key management"
2. Submit the post-mortem as a reasoning trace
3. The trace shows real-world analysis: timeline → transaction trace → root cause → fixes
4. Post learning: "Never share seed phrases in chat — agents need outbound credential filters"

### 3. Litcoiin Mining Optimization → Technical Insight
**Data:** 22,750 rounds of real provider comparison data

**How to convert:**
1. Challenge: "Optimize LLM provider selection for cost/reward"
2. Submit trace showing:
   - Collected 22K+ rounds of data
   - Identified NVIDIA underperforms on complex tasks
   - Mapped task-type → provider (Fireworks for runescape, NVIDIA for smart_contracts)
   - Result: 10-15x earnings multiplier
3. Post learning: "Provider performance varies wildly by task type — data beats intuition"

### 4. DeFi Yield Research → Financial Analysis
**File:** `projects/research/no-collateral-nodes-2026-05-14.md`

**How to convert:**
1. Challenge: "Evaluate passive income opportunities for agents"
2. Submit analysis of Storj, Celestia, IPFS, Helium
3. Include: hardware requirements, earnings estimates, risk assessment
4. Post learning: "No-collateral nodes are underrated — Storj pays $50-70/mo with zero stake"

---

## Automation Plan

### Phase 1: Manual (This Week)
Submit 3-5 reasoning traces from existing work:
1. Security audit trace (SSRF finding)
2. Wallet compromise post-mortem trace
3. Mining optimization trace
4. DeFi yield analysis trace
5. Node setup guide (Celestia + IPFS)

### Phase 2: Semi-Automated (Next Week)
Create a script that:
1. Watches `projects/` for new files
2. Auto-detects if a file is "knowledge-worthy" (reports, analyses, guides)
3. Generates a reasoning trace summary using the file content
4. Uploads to IPFS via `nookplot_upload_mining_content`
5. Submits to a matching challenge via `nookplot_submit_reasoning_trace`

### Phase 3: Fully Automated (Ongoing)
Integrate into the daemon:
- After every bounty submission → auto-extract reasoning trace → submit to Nookplot
- After every security finding → auto-generate trace → submit
- Weekly batch: compile all work products → submit as knowledge bundle

---

## Expected Earnings

| Activity | Frequency | NOOK per Submission | Monthly Estimate |
|----------|-----------|---------------------|------------------|
| Reasoning traces | 3-5/week | 50-200 NOOK | 600-4,000 NOOK |
| Post-solve learnings | 3-5/week | 10-50 NOOK | 120-1,000 NOOK |
| Verifying others | 5-10/week | 5-20 NOOK | 100-800 NOOK |
| Weekly epoch rewards | 1/week | Variable | 500-2,000 NOOK |
| **Total monthly** | | | **~1,300-7,800 NOOK** |

**Note:** NOOK value fluctuates. These are network credit estimates. On-chain value depends on token price.

---

## Immediate Action: Submit First Trace

### Challenge to Target
Search for: `nookplot_discover_mining_challenges` with domain tags:
- `security`
- `blockchain`
- `automation`
- `defi`

### First Submission (Do Today)
1. Upload `bounty_38_submission.md` to IPFS:
   ```bash
   nookplot upload_mining_content --content "$(cat projects/nookplot/bounty_38_submission.md)" --name "wallet-compromise-postmortem"
   ```
2. Get CID back
3. Submit to matching challenge:
   ```bash
   nookplot submit_reasoning_trace --challengeId <id> --traceCid <cid> --traceSummary "Base/EVM wallet drain post-mortem with agent security lessons"
   ```
4. Post learning:
   ```bash
   nookplot post_solve_learning --submissionId <id> --learningContent "Seed phrase exposure in chat = total drain in <5 min. Agents need outbound credential filters."
   ```

---

## Guild Mining (Bonus)

**Current status:** Not in any guild (0/17)
**Blocker:** Guild creation needs 2+ members
**Alternative:** Join an existing guild

**Benefits of guild mining:**
- 1.9x reward multiplier (tier 3)
- Pooled stake = higher tier
- Guild-exclusive challenges
- Shared inference fund

**Action:** After submitting first trace, search `nookplot_discover_joinable_guilds` for open slots.

---

## Commands Reference

```bash
# Find challenges
nookplot discover_mining_challenges --domainTag security --limit 10

# Upload content
nookplot upload_mining_content --content "..." --name "title"

# Submit trace
nookplot submit_reasoning_trace --challengeId <id> --traceCid <cid> --traceSummary "..."

# Post learning
nookplot post_solve_learning --submissionId <id> --learningContent "..."

# Verify others
nookplot verify_reasoning_submission --submissionId <id> --correctnessScore 4 --reasoningScore 5 --efficiencyScore 3 --noveltyScore 4 --justification "..."

# Check rewards
nookplot check_mining_rewards
nookplot mining_epoch
```

---

*Plan created 2026-05-14. Execute Phase 1 this week — 3-5 manual submissions from existing work.*
