# HEARTBEAT.md - Proactive Checks

Every heartbeat, rotate through these checks. Don't just reply HEARTBEAT_OK — do the work.

## Quick Status (via daemon)

The **Manteclaw Daemon** (`daemon.py`) now runs lanes autonomously:
- **Lane A** — Litcoiin balance polling (every 5 min)
- **Lane B** — Nookplot bounty scraping (every 10 min)
- **Lane C** — 0xWork task discovery (every 15 min)
- **Lane D** — Zyfai APY monitor (every 30 min)

**Quick check:** `python3 daemon.py status`
**Lane state:** `python3 orchestrator.py summary`
**Auto-backup:** `python3 autobackup.py status`

## Manual Checklist (rotate 2-4x per day)

- [ ] **Calendar** — Check next 24-48h for upcoming events
- [ ] **Litcoiin balance** — Check if ≥ 50,000 threshold for claim (daemon covers this, but verify)
- [ ] **Nookplot** — Check for new bounties, messages, guild activity
- [ ] **Marketplaces** — Check for new hires, messages, tasks
- [ ] **Git status / Auto-commit** — Uncommitted changes? Run `./auto-commit.sh`. Check `.auto-commit.log` — if last commit was >24h ago, investigate why autobackup isn't firing.
- [ ] **Memory maintenance** — Review recent memory files, update MEMORY.md
- [ ] **Credential health** — `python3 credential_manager.py check`
- [ ] **Daemon health** — `python3 daemon.py status` — any crashed lanes?

## When to reach out (not HEARTBEAT_OK)

- Litcoiin balance hit 50,000 → Claim now (daemon will flag this)
- Calendar event in <2h → Reminder
- New Nookplot bounty matching our skills → Alert
- Marketplace hire/task → Alert
- Uncommitted changes >24h old → Push them
- Credential warning (30/60/90 days) → Alert for rotation
- Daemon lane crashed → Restart + investigate
- GitHub repo needs attention (issues, PRs)

## Track state

```json
{
  "lastChecks": {
    "calendar": null,
    "litcoiin_balance": null,
    "nookplot_bounties": null,
    "marketplaces": null,
    "git_status": null,
    "memory": null,
    "credentials": null,
    "daemon_health": null
  }
}
```

Write this to `memory/heartbeat-state.json` after each check.

## Infrastructure Commands

```bash
# Daemon
python3 daemon.py start          # background scheduler
python3 daemon.py stop           # stop scheduler
python3 daemon.py status         # lane status JSON

# Auto-backup
python3 autobackup.py start      # git auto-commit every 2h
python3 autobackup.py once       # manual trigger
python3 autobackup.py status     # last commit info

# Checkpoint (before any destructive op)
python3 checkpoint.py save "pre-key-rotation"
python3 checkpoint.py list
python3 checkpoint.py restore <id> --yes

# Credential lifecycle
python3 credential_manager.py scan
python3 credential_manager.py check
python3 credential_manager.py manifest
python3 credential_manager.py rotate <.env_file>

# Cross-lane state
python3 orchestrator.py summary
python3 orchestrator.py get A
```
