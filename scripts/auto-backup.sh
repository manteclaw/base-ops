#!/bin/bash
# auto-backup.sh — run every 5 minutes via cron
# Prevents future workspace wipes

cd /root/.openclaw/workspace

# Only commit if there are changes
if ! git diff --quiet HEAD 2>/dev/null; then
    git add -A
    git commit -m "auto: $(date -u +%Y-%m-%d-%H:%M:%S UTC)"
    
    # Push if remote exists
    if git remote get-url origin >/dev/null 2>&1; then
        git push origin main 2>/dev/null || true
    fi
fi
