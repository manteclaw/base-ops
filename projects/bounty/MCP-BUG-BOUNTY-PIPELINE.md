# MCP Bug Bounty Scanning Pipeline — Setup Report

## Objective
Set up an automated bug bounty scanning pipeline for MCP servers, targeting huntr.com / MSRC / Google VRP submissions. Reference benchmark: eltociear agent found 68+ CVEs across MCP servers. Target bounty: $1,500-$50K per vulnerability.

---

## 1. Scanners Found & Installed

### ✅ Primary Scanner: `mcp-audit` (Python)
- **Package:** `mcp-audit-scanner` v0.8.1
- **Installation:**
  ```bash
  pipx install mcp-audit-scanner
  # Or in venv:
  python3 -m venv venv && source venv/bin/activate && pip install mcp-audit-scanner semgrep
  # Fix typer/click compatibility if needed:
  pip install 'typer<0.13'
  ```
- **Commands:**
  - `mcp-audit sast <target> --format json` — SAST scan with Semgrep rules
  - `mcp-audit scan --auto` — Scan Claude Desktop / Cursor configs
  - `mcp-audit discover` — List detected MCP configs
  - `mcp-audit shadow` — Find all shadow MCP servers on host
  - `mcp-audit sbom` — Generate CycloneDX SBOM
- **Ruleset:** 68+ Semgrep rules covering OWASP MCP Top 10:
  - `mcp-fastapi-no-ssl`, `mcp-flask-no-ssl` (CWE-319)
  - `mcp-logging-sensitive-var`, `mcp-api-key-header-logged` (CWE-532)
  - `mcp-open-path-traversal` (CWE-22)
  - `mcp-subprocess-string-cmd` (CWE-78)
  - `mcp-hardcoded-connection-string`, `mcp-hardcoded-api-key` (CWE-798)
  - `mcp-ts-fs-readfile-traversal`, `mcp-ts-path-join-traversal` (TypeScript)
  - `mcp-ts-execsync-injection`, `mcp-ts-fetch-ssrf`
  - `mcp-ts-tool-description-exfiltration` (tool poisoning)

### ⚠️ Secondary Scanner: `@piiiico/agent-audit` (npm)
- **Package:** `@piiiico/agent-audit` v0.3.9
- **Installation:** `npm install -g @piiiico/agent-audit`
- **Scope:** Scans MCP config files (Claude Desktop, Cursor) for prompt injection, command injection, hardcoded credentials, auth bypass, excessive permissions
- **Limitation:** Only scans config files, not source code directories

### ❌ `agent-security-scanner-mcp` (npm)
- **Package:** `agent-security-scanner-mcp`
- **Status:** Broken — missing `semantic-integration.js` module on install
- **Note:** Not usable in current state

---

## 2. Scan Results

### Target A: `awslabs/mcp` (8,633 stars)
**Command:**
```bash
mcp-audit sast /tmp/awslabs-mcp --format json > awslabs-mcp-scan.json
```

**Findings Summary:**
| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 201 |
| **Total** | **203** |

**Top Finding Types:**
| Title | Count | Notes |
|-------|-------|-------|
| `mcp-flask-no-ssl` | 67 | Sample/transport issues — mostly low impact |
| `mcp-logging-sensitive-var` | 54 | Credentials logged in async functions |
| `mcp-api-key-header-logged` | 37 | API keys forwarded to logs before auth check |
| `mcp-open-path-traversal` | 27 | `open()` with variable path in async functions |
| `mcp-subprocess-string-cmd` | 6 | `subprocess.run` with string commands |
| `mcp-print-sensitive-var` | 4 | Sensitive vars passed to `print()` |
| `mcp-hardcoded-connection-string` | 2 | CRITICAL — docstring examples (false positives) |

**Most Actionable Finding — Path Traversal (CWE-22):**
- **File:** `src/aws-healthomics-mcp-server/.../tools/workflow_management.py`
- **Function:** `create_workflow()` MCP tool
- **Vulnerability:** The `readme` parameter accepts a "local .md file path" and passes it to `validate_readme_input()` which calls `open(readme, 'r')` without path sanitization
- **Impact:** Arbitrary file read via path traversal (e.g., `readme="../../../etc/passwd"`)
- **Severity:** HIGH
- **Status:** Needs manual validation + PoC

**CRITICAL Findings — Hardcoded Connection Strings:**
- **File:** `src/documentdb-mcp-server/.../connection_tools.py`
- **Lines:** 58, 175
- **Reality:** FALSE POSITIVES — these are docstring examples with `# pragma: allowlist secret` annotations. The scanner matched example connection strings in documentation.

### Target B: OpenClaw Extensions (local)
**Command:**
```bash
mcp-audit sast /root/.openclaw/extensions --format json > openclaw-extensions-scan.json
```

**Findings Summary:**
| Severity | Count |
|----------|-------|
| CRITICAL | 7 |
| HIGH | 166 |
| MEDIUM | 90 |
| **Total** | **263** |

**Top Finding Types:**
| Title | Count |
|-------|-------|
| `mcp-ts-fs-readfile-traversal` | 71 |
| `mcp-ts-path-join-traversal` | 59 |
| `mcp-ts-fs-writefile-traversal` | 48 |
| `mcp-ts-no-type-check-before-use` | 29 |
| `mcp-ts-fetch-ssrf` | 22 |
| `mcp-ts-console-log-sensitive` | 21 |
| `mcp-ts-execsync-injection` | 4 |

**CRITICAL Findings Analysis:**
- **2x `mcp-ts-tool-description-exfiltration`** in `openclaw-lark/src/tools/oapi/im/message.js` — FALSE POSITIVES. The scanner flagged Chinese-language tool descriptions as "exfiltration keywords." These are legitimate Feishu IM tool descriptions.
- **4x `mcp-ts-execsync-injection`** in `openclaw-qqbot/scripts/` — LOW IMPACT. These are build/CLI scripts (`qqbot-cli.js`, `link-sdk-core.cjs`, `postinstall-link-sdk.js`), not MCP tool handlers. The `cmd` values are hardcoded in upgrade/install logic.
- **1x `mcp-ts-hardcoded-api-key`** in `openclaw-qqbot/src/api.ts` — FALSE POSITIVE. No actual hardcoded key at line 54; the scanner matched URL constants.

---

## 3. Submission Workflow Documentation

### huntr.com (Primary — AI/ML Open Source)
- **URL:** https://huntr.com
- **Programs:** Model File Vulnerabilities (MFV) + Open Source Vulnerabilities (OSV)
- **Scope:** MCP servers fall under OSV (open source AI libraries)
- **Bounty Range:** $1,500-$50,000 per validated vulnerability
- **Process:**
  1. Register at https://huntr.com (JOIN US)
  2. Go to https://huntr.com/bounties → find target repo
  3. Click "SUBMIT REPORT"
  4. Fill secure form with:
     - Title (e.g., "Path Traversal in AWS HealthOmics MCP Server")
     - Description + impact
     - Proof-of-Concept (PoC) script
     - Affected file(s) and line number(s)
     - CVSS score
  5. Wait for maintainer validation (31 days response window)
  6. If validated → bounty + CVE assigned
  7. Report goes public on day 90
- **Payment:** Monthly via Stripe Connect (25th of each month)
- **Blocker:** Requires browser-based submission (no API/CLI available)

### Microsoft MSRC
- **Scope:** Copilot MCP scope, Azure AI services
- **Bounty:** $250-$30,000 per vulnerability
- **URL:** https://msrc.microsoft.com
- **Blocker:** Browser submission + Microsoft account required

### Google VRP (Vulnerability Reward Program)
- **Scope:** Google AI/ML projects (genai-toolbox, etc.)
- **Bounty:** Varies by severity
- **URL:** https://bughunters.google.com
- **Blocker:** Browser submission

### 0din.ai (Mozilla)
- **Scope:** Mozilla AI/ML projects
- **Status:** 33 findings already submitted by eltociear
- **Blocker:** Browser submission

### OpenAI Safety Bounty (Bugcrowd)
- **Max Bounty:** $7,500
- **Focus:** Prompt injection, agent hijack
- **Blocker:** Browser submission via Bugcrowd

---

## 4. Industry Context (eltociear Pipeline)

**Reference:** https://github.com/eltociear/awesome-molt-ecosystem

**Scanner Stats:**
- 71 repos scanned
- 13 actionable reports generated
- ~30% false positive rate
- Low-hanging fruit exhausted; next vulns need biz logic / indirect injection / TOCTOU

**Ready-for-Submission Pipeline:**
| Target | Stars | Findings | Severity | Est. Bounty |
|--------|-------|----------|----------|-------------|
| awslabs/mcp | 8,633 | 9 SSRF via git clone | CRITICAL | $5K-$15K |
| pal-mcp-server | 11,352 | 5 path traversal | HIGH | $1.5K-$5K |
| CodeGraphContext | 2,714 | 3 Cypher injection | HIGH | $3.5K-$11.5K |
| Gmail-MCP-Server | 1,082 | 4 HIGH | HIGH | $1.5K-$5K |
| Cloudflare MCP | — | 6 HIGH | HIGH | $1.5K-$5K |
| Inspector (official) | 9,292 | 1 CRITICAL | CRITICAL | $3K-$10K |

**Total Pipeline Value:** $15,000-$50,000+

---

## 5. Recommended Next Steps

### Immediate (This Week)
1. **Validate the awslabs/mcp path traversal finding**
   - Write a PoC script that calls `create_workflow` with `readme="../../../etc/passwd"`
   - Confirm arbitrary file read
   - Document exact impact + CVSS score

2. **Register on huntr.com**
   - Complete browser-based registration
   - Link Stripe Connect for payouts
   - Browse bounties page for `awslabs/mcp`

3. **Submit first report**
   - Target: `awslabs/mcp` path traversal (CWE-22)
   - Include: PoC script, affected lines, impact description
   - Estimated bounty: $1,500-$5,000 (HIGH severity)

### Short-Term (Next 2 Weeks)
4. **Scan more high-value targets**
   - `pal-mcp-server` (11,352 stars)
   - `inspector` (9,292 stars)
   - `CodeGraphContext` (2,714 stars)
   - Use: `mcp-audit sast <repo> --format json`

5. **Build automated scan pipeline**
   - GitHub Actions workflow that runs `mcp-audit sast` on cloned repos
   - Filter findings by severity (HIGH/CRITICAL only)
   - Auto-generate draft report templates
   - Blocker: Submission still requires browser

### Medium-Term (Next Month)
6. **Explore headless browser submission**
   - Selenium/Playwright automation for huntr.com forms
   - Risk: Platform may detect/block automation
   - Alternative: Manual submission with pre-filled templates

7. **Expand scanner coverage**
   - Add custom Semgrep rules for MCP-specific patterns
   - Integrate with `nookplot` MCP tools (453 available) for distributed scanning
   - Target: 5 new repos per week

---

## 6. Key Files & Commands

### Scanner Installation (venv)
```bash
cd /root/.openclaw/workspace/projects/bounty
source venv/bin/activate
mcp-audit sast <target_dir> --format json > scan-results.json
```

### Scan Results Location
- `awslabs/mcp`: `/tmp/awslabs-mcp-scan.json` (203 findings, 2 CRITICAL, 201 HIGH)
- OpenClaw extensions: `/tmp/openclaw-extensions-scan.json` (263 findings, 7 CRITICAL, 166 HIGH)

### Quick Analysis
```bash
# Count by severity
cat scan-results.json | python3 -c "
import sys, json
content = sys.stdin.read()
lines = content.split('\n')
start = next(i for i, line in enumerate(lines) if line.strip().startswith('['))
data = json.loads('\n'.join(lines[start:]))
from collections import Counter
for sev, count in Counter(item['severity'] for item in data).most_common():
    print(f'{sev}: {count}')
"
```

---

## 7. Verdict

| Question | Answer |
|----------|--------|
| Scanner found? | ✅ YES — `mcp-audit-scanner` v0.8.1 installed and working |
| Scan run? | ✅ YES — 2 targets scanned (awslabs/mcp + openclaw extensions) |
| Findings? | ✅ YES — 466 total findings (9 CRITICAL, 367 HIGH, 90 MEDIUM) |
| Actionable vulnerabilities? | ⚠️ PARTIAL — 1 likely valid path traversal in awslabs/mcp; many false positives |
| huntr.com submission URL? | ❌ NOT YET — requires browser registration + manual submission |
| Pipeline ready? | ⚠️ PARTIAL — Scanner works, validation needed, submission is manual |

**Bottom line:** The scanner is live and finding real issues. The path traversal in `awslabs/mcp` is the most promising first submission. huntr.com registration + PoC validation are the blockers for first bounty.

---

*Report generated: 2026-05-06*
*Scanner: mcp-audit-scanner v0.8.1 with Semgrep SAST rules*
