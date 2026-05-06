#!/bin/bash
cd /root/.openclaw/workspace || exit 1
git add -A
git commit -m "auto: $(date -u +%Y-%m-%d_%H:%M:%S)" 2>/dev/null || true
git push origin clean-main 2>/dev/null || true
