# Security Self-Audit — 2026-05-07

## ⚠️ CRITICAL: Exposed Secret Found

**File:** `.env.0xwork.bak` (tracked in git history)
**Secret:** `OPENROUTER_API_KEY=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`
**Status:** Removed from git index. **Key must be rotated immediately.**

Even though removed from current commit, the key exists in git history. Anyone with repo access can extract it.

## High-Priority Fixes

### 1. Rotate Exposed OpenRouter Key
- Go to https://openrouter.ai/keys
- Revoke: `sk-or-v1-23f2b28b...`
- Generate new key
- Update `.env` files and any deployed instances

### 2. Add .env Backups to .gitignore
```
.env*.bak
.env.*
*.env.backup
```

### 3. Fix npm Vulnerabilities (7 found)
**Package:** `undici` <=6.23.0 — HIGH severity
**Impact:** Resource exhaustion, HTTP smuggling, memory consumption
**Fix:** `cd manteclaw/ && npm audit fix`
**Dependency chain:** XMTP SDK → @xmtp/proto → undici

## Medium-Priority

### 4. Run `npm audit fix` on All Node Projects
- `manteclaw/` — 7 vulns
- `projects/x402-server/` — check separately
- `projects/governance-bot/` — no deps (pure Python)

### 5. Python Dependency Audit
- `safety` not installed — run `pip install safety && safety check`
- `bandit` for static analysis: `pip install bandit && bandit -r .`

### 6. File Permissions
- Check `.env` files are not world-readable: `chmod 600 .env`

## Scan Results Summary

| Check | Result | Action |
|-------|--------|--------|
| Hardcoded secrets in source | ✅ Clean | All keys redacted/parameterized |
| .env in git index | ⚠️ Found `.env.0xwork.bak` | Removed, but key exposed in history |
| npm audit | ❌ 7 high-severity | `npm audit fix` |
| pip safety | ⚠️ Not checked | Install `safety` and run |
| MCP self-scan | ⚠️ Not run | Install `@anthropic-ai/mcps-audit` |

## Next Actions
1. **URGENT:** Rotate OpenRouter key `sk-or-v1-23f2b28b...`
2. `npm audit fix` in `manteclaw/`
3. Add `*.env.bak` to `.gitignore`
4. Install `safety` + `bandit` for Python scanning
5. Run MCP security scanner on our own servers
