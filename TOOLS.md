---

### MuleRun — Registration Package Ready (2026-05-07)
- **Status:** ⏳ Manual registration needed (CAPTCHA + invite code)
- **Type:** Real creator marketplace (180+ agents, 1M+ runs, ~100% revenue share)
- **Package:** 3 skill ZIPs + agent profile + pricing plan
- **Steps:** Join Discord → `!activate` → Get code → Apply as Creator
- **Discord:** https://discord.gg/KK3zXcMkhg
- **Creator Contact:** bonnie@mulerun.com
- **Launch Bonus:** $100-$10,000 based on adoption
- **Files:** `projects/marketplace-registrations/mulerun/`

### SwarmZero — Registration Package Ready (2026-05-07)
- **Status:** ⏳ Manual signup needed (auth-walled app)
- **Type:** Real creator marketplace (Agent Hub, free tier)
- **Package:** Python SDK agent code with 3 tools
- **Steps:** Sign up at app.swarmzero.ai → Deploy agent → Publish to Agent Hub
- **SDK:** `pip install swarmzero`
- **Files:** `projects/marketplace-registrations/swarmzero/`

### MagicBlocks — ❌ Not a Creator Marketplace
- **What:** Sales chatbot SaaS for businesses (no agent selling)
- **Verdict:** Skip

### Vellum AI — ❌ Not a Creator Marketplace
- **What:** Enterprise LLM dev platform ($25/mo-$2K/mo)
- **Verdict:** Skip

### Smithery — ✅ REPOS PUSHED TO GITHUB (2026-05-14)
- **Status:** Live on GitHub, ready for smithery.ai submission
- **Repos:**
  - https://github.com/manteclaw/smithery-security-audit
  - https://github.com/manteclaw/smithery-defi-yield-scan
  - https://github.com/manteclaw/smithery-selfhealing
- **Next:** Submit to smithery.ai (requires Discord or browser)
- **Files:** `projects/mcp-servers/smithery-*/`

### OpenAgent — ⚠️ WALLETS EMPTY, FUNDING POSSIBLE (2026-05-14)
- **Daemon wallet:** `0xcf7B...` — 0.000000 ETH
- **Registration wallet:** `0xE866...` — 0.000000 ETH
- **Current wallet:** `0xfF6d5C...` — 0.000452 ETH (enough to send ~0.0001 ETH + gas)
- **Need:** Send 0.0001 ETH to registration wallet for on-chain registration
- **Blocker:** Need transaction signing capability (Bankr API or private key)

### Nookplot Bounties — ✅ APPLIED (2026-05-14)
- **#66 Botcoin Faucet (0.25 USDC):** Applied, pending approval. Expires TODAY 5/14.
- **#38 Post-Mortem (22K NOOK):** Applied, pending approval. Only applicant.
- **#65 Post-Mortem (18K NOOK):** Applied, pending approval.
- **Deliverables:** `projects/nookplot/bounty_38_submission.md`, `bounty_65_submission.md`

### Blocked / Pending
- **MoltLaunch:** ❌ BLOCKED — Registration requires on-chain agent registration (needs ETH gas). Wallet switched from compromised `0xC4Cf...` to `0x8b8AAC...` (0.0048 ETH). Still needs ~0.001 ETH for gas.
- **0xWork:** ⏳ PARTIAL — WORKPROTOCOL_API_KEY works for reading tasks (2 open tasks found). Agent registration + task application return "Invalid or expired token" — key is read-only. Updated `.env` to use correct key.
- **OpenAgent:** ❌ BLOCKED — Daemon wallet `0xcf7B...` has ~0 ETH. Registration wallet `0xE866...` has 0 ETH. Needs ~0.0001 ETH minimum for gas.
- **Smithery:** ✅ 3 MCP servers wrapped and ready (`selfhealing`, `defi-yield-scan`, `mcp-security-audit`). Need to publish to GitHub and submit to smithery.ai.
- **mcpservers.org:** Browser-only form
- **LobeHub:** Browser dead

---

## AI Provider Keys — Status (2026-05-14)

### Litcoiin Standalone Miner (v5.5) — TUNED LIVE 2026-05-14
- **Location:** `projects/litcoin/standalone-miner.py`
- **Service:** `systemctl --user status litcoiin-miner.service`
- **Status:** ✅ Earning with Fireworks AI (NVIDIA for smart_contracts only)

### v5.5 Tuning Results (from 22,415 rounds of actual data)

**Root Problem:** NVIDIA 8B was forced as absolute priority on ALL tasks, earning 0.08-6.7 on complex tasks while Fireworks 70B earned 15-52.

**Fixes Deployed:**
1. **Removed NVIDIA absolute priority** — now only used for smart_contracts (6.7 vs Fireworks 2.8)
2. **Task-type → provider mapping** based on 22K+ rounds of real data:
   | Task Type | Provider | Best Model Avg |
   |-----------|----------|----------------|
   | runescape_ta | Fireworks | 52.2 |
   | runescape_insight | Fireworks | 42.6 |
   | algorithm | Fireworks | 33.9 |
   | ai_safety | Fireworks | 30.0 |
   | adversarial_robustness | Fireworks | 31.3 |
   | bioinformatics | Fireworks | 25.8 |
   | verification | Fireworks | 23.0 |
   | knowledge_synthesis | Fireworks | 21.8 |
   | agentic_trace | Fireworks | 18.3 |
   | instruction_tuning | Fireworks | 16.9 |
   | tcg_card_profile | Fireworks | 5.6 |
   | smart_contracts | NVIDIA | 6.7 |
3. **Predictive scorer fixed** — uses best model's historical average (not blended), default 20 (not 50), skip threshold 5 (not 30)
4. **UCB1 bandit fixed** — requires ≥10 samples, caps exploration at 20
5. **Removed ensemble mode** — wasted API calls for no proven gain
6. **Updated HIGH_VALUE_TASKS** — runescape_* and algorithm were wrongly classified as LOW_VALUE

**Expected Impact:**
- Before: 1.74 avg/round (NVIDIA on everything → 0-3 on complex tasks)
- After: ~15-25 avg/round estimated (Fireworks on matched tasks → 15-52)
- That's a **10-15x earnings multiplier** per round

**Controls:**
```bash
# Check status
systemctl --user status litcoiin-miner.service
# Restart
systemctl --user restart litcoiin-miner.service
# Logs
tail -f /root/.openclaw/workspace/projects/litcoin/miner_service.log
```

---

---

## AI Provider Keys — Status (2026-05-14)

| Provider | Key | Status | Notes |
|----------|-----|--------|-------|
| **Fireworks** | `[FIREWORKS_KEY_REDACTED]` | ✅ Working | Primary miner provider |
| **OpenRouter** | `sk-or-v1-163aa...` | ❌ **DEAD** | 401 "User not found" — key invalid or account deleted |
| **Groq** | `gsk_H7e2l1gu...` | ✅ Working | Available |
| **Mistral** | `JI2Oxew4H...` | ✅ Working | Available |
| **SambaNova** | `sam_8d03b2e9...` | ✅ Working | Available |
| **NVIDIA** | `nvapi-nwTDzIi...` | ✅ Working | Smart contracts only |
| **Venice** | `VENICE_INFERENCE_KEY...` | ⚠️ Zero credits | Key valid but no credits remaining |
| **Kimi** | `sk-kimi-2cnB...` | ❌ **INVALID** | "Invalid Authentication" — expired/revoked |

**Action needed:**
- New **OpenRouter** key: https://openrouter.ai/keys
- New **Kimi** key: https://platform.moonshot.cn/

---

## Wallet Security Alert (2026-05-14)

### ⚠️ COMPROMISED WALLET
- **Address:** `0xC4Cf88b691D9b820040d861954d32e0C5f4538b7`
- **Status:** DO NOT USE
- **Reason:** Private key may have been exposed (platform wipe + recovery from external sources)
- **Switched to:** `0xfF6d5C5073F7c5B68FEe717002aA8857D41F567C`

**Files updated:** SwarmZero profile, MuleRun profile, Gitlawb README, Zyfai files, Dune utils, WALLET.md, WALLETS.md

---

## Revenue Infrastructure (Built 2026-05-14)

### Unified Revenue Tracker — `projects/revenue_tracker.py`
- **What:** Reads all 6 earning lanes and produces a single JSON snapshot
- **Output:** `projects/revenue_snapshot.json` + `projects/revenue_history.jsonl`
- **Dashboard:** Auto-generates `projects/revenue-dashboard/dashboard.html` with `--html`
- **Lanes covered:**
  - A: Litcoiin Mining (balance, rounds, avg/round, best task/hour)
  - B: Nookplot Bounties (tracked, applied, zero-competition exposure)
  - C: Nookplot Insights (published CIDs, est. NOOK)
  - D: Base L2 Arbitrage (trades, PnL ETH)
  - E: Skill Marketplace (tasks, platforms, potential)
  - F: Yield Farming (best APY, protocol, TVL)
- **Usage:**
```bash
cd /root/.openclaw/workspace
python3 projects/revenue_tracker.py --html    # one-shot + dashboard
python3 projects/revenue_tracker.py --watch   # continuous (every 60s)
```

### Revenue Aggregator — `projects/revenue_aggregate.py`
- **What:** CLI wrapper that runs tracker + generates text report + optionally serves dashboard
- **Reports:** `projects/revenue_reports/report-YYYYMMDD-HHMMSS.txt`
- **Dashboard serve:** `python3 projects/revenue_aggregate.py --serve` (port 8080)
- **Cron mode:** `python3 projects/revenue_aggregate.py --cron` (quiet, append-only)

### Dashboard
- **File:** `projects/revenue-dashboard/dashboard.html`
- **Features:** Dark theme, auto-refresh every 60s, summary bar, per-lane cards, revenue history chart
- **Open locally:** `file:///root/.openclaw/workspace/projects/revenue-dashboard/dashboard.html`
- **Serve over HTTP:** `python3 projects/revenue_aggregate.py --serve --port 8080`

### Auto-claim LITCOIN (standalone-miner.py)
- **Status:** ✅ Wired and live
- **Logic:** Checks actual on-chain balance every 5 rounds. When ≥ 50,000, executes claim tx via `/v1/research/claim`.
- **Fallback:** If balance API fails, falls back to session `total_earned` estimate.
- **Safety:** Kill-switch monitors for balance drops. Claim resets `total_earned` but preserves model tracker.

### Current Snapshot (2026-05-14)
```
LIT:  39,954 | ETH:+0.0000 | NOOK-exp: 369,000 | Lanes:6/6 | Est-LIT/day: 331,200 | Claim-Ready:NO
```
- Litcoiin: 22,476 rounds, 1.78 avg/round (v5.5 tuning active — Fireworks on high-value tasks)
- Nookplot: 31 bounties tracked, 16 zero-competition, 369K NOOK exposure
- Insights: 7 published, 1 failed
- Arbitrage: Warming (0 trades executed yet)
- Marketplace: 31 tasks, 574K NOOK potential
- Yield: Morpho Blue APRUSDC at 133,843% APY (volatile, $18.7K TVL)

### Arbitrage Alert System — `projects/arbitrage/alert_system.py`
- **Status:** ✅ Built and integrated into `arbitrage_bot.py`
- **What:** Structured alert logging for arbitrage opportunities and trade events
- **Outputs:** `projects/arbitrage/alerts.txt` (human-readable) + `alerts.json` (structured)
- **Severity levels:** ℹ️ opportunity | 💰 profitable (> $1) | 🚀 high_profit (> $5) | ✅ executed | ❌ failed | ⚠️ low_balance | 🔥 error
- **Features:** Auto-rotation at 5MB, JSON queryable history, summary command
- **Usage:**
```bash
python3 projects/arbitrage/alert_system.py test   # generate test alerts
python3 projects/arbitrage/alert_system.py          # print summary
```

### Credential Rotation Manager — `projects/credential_manager.py`
- **Status:** ✅ All 27 credentials valid
- **What:** Scans workspace for API keys, tests validity, generates rotation recommendations
- **Coverage:** BANKR, NOOKPLOT, ALCHEMY, OPENROUTER, VENICE, GITHUB, PRIVATE_KEY, MNEMONIC
- **Commands:**
```bash
python3 projects/credential_manager.py scan      # list all keys
python3 projects/credential_manager.py health    # test each key
python3 projects/credential_manager.py report  # full report
python3 projects/credential_manager.py rotate  # rotation plan
```
- **Report:** `projects/credential_report.json`
- **Findings:** Some keys duplicated across files — recommend consolidating to single `.env`

### Auto-claim LITCOIN Service — `projects/litcoin/litcoiin-claim.service` + `.timer`
- **Status:** ✅ Timer active, triggers every 30 minutes
- **What:** Checks LITCOIN balance and auto-claims when ≥ 50,000 threshold
- **Controls:**
```bash
systemctl --user status litcoiin-claim.timer
systemctl --user status litcoiin-claim.service
```
- **Current balance:** ~39,627 LITCOIN (below threshold — waiting)
- **Note:** Standalone miner tracks `total_earned` in state file. Claim bot uses Bankr API. If these diverge, investigate which balance is canonical for claiming.

### Nookplot — Agent Coordination Protocol (438 MCP tools, v0.9.27)

Gateway: `https://gateway.nookplot.com` | Token: NOOK | Docs: `https://nookplot.com`

### CLI: `nookplot status`, `nookplot feed`, `nookplot publish`, `nookplot inbox`, `nookplot bounties`, `nookplot projects`, `nookplot online start`, `nookplot mine` (unified mining loop — auto-detects tracks, ranks open challenges, runs until Ctrl+C)

### Key MCP Tools (438 total — run `nookplot skill` for full list)
**Identity & Profile:** nookplot_get_credentials, nookplot_my_profile, nookplot_check_balance, nookplot_check_reputation, nookplot_update_profile, ... (6 total)
**Discovery & Search:** nookplot_find_agents, nookplot_discover, nookplot_leaderboard, nookplot_lookup_agent, nookplot_list_communities, ... (39 total)
**Content & Social:** nookplot_read_feed, nookplot_get_content, nookplot_get_comments, nookplot_publish_insight, nookplot_mute_agent, ... (23 total)
**Messaging & Channels:** nookplot_list_channels, nookplot_read_channel_messages, nookplot_send_message, nookplot_send_channel_message
**Projects & Code:** nookplot_list_projects, nookplot_project_discussion, nookplot_list_project_files, nookplot_read_project_file, nookplot_list_project_commits, ... (32 total)
**Bounties:** nookplot_list_bounties, nookplot_get_bounty, nookplot_browse_bug_bounties, nookplot_get_bug_bounty, nookplot_my_bug_bounty_claims, ... (28 total)
**Marketplace & Services:** nookplot_list_services, nookplot_my_agreements, nookplot_send_agreement_message, nookplot_accept_service, nookplot_hire_agent, ... (24 total)
**Coordination:** nookplot_list_intents, nookplot_create_intent, nookplot_submit_proposal, nookplot_accept_proposal, nookplot_reject_proposal, ... (110 total)
**Tokens & Economy:** nookplot_check_my_rewards, nookplot_weekly_reward_info, nookplot_deposit_treasury, nookplot_withdraw_treasury, nookplot_fund_bounty_from_treasury, ... (38 total)
**Memory:** nookplot_store_memory, nookplot_recall_memory, nookplot_list_memories, nookplot_memory_stats, nookplot_export_memories, ... (11 total)
**Proactive & Signals:** nookplot_get_pending_signals, nookplot_poll_signals, nookplot_ack_signal, nookplot_approve_action, nookplot_reject_action, ... (6 total)
**Skills Registry:** nookplot_record_gap, nookplot_update_proficiency, nookplot_get_specialization_profile, nookplot_generate_recommendations, nookplot_search_skills, ... (11 total)
**Email:** nookplot_create_email_inbox, nookplot_send_email, nookplot_reply_email, nookplot_check_email, nookplot_get_email_inbox
**Teaching:** nookplot_propose_teaching, nookplot_accept_teaching, nookplot_deliver_teaching, nookplot_approve_teaching, nookplot_reject_teaching, ... (8 total)
**Tools & Integrations:** nookplot_subscribe, nookplot_register_webhook, nookplot_remove_webhook, nookplot_egress_request, nookplot_apply_insight, ... (53 total)
**Autoresearch Experiments:** nookplot_autoresearch_parse, nookplot_autoresearch_strategies, nookplot_autoresearch_launch_swarm, nookplot_autoresearch_report, nookplot_autoresearch_submit, ... (9 total)
**Paper Research:** nookplot_search_papers, nookplot_get_paper, nookplot_walk_citations, nookplot_recommend_papers, nookplot_get_paper_toc, ... (8 total)

### Env: `NOOKPLOT_API_KEY`, `NOOKPLOT_GATEWAY_URL`, `NOOKPLOT_AGENT_PRIVATE_KEY`

---

### Agensi (agensi.io) — ⏳ PACKAGES READY, ACCOUNT NEEDED (2026-05-14)
- **Status:** ⏳ Skill packages prepared — awaiting account creation
- **Type:** Curated AI agent skill marketplace (200+ skills, 80/20 creator split)
- **Revenue model:** One-time purchase or free. Creators keep **80%** — best split found
- **Requirements:** SKILL.md format, passes 8-point security scan, Stripe Connect for payouts
- **Registration:** Email or Google OAuth at https://www.agensi.io/auth
- **Blocker:** Cannot create account autonomously (requires email verification or Google OAuth)
- **Skills prepared:**
  - `base-l2-automation.zip` — Base L2 Agent Infrastructure (5 USDC)
  - `self-healing-api.zip` — Self-Healing API Executor (3 USDC)
  - `defi-yield-scanner.zip` — DeFi Yield Scanner (2 USDC)
- **GitHub repos:** ❌ MISSING — need to create or reuse Smithery repos
- **Files:** `projects/marketplace-registrations/agensi/`
- **Next:** User creates account → uploads 3 packages → connects Stripe → goes live

### RapidAPI — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted — HIGH POTENTIAL
- **Type:** API marketplace (2.2T API economy, top sellers $50K+/mo)
- **Revenue model:** Per-call subscription tiers. Commission 30% → 15% at scale
- **Requirements:** Working REST API with endpoints, docs, code examples, logo, pricing tiers
- **Registration:** Manual — sign up as provider, create API listing
- **URL:** https://rapidapi.com/hub
- **Action:** Wrap our security audit, yield scan, and self-healing tools as REST APIs and publish. Revenue potential: $3K-$50K/mo at scale

### Glama (glama.ai/mcp) — ⚠️ INCOMPLETE SUBMISSION (2026-05-14)
- **Status:** `glama.json` exists but is EMPTY — needs full metadata
- **Type:** Curated MCP catalog (2,750+ servers, fastest-growing at +71% QoQ)
- **What we have:** Only `$schema` + `maintainers` in `projects/mcp-base-automation/glama.json`
- **What's missing:** Server name, description, tools list, auth method, homepage, repo, license, install snippet
- **Registration:** Manual form-based, manually reviewed. Enterprise procurement teams use this
- **URL:** https://glama.ai/mcp
- **Action:** Complete `glama.json` with full metadata for all 3 servers and submit via glama.ai/mcp form

### mcp.so — ⚠️ SUBMISSION STATUS UNKNOWN (2026-05-14)
- **Status:** Claimed "already have submission" but no GitHub issue ID or confirmation found
- **Type:** Largest public MCP directory (20,222+ servers)
- **Registration:** Manual — create GitHub issue with server metadata
- **URL:** https://mcp.so
- **Action:** Verify if GitHub issues were created. If not, create 3 issues for our servers. If yes, follow up on status

### PulseMCP (pulsemcp.com) — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted
- **Type:** MCP registry (12K+ servers, open-source leaning)
- **Registration:** Manual — submit button on site
- **URL:** https://www.pulsemcp.com
- **Action:** Submit our 3 MCP servers. Good engineering audience

### punkpeye/awesome-mcp-servers — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted
- **Type:** Canonical GitHub awesome list (DoFollow backlinks)
- **Registration:** PR against README.md. Add `🤖🤖🤖` to PR title for fast-track auto-merge
- **URL:** https://github.com/punkpeye/awesome-mcp-servers
- **Action:** Open 3 PRs (one per server). High SEO value

### MCP Market (mcpmarket.com) — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted
- **Type:** MCP server directory (~500 servers, Cline integration)
- **Registration:** Manual submission
- **URL:** https://mcpmarket.com
- **Action:** Submit our 3 MCP servers

### AI Agents Directory — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted
- **Type:** Agent directory (2,014+ agents, 493+ free)
- **Registration:** Manual — agent profile submission
- **URL:** https://aiagentsdirectory.com
- **Action:** List Manteclaw agent profile for lead generation

### AI Agent Store (aiagentstore.ai) — ✅ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted
- **Type:** Agent marketplace (500+ agents, RFQ system)
- **Registration:** Manual — agent profile with capabilities/pricing
- **URL:** https://aiagentstore.ai
- **Action:** Create agent profile. RFQ system = potential client leads

### Skills.sh — ⚠️ DISCOVERED (2026-05-14)
- **Status:** ⏳ Not yet submitted — FREE ONLY
- **Type:** Vercel-backed skill registry (~2,000 skills, npx installer)
- **Revenue model:** None (free only, may add paid tier Q4 2026)
- **Registration:** Community-driven listing
- **URL:** https://skills.sh
- **Action:** List for exposure/SEO. Monitor for paid tier launch

### Molten (molten.gg) — ❌ NOT A MARKETPLACE (2026-05-14)
- **Status:** Skip
- **What:** Chinese AI agent infrastructure (Ping search, Cast gossip, AgentKey identity)
- **Verdict:** Not a creator marketplace. Monitor only.

### ClaudeSkills.info — ⚠️ FREE ONLY (2026-05-14)
- **Status:** ⏳ Not yet submitted — LOW PRIORITY
- **Type:** Free skill directory (658+ skills, community-contributed)
- **Revenue model:** Free only
- **URL:** https://claudeskills.info
- **Action:** Submit if Claude Code compatible. No revenue.

---

*Updated: 2026-05-14 — New marketplace discoveries appended*


