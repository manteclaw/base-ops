#!/usr/bin/env bash
# auto-commit.sh — Git auto-commit + push for /root/.openclaw/workspace
# Usage: ./auto-commit.sh   (manual) or via cron

set -euo pipefail

REPO_DIR="/root/.openclaw/workspace"
LOGFILE="$REPO_DIR/.auto-commit.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for log readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    local msg="$1"
    local color="${2:-$NC}"
    echo -e "${color}[${TIMESTAMP}] ${msg}${NC}" | tee -a "$LOGFILE"
}

# Move to repo
cd "$REPO_DIR" || { log "ERROR: Cannot cd to $REPO_DIR" "$RED"; exit 1; }

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log "ERROR: Not a git repository" "$RED"
    exit 1
fi

# Stage all changes
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    log "No changes to commit" "$YELLOW"
    exit 0
fi

# Commit with timestamp
COMMIT_MSG="auto: $(date)"
if git commit -m "$COMMIT_MSG"; then
    log "Committed: $COMMIT_MSG" "$GREEN"
else
    log "ERROR: Commit failed" "$RED"
    exit 1
fi

# Try to push
if git push origin $(git branch --show-current 2>/dev/null || echo "main"); then
    log "Pushed successfully" "$GREEN"
else
    log "WARNING: Push failed (check remote/origin)" "$YELLOW"
    # Don't exit 1 — local commit succeeded, push may retry next run
fi

exit 0
