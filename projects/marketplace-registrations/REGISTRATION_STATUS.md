# Marketplace Registration Status — May 7, 2026

## Summary

**Requested:** 4 marketplaces (MuleRun, SwarmZero, MagicBlocks, Vellum AI)  
**Actual Creator Marketplaces:** 2 (MuleRun, SwarmZero)  
**Not Creator Marketplaces:** 2 (MagicBlocks = SaaS sales tool, Vellum = Enterprise LLM platform)  
**Registration Method:** Manual (browser CAPTCHA/auth walls block automation)

---

## ✅ MuleRun — READY TO REGISTER

**Status:** Application package complete, awaiting manual submission  
**Type:** Real creator marketplace (180+ agents, 1M+ runs)  
**Revenue:** ~100% to creators, $100-$10K launch bonuses  
**Entry:** Public launch March 18, 2026. Free tier (200 daily credits + 500 welcome).  
**Creator Studio:** Live but requires application approval (~2 days).

### Your Package
- 📄 `agent-profile.md` — Complete marketplace listing + agent instructions
- 🗜️ `base-l2-operations.zip` — Skill: DeFi on Base L2
- 🗜️ `mcp-security-audit.zip` — Skill: CVE scanner for MCP servers
- 🗜️ `litcoiin-miner.zip` — Skill: Proof-of-research mining
- 📋 Pricing: 15-100 credits per task

### Registration Steps (5 min)
1. Join Discord: https://discord.gg/KK3zXcMkhg
2. Send `!activate` → Wait 2-4h for invite code
3. Register: https://mulerun.com → Enter code → Verify email
4. Apply for Creator: https://mulerun.com/creator-studio
5. Upload 3 skill ZIPs + set pricing
6. Submit → Get $100 bonus + 1,000 credits

**Contact:** bonnie@mulerun.com

---

## ✅ SwarmZero — READY TO REGISTER

**Status:** Agent code + profile ready, awaiting signup  
**Type:** Real creator marketplace (Agent Hub for buying/selling agents)  
**Revenue:** Per-call credits / subscriptions  
**Entry:** Public beta, free tier available  
**SDK:** `pip install swarmzero` — Python-based agent builder

### Your Package
- 📄 `agent-profile.md` — Agent description + SDK code
- 🐍 `manteclaw_agent.py` — SwarmZero Agent class with 3 tools:
  - `mine_litcoiin()` — Bankr API mining
  - `audit_mcp_server()` — Security vulnerability scanner
  - `check_base_yield()` — DeFi yield optimizer

### Registration Steps (5 min)
1. Sign up: https://app.swarmzero.ai
2. Install SDK: `pip install swarmzero`
3. Run agent locally: `python manteclaw_agent.py`
4. Test: `curl http://localhost:8000/api/v1/chat`
5. Deploy to Agent Hub via web UI
6. Set pricing → Go live

---

## ❌ MagicBlocks — NOT A CREATOR MARKETPLACE

**What it is:** No-code AI sales chatbot SaaS for businesses  
**Why it doesn't fit:** You build chatbots for YOUR website, not sell autonomous agents to others  
**Their "marketplace":** Template sharing between agencies, not agent monetization  
**Alternative if interested:** Agency Partner Program (30% discount, free account)  
**Verdict:** Skip unless you want to build sales chatbots for clients

---

## ❌ Vellum AI — NOT A CREATOR MARKETPLACE

**What it is:** Enterprise LLM development platform  
**Why it doesn't fit:** Build/test/deploy internal agents. Pricing $25/mo-$2K/mo.  
**Their "marketplace":** Hosted prototype sharing, not public sales  
**Target:** CTOs moving from weekend project to production B2B  
**Verdict:** Skip unless you need enterprise LLM infrastructure

---

## 🔄 Suggested Replacements (Actual Creator Marketplaces)

Since 2 of 4 weren't marketplaces, here are 2 verified alternatives:

### 1. OpenAgent Market (openagent.market)
- ✅ Already registered but daemon exits / 0 ETH gas
- **Fix needed:** Fund wallet + debug daemon
- **Status:** Partial — needs completion

### 2. Smithery (smithery.ai)
- ✅ MCP server marketplace
- **Status:** Pending — needs FastMCP wrapper for your skills
- **Action:** Subagent was wrapping 3 utilities as MCP servers

### 3. Molten (molten.gg)
- Agent marketplace with guild system
- **Check:** If registration is easier than MuleRun/SwarmZero

---

## Files Created

```
projects/marketplace-registrations/
├── mulerun/
│   ├── agent-profile.md
│   ├── base-l2-operations.zip
│   ├── mcp-security-audit.zip
│   └── litcoiin-miner.zip
└── swarmzero/
    └── agent-profile.md
```

## Next Action

**You need to manually complete 2 registrations (5 min each):**
1. MuleRun: Join Discord → Get code → Apply as Creator → Upload ZIPs
2. SwarmZero: Sign up → Deploy agent → Publish to Agent Hub

Everything is prepared. Just copy-paste the profiles and upload the skill ZIPs.

**Want me to also fix OpenAgent (gas issue) and push Smithery MCP wrappers so you have 4 real marketplaces?**
