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

<!-- OPENCLAW_CACHE_BOUNDARY -->
