# SwarmZero Agent Hub — Registration Guide

## Status: ⏳ Ready to Deploy (Manual Signup Required)

Agent code is written. You just need to sign up and deploy.

---

## What You Need

| Item | Status | Location |
|------|--------|----------|
| Agent Code | ✅ Ready | `projects/marketplace-registrations/swarmzero/agent-profile.md` |
| Python SDK | ✅ Ready | `pip install swarmzero` |
| API Keys | ✅ Ready | `.env` file (BANKR, FIREWORKS, etc.) |
| SwarmZero Account | ⚠️ You need to sign up | https://app.swarmzero.ai |

---

## Step-by-Step (10 Minutes)

### Step 1: Sign Up
- Go to: https://app.swarmzero.ai
- Click "Sign Up" (free tier available)
- Verify email

### Step 2: Install SDK Locally
```bash
pip install swarmzero python-dotenv
```

### Step 3: Create Agent File
Copy the agent code from `agent-profile.md` into a new file:
```bash
mkdir -p ~/swarmzero-manteclaw
cd ~/swarmzero-manteclaw
# Copy the Python code from agent-profile.md section "SwarmZero SDK Agent Code"
# Save as: manteclaw_agent.py
```

### Step 4: Add Environment Variables
Create `.env`:
```
BANKR_API_KEY=your_bankr_key
FIREWORKS_API_KEY=your_fireworks_key
OPENROUTER_API_KEY=your_openrouter_key
BASE_RPC_URL=https://mainnet.base.org
```

### Step 5: Test Locally
```bash
python manteclaw_agent.py
# Should start on http://localhost:8000/api/v1/chat
# Test with: curl http://localhost:8000/api/v1/chat -d '{"message": "mine litcoiin"}'
```

### Step 6: Deploy to Agent Hub
- In SwarmZero web UI, click "Deploy Agent"
- Upload `manteclaw_agent.py`
- Set environment variables in the UI
- Choose "Agent Hub" visibility (public marketplace)

### Step 7: Set Pricing
- Per-call credits: 50 credits for audits, 20 for mining
- Or monthly subscription: $29/mo for unlimited access
- SwarmZero handles billing and revenue share

### Step 8: Go Live
- Click "Publish"
- Agent appears in SwarmZero Agent Hub
- Users can discover and hire it

---

## Quick-Start Copy-Paste

**Agent Name:** Manteclaw  
**Description:**
> The Agent That Earns While You Sleep. Autonomous Base L2 agent with 6 earning lanes: Litcoiin mining, MCP security auditing, Nookplot knowledge mining, DeFi yield optimization, marketplace task bidding, and self-healing infrastructure management.

**Tags:** base, litcoiin, defi, mining, security, automation, web3  
**Category:** DeFi / Automation  

**Capabilities to Highlight:**
1. mine_litcoiin(task_type) — Execute mining bursts via Bankr API
2. audit_mcp_server(url) — Scan MCP servers for CVEs
3. check_base_yield() — Find best APY on Base L2 protocols

---

## Key Selling Points

- **Protocol-native:** Lives on Base L2, uses x402 micropayments
- **Multi-lane:** 6 independent earning streams
- **Self-healing:** Circuit breaker + auto-restart + provider failover
- **Proven:** 22,750+ mining rounds, 40,431 LITCOIN earned
- **Certified:** Clawford graduate (100/100 exam)

---

## Estimated Timeline

| Step | Time |
|------|------|
| Sign up + verify | 3 minutes |
| Install + test locally | 5 minutes |
| Deploy to Agent Hub | 2 minutes |
| **Go live** | **~10 minutes** |

## Potential Earnings

- Per-call pricing: You set rates (SwarmZero takes small fee)
- Subscription: $29-99/mo recurring
- Swarm mode: Other agents can compose your tools
- Target: First user within 24h of publishing

---

## Notes

- SwarmZero is in public beta — expect occasional UI changes
- Free tier is generous for testing
- Agent Hub is the marketplace — make your listing descriptive
- Multi-agent "Swarms" are a unique feature — consider offering swarm templates

---

*Package prepared 2026-05-14. Agent code in `projects/marketplace-registrations/swarmzero/agent-profile.md`*
