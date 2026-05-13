# Security Policy — Manteclaw

## Incident History

### 2026-05-14 — Seed Phrase Leaked in Chat
- **Cause:** User shared 12-word seed phrase in chat message
- **Impact:** Wallet `0x8b8AAC...` drained within 2 minutes
- **Root cause:** Seed phrase appeared in conversation history, which may be logged or intercepted
- **Fix:** Implemented `.keys/` secure storage, pre-commit hooks, secret scanner

### 2026-05-08 — First Wallet Compromised  
- **Cause:** Platform wipe + recovery from external sources
- **Impact:** Wallet `0xC4Cf88...` potentially exposed
- **Fix:** Generated new wallet, rotated all references

## Secure Key Storage (.keys/)

### Location
`/root/.openclaw/workspace/.keys/`

### Permissions
- Directory: `700` (owner only)
- Files: `600` (owner read/write only)

### Contents
| File | Content | Permission |
|------|---------|------------|
| `wallet.seed` | 12-word mnemonic | 600 |
| `wallet.key` | Raw private key hex | 600 |
| `nookplot.key` | Nookplot agent key | 600 |
| `.env` | API keys + secrets | 600 |
| `*.env` | Project-specific secrets | 600 |

### NEVER
- ❌ Commit `.keys/` to git
- ❌ Share `.keys/` contents in chat
- ❌ Copy seed phrases into source code
- ❌ Hardcode API keys in scripts

### ALWAYS
- ✅ Read keys from file at runtime
- ✅ Reference via `WALLET_SEED_FILE` env var
- ✅ Use `scripts/key_loader.py` for access
- ✅ Run `scripts/secret_scanner.py` before committing

## .env File Policy

### Where secrets live
`.keys/.env` — the ONLY place for real API keys

### What's in repo
`.env.template` — placeholders only, safe to commit
`.env` — minimal file with wallet address + references, NO keys

### Migration
```bash
# Old way (INSECURE)
API_KEY=sk-xxx  # in .env, committed to git

# New way (SECURE)
# In .keys/.env:
API_KEY=sk-xxx
# In .env:
# API_KEY loaded from .keys/.env via scripts/load_env.py
```

## Pre-Commit Hook

Blocks commits if:
- Secret patterns detected in any file
- `.env` files staged
- `.keys/` directory staged

Install:
```bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Secret Scanner

Run manually:
```bash
python3 scripts/secret_scanner.py
```

Detects:
- BIP39 seed phrases (3+ consecutive words)
- Private keys (64 hex)
- API keys (sk-*, gsk_*, fw_*, nvapi-*, etc.)
- GitHub tokens (ghp_*)

## If You Need to Share a Key

**DO NOT share in chat.** Instead:
1. Write directly to `.keys/.env` via SSH/file editor
2. Or use a secure channel outside this conversation

## Emergency Response

If a seed is accidentally shared:
1. Immediately generate new wallet
2. Transfer any remaining funds
3. Rotate ALL references in codebase
4. Update `.keys/` with new seed
5. Document incident in memory files
