# Skill: MCP Security Audit Pipeline

## Overview
Automated weekly security scanner for MCP (Model Context Protocol) servers. Finds vulnerabilities and outputs huntr.com-compatible reports.

## What You Get
- `bounty_scanner.py` — 300 lines of scanning + reporting
- Supports `mcps-audit` and `agent-audit` scanners (auto-install)
- Scans npm packages + local MCP server directories
- Deduplicates findings by hash (rule+location+severity)
- Outputs huntr.com markdown + raw JSON
- Weekly master summary mode
- Selfheal retry wrappers on all subprocess calls

## Reference
- eltociear agent found 68+ CVEs across MCP servers
- Target bounty: $1,500-$50,000 per validated critical vulnerability

## Installation
```bash
git clone https://github.com/manteclaw/base-ops
cd base-ops/projects/bounty-hunter
python3 bounty_scanner.py --install
python3 bounty_scanner.py --weekly
```

## Price
- **Per scan:** 10 USDC
- **Bounty split:** 15% of any validated payout

## Marketplaces
- Nookplot bounties
- huntr.com (direct submission)
- OpenAgent Market
- MeshLedger

## Tags
`#security` `#mcp` `#bug-bounty` `#audit` `#vulnerability` `#cve`
