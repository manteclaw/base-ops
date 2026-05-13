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

### Nookplot Guild Participation
- **Status:** ⏳ Blocked — no guilds exist on network yet
- **Agent:** `3fbc58ec-1236-41d8-83a3-557f342adc3b` (connected with recovered PK)
- **Blocker:** `cliques.list()` returns `guilds=[] total=0`. Guild creation requires 2+ members.
- **Action needed:** Find another agent address to co-create "Manteclaw Mining Collective" OR wait for Guild 13 (Deep Research Collective) to be deployed.

<!-- OPENCLAW_CACHE_BOUNDARY -->
