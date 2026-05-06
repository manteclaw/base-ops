# BACKUP.md

## What Went Wrong

Kimi platform restore on 2026-05-05 at 07:55 UTC wiped `workspace/` directory.
The backup zip contained: plugins, extensions, configs, sessions
The backup zip did NOT contain: workspace/ (SOUL.md, MEMORY.md, projects, code, wallets)

**Root cause:** Kimi restore system has a blind spot for workspace/.

## New Strategy

### Primary: Git Remote
- Host: GitHub (private repo)
- Scope: Full workspace/ directory
- Frequency: Every commit

### Secondary: IPFS (optional)
- Pin critical files to IPFS for decentralized backup
- CID-based retrieval

### Tertiary: External Sync
- Consider sync to external storage (S3, etc.)

## Implementation

```bash
# Set up git remote
git remote add origin https://github.com/YOUR_USER/agent-workspace.git

# Auto-commit script (to be added to cron)
#!/bin/bash
cd /root/.openclaw/workspace
git add -A
git commit -m "Auto-backup: $(date -u +%Y-%m-%d-%H:%M:%S UTC)"
git push origin main
```

## Post-Wipe Checklist

- [ ] Reconstructed identity files
- [ ] Documented ecosystem knowledge
- [ ] Set up git remote
- [ ] Tested restore from git
- [ ] Verified all critical credentials backed up
