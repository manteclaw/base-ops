# Bug Bounty Submission Report — 2026-05-14

## Advisories Ready to File

### 1. C1: QQBot Command Injection (CRITICAL)
- **File:** `qqbot-command-injection-CVE-2026-XXXX.md`
- **Impact:** RCE on host running OpenClaw gateway
- **CVSS:** 10.0
- **Est. Bounty:** $1,500 - $5,000

### 2. M1: QQBot SSRF (MEDIUM)
- **File:** `qqbot-ssrf-CVE-2026-XXXX.md`
- **Impact:** Internal network access, cloud metadata theft
- **CVSS:** 7.5
- **Est. Bounty:** $500 - $2,000

### 3. M2: FFmpeg Command Injection (MEDIUM-HIGH)
- **File:** `ffmpeg-command-injection-CVE-2026-XXXX.md`
- **Impact:** RCE via protocol prefix exploit
- **CVSS:** 9.8
- **Est. Bounty:** $300 - $1,500

**Total Est. Value: $2,250 - $10,000**

## Submission Paths

### Option 1: huntr.com ✅ BEST
- **URL:** https://huntr.com
- **Type:** AI/ML open-source bug bounty platform
- **Process:** Submit via secure form → 31 day maintainer response → validation → payout
- **Advantages:** Specifically for AI/ML, CVE awarded, public disclosure at day 90
- **Status:** Ready to submit

### Option 2: GitHub Security Advisory ❌ BLOCKED
- **Repo:** tencent-connect/openclaw-qqbot
- **Issue:** No SECURITY.md, no published advisories
- **Blocker:** We don't have maintainer access to create advisories
- **Workaround:** File via huntr.com which contacts maintainers

### Option 3: Direct Contact ❌ HARD
- **No security contact found** in repo
- **No email** listed for security issues
- **Tencent general security:** unlikely to route to this specific project

## Recommended Action

**Submit to huntr.com NOW.**

Steps:
1. Go to https://huntr.com
2. Create researcher account
3. Submit each advisory individually
4. Include: reproduction steps, impact, CVSS, suggested fix
5. Wait 31 days for maintainer response
6. If validated → bounty + CVE awarded

## Timeline
- **Submit:** Today (2026-05-14)
- **Maintainer response:** ~31 days
- **Validation/payout:** ~45-60 days
- **Public disclosure:** Day 90 (unless extension requested)

## Next Steps
- [ ] Create huntr.com researcher account
- [ ] Submit C1 (Command Injection)
- [ ] Submit M1 (SSRF)
- [ ] Submit M2 (FFmpeg Injection)
- [ ] Track submissions and respond to maintainer questions

---
**$2,250-$10,000 sitting on the table. Let's file these.** ⚡
