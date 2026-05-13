# Agensi Action Checklist

## Immediate Blockers (Need Your Input)

### 1. Create Account
- [ ] Visit https://www.agensi.io/auth
- [ ] Click "Don't have an account? Sign up"
- [ ] Use "Sign up with Google" (fastest) or fill email form
- [ ] Verify email if needed

### 2. Set Up Payouts
- [ ] Navigate to Creator Dashboard after login
- [ ] Connect Stripe Connect account
- [ ] This is required to receive the 80% revenue share

### 3. Create GitHub Repos (or reuse Smithery)
**Option A — Create new repos:**
- [ ] Create https://github.com/manteclaw/base-l2-ops
- [ ] Create https://github.com/manteclaw/selfhealing  
- [ ] Create https://github.com/manteclaw/defi-yield-scan

**Option B — Reuse existing Smithery repos:**
- [ ] https://github.com/manteclaw/smithery-security-audit → Rename/repurpose for security audit skill
- [ ] https://github.com/manteclaw/smithery-defi-yield-scan → Use for yield scanner
- [ ] https://github.com/manteclaw/smithery-selfhealing → Use for self-healing API

## Submission Steps (After Account Created)

### 4. Submit Skill 1 — Base L2 Automation (5 USDC)
- [ ] Go to https://www.agensi.io/dashboard/submit
- [ ] Upload `base-l2-automation.zip` (located at `projects/marketplace-registrations/agensi/packages/`)
- [ ] Set price: 5 USDC
- [ ] Add tags: base, l2, agent, infrastructure, wallet, identity, setup
- [ ] Link GitHub repo

### 5. Submit Skill 2 — Self-Healing API (3 USDC)
- [ ] Upload `self-healing-api.zip`
- [ ] Set price: 3 USDC
- [ ] Add tags: automation, retry, resilience, api, python
- [ ] Link GitHub repo

### 6. Submit Skill 3 — DeFi Yield Scanner (2 USDC)
- [ ] Upload `defi-yield-scanner.zip`
- [ ] Set price: 2 USDC
- [ ] Add tags: defi, yield, base, apy, scanner, usdc
- [ ] Link GitHub repo

### 7. Post-Submission
- [ ] Wait for 8-point security scan (automated, usually minutes)
- [ ] Wait for admin review
- [ ] Skills go live
- [ ] Start earning 80% on every sale

## Package Files Ready

All packages are prepared at:
```
projects/marketplace-registrations/agensi/packages/
├── base-l2-automation.zip        (851 bytes)
├── self-healing-api.zip          (1059 bytes)
└── defi-yield-scanner.zip        (926 bytes)
```

Each contains a properly formatted SKILL.md with:
- Agensi-compatible pricing (one-time purchase only)
- GitHub repo links for curl install
- Relevant tags for discoverability

## Expected Timeline

| Step | Time |
|------|------|
| Account creation | 2 minutes |
| Stripe Connect setup | 5 minutes |
| GitHub repo creation | 10 minutes (if creating new) |
| 3 skill submissions | 15 minutes |
| Security scan | ~5-30 minutes (automated) |
| Admin review | 24-48 hours |
| **Total to live** | **1-2 days** |

## Revenue Potential

| Skill | Price | Per Sale (80%) |
|-------|-------|----------------|
| Base L2 Automation | 5 USDC | 4.00 USDC |
| Self-Healing API | 3 USDC | 2.40 USDC |
| DeFi Yield Scanner | 2 USDC | 1.60 USDC |
| **Bundle value** | **10 USDC** | **8.00 USDC** |

If each skill sells 10x/month: **80 USDC/month** = potential baseline.

---

*Generated: 2026-05-14*
*Status: Ready to submit — awaiting account creation*
