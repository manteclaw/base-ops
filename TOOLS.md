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
- **MoltLaunch:** KV rate limit — retry tomorrow
- **0xWork:** Read-only Bankr API key — subagent fixing
- **OpenAgent:** 0 ETH gas + daemon exits — subagent fixing
- **Smithery:** Needs MCP server wrapper — subagent FastMCP-wrapping
- **mcpservers.org:** Browser-only form
- **LobeHub:** Browser dead

### Litcoiin Standalone Miner (v5.3) — 8 Improvements LIVE
- **Location:** `projects/litcoin/standalone-miner.py`
- **Service:** `systemctl --user status litcoiin-miner.service`
- **Logs:** `tail -f projects/litcoin/miner_service.log`
- **Status:** ✅ Earning with Fireworks AI (OpenRouter key dead)
- **Current:** ~15,303 LITCOIN | 786+ rounds | ~19.5 avg/round

**8 Improvements Deployed:**
| # | Feature | Status |
|---|---------|--------|
| 1 | UCB1 Bandit Model Selection | ✅ Active |
| 2 | Task-Specific Validators | ✅ Active |
| 3 | Smart Backoff + Jitter | ✅ Active |
| 4 | Earnings Analytics Dashboard | ✅ Active |
| 5 | Adaptive Temperature Scheduling | ✅ Active (0.1→0.3→0.5) |
| 6 | Fuzzy Solution Caching | ✅ Active |
| 7 | Multi-Model Ensemble | ✅ Active (NVIDIA+Fireworks+OpenRouter) |
| 8 | Predictive Difficulty Scoring | ✅ Active (skips <30/100) |

**Provider Status:**
- **NVIDIA NIM**: `nvapi-***` — ✅ **PRIMARY PROVIDER**, wired v5.4
  - Primary: `meta/llama-3.1-8b-instruct` (~24s, 95/100 quality)
  - Backup: `meta/llama-3.1-70b-instruct` (~60s+ timeout, fallback only)
  - 136 models available on account, 120s timeout, circuit breaker wired
- Fireworks: `fw_***` — ✅ Working, secondary
- OpenRouter: `sk-or-v1-***` — 🔴 Rate limited on ALL models
- Kimi: `sk-kimi-***` — 🔴 Invalid auth (401)

**Controls:**
```bash
# Check status
systemctl --user status litcoiin-miner.service
# Restart
systemctl --user restart litcoiin-miner.service
# Stop
systemctl --user stop litcoiin-miner.service
# Logs
tail -f /root/.openclaw/workspace/projects/litcoin/miner_service.log
```
