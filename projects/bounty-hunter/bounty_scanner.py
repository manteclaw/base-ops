#!/usr/bin/env python3
"""
bounty_scanner.py — NEW LANE: MCP Bug Bounty Pipeline
Weekly security scanner for MCP servers. Runs mcps-audit + agent-audit,
formats findings as huntr.com-compatible markdown reports.

Reference: eltociear agent found 68+ CVEs across MCP servers.
Target: $1,500-$50K per vulnerability via huntr.com, MSRC, Google VRP.

Usage:
    python3 bounty_scanner.py                              # Scan default targets
    python3 bounty_scanner.py --target ./my-mcp-server    # Scan local server
    python3 bounty_scanner.py --weekly                     # Cron mode — generate dated report
    python3 bounty_scanner.py --list-tools                 # Show available scanners
"""

import sys
import json
import os
import argparse
import subprocess
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Import selfheal retry wrappers
sys.path.insert(0, "/root/.openclaw/workspace")
from selfheal import retry, heal

# ── Config ──────────────────────────────────────────────────────────

REPORTS_DIR = Path("/root/.openclaw/workspace/projects/bounty-hunter/reports")
DEFAULT_TARGETS = [
    # Common MCP server packages to audit (npm-based)
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-github",
    "@modelcontextprotocol/server-postgres",
    "@modelcontextprotocol/server-sqlite",
    # Add more as discovered — these are high-value targets
]

# Local directories to scan (if they exist)
LOCAL_MCP_DIRS = [
    "/root/.openclaw/extensions",
    "/root/.openclaw/workspace/projects",
]

SCANNERS = {
    "mcps-audit": {
        "install": "npm install -g mcps-audit",
        "cmd": "mcps-audit",
        "args": ["--json"],
        "supports": ["config", "server"],
    },
    "agent-audit": {
        "install": "npm install -g @piiiico/agent-audit",
        "cmd": "agent-audit",
        "args": ["--json", "--min-severity", "medium"],
        "supports": ["config", "server"],
    },
    "agent-audit-mcp": {
        "install": "npm install -g @piiiico/agent-audit",
        "cmd": "agent-audit-mcp",
        "args": ["--json", "--min-severity", "medium"],
        "supports": ["config", "server"],
    },
}

# ── Helpers ─────────────────────────────────────────────────────────

def ensure_reports_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def scanner_available(name: str) -> bool:
    try:
        subprocess.run([name, "--version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def install_scanner(name: str):
    info = SCANNERS.get(name)
    if not info:
        return False
    print(f"[INSTALL] Installing {name}...")
    try:
        subprocess.run(info["install"].split(), check=True, timeout=120)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to install {name}: {e}")
        return False


# ── Scan Functions (with selfheal) ──────────────────────────────────

@heal(service="mcps-audit", max_retries=3, base_delay=5.0)
def run_mcps_audit(target: str) -> Dict[str, Any]:
    """Run mcps-audit against a target."""
    cmd = ["mcps-audit", target, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"mcps-audit failed: {result.stderr[:300]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # mcps-audit sometimes outputs mixed text+JSON — try to extract JSON
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except:
                    pass
        return {"raw_output": result.stdout, "parse_error": True}


@heal(service="agent-audit", max_retries=3, base_delay=5.0)
def run_agent_audit(target: str) -> Dict[str, Any]:
    """Run agent-audit against a target."""
    cmd = ["agent-audit", target, "--json", "--min-severity", "medium"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"agent-audit failed: {result.stderr[:300]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout, "parse_error": True}


# ── Report Formatters ───────────────────────────────────────────────

def format_huntr_report(findings: List[Dict[str, Any]], target: str, scanner: str) -> str:
    """Format findings as huntr.com-compatible markdown."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    md = f"""# Security Audit Report — {target}

**Scanner:** {scanner}  
**Date:** {now}  
**Target:** `{target}`  
**Agent:** Manteclaw (Automated MCP Security Pipeline)

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {sum(1 for f in findings if f.get('severity','').upper() == 'CRITICAL')} |
| 🟠 High | {sum(1 for f in findings if f.get('severity','').upper() == 'HIGH')} |
| 🟡 Medium | {sum(1 for f in findings if f.get('severity','').upper() == 'MEDIUM')} |
| 🟢 Low | {sum(1 for f in findings if f.get('severity','').upper() == 'LOW')} |
| **Total** | **{len(findings)}** |

---

## Findings

"""
    
    for i, finding in enumerate(findings, 1):
        sev = finding.get("severity", "UNKNOWN").upper()
        sev_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
        rule = finding.get("rule", finding.get("check", "N/A"))
        location = finding.get("location", finding.get("file", "N/A"))
        description = finding.get("description", finding.get("message", "No description provided."))
        evidence = finding.get("evidence", finding.get("snippet", ""))
        fix = finding.get("fix", finding.get("remediation", "Review and remediate based on severity."))
        owasp = finding.get("owasp", finding.get("category", "N/A"))
        cve = finding.get("cve", "N/A")
        
        md += f"""### {i}. {sev_emoji} [{sev}] {rule}

**Location:** `{location}`  
**OWASP / Category:** {owasp}  
**CVE:** {cve}

**Description:**
{description}

**Evidence:**
```
{evidence[:500]}
```

**Remediation:**
{fix}

---

"""
    
    md += f"""## Disclosures & Bounties

This report was generated by an automated MCP security scanning pipeline.
For original vulnerability research, findings should be:

1. **Verified manually** against the latest version of the target
2. **Reported via huntr.com** (https://huntr.com) for open-source projects
3. **Reported via MSRC** for Microsoft-related projects
4. **Reported via Google VRP** for Google-related projects

**Estimated bounty range:** $1,500 - $50,000 per validated critical vulnerability.

**Submission checklist:**
- [ ] Reproduced on clean environment
- [ ] Minimal proof-of-concept provided
- [ ] Impact clearly described
- [ ] Fix suggestion included
- [ ] Submitted to appropriate platform

---

*Report ID: `manteclaw-mcp-{hashlib.sha256((target + now).encode()).hexdigest()[:12]}`*  
*Pipeline: bounty_scanner.py v1.0*
"""
    return md


def normalize_findings(raw: Dict[str, Any], scanner: str) -> List[Dict[str, Any]]:
    """Normalize different scanner outputs to a common schema."""
    findings = []
    
    if scanner == "mcps-audit":
        # mcps-audit JSON structure varies — try common patterns
        for key in ["findings", "results", "vulnerabilities", "issues"]:
            if key in raw and isinstance(raw[key], list):
                for f in raw[key]:
                    findings.append({
                        "severity": f.get("severity", "MEDIUM"),
                        "rule": f.get("rule", f.get("title", "Unknown")),
                        "location": f.get("location", f.get("target", "N/A")),
                        "description": f.get("description", f.get("message", "")),
                        "evidence": f.get("evidence", f.get("snippet", "")),
                        "fix": f.get("remediation", f.get("fix", "Review documentation.")),
                        "owasp": f.get("owasp", f.get("category", "N/A")),
                        "cve": f.get("cve", "N/A"),
                        "scanner": scanner,
                    })
    
    elif scanner in ("agent-audit", "agent-audit-mcp"):
        # agent-audit outputs list of findings directly or nested
        data = raw
        if isinstance(data, dict):
            for key in ["findings", "results", "vulnerabilities"]:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
        if isinstance(data, list):
            for f in data:
                findings.append({
                    "severity": f.get("severity", "MEDIUM"),
                    "rule": f.get("rule", f.get("title", f.get("check", "Unknown"))),
                    "location": f.get("location", f.get("file", f.get("target", "N/A"))),
                    "description": f.get("description", f.get("message", "")),
                    "evidence": f.get("evidence", f.get("snippet", f.get("details", ""))),
                    "fix": f.get("fix", f.get("remediation", "Review and patch.")),
                    "owasp": f.get("owasp", f.get("category", "N/A")),
                    "cve": f.get("cve", "N/A"),
                    "scanner": scanner,
                })
    
    return findings


# ── Core Scanning ───────────────────────────────────────────────────

def scan_target(target: str, scanners: List[str]) -> Dict[str, Any]:
    """Run all available scanners against a single target."""
    all_findings = []
    scan_meta = []
    
    for scanner_name in scanners:
        if not scanner_available(scanner_name):
            print(f"[SKIP] Scanner not available: {scanner_name}")
            continue
        
        print(f"[SCAN] Running {scanner_name} against {target}...")
        try:
            if scanner_name == "mcps-audit":
                raw = run_mcps_audit(target)
            else:
                raw = run_agent_audit(target)
            
            findings = normalize_findings(raw, scanner_name)
            all_findings.extend(findings)
            scan_meta.append({
                "scanner": scanner_name,
                "target": target,
                "findings_count": len(findings),
                "status": "success",
            })
            print(f"[OK] {scanner_name}: {len(findings)} findings")
        except Exception as e:
            scan_meta.append({
                "scanner": scanner_name,
                "target": target,
                "findings_count": 0,
                "status": "failed",
                "error": str(e)[:200],
            })
            print(f"[FAIL] {scanner_name}: {e}")
    
    # Deduplicate by hash of rule+location+severity
    seen = set()
    unique = []
    for f in all_findings:
        h = hashlib.sha256(f"{f['rule']}:{f['location']}:{f['severity']}".encode()).hexdigest()[:16]
        if h not in seen:
            seen.add(h)
            f["_hash"] = h
            unique.append(f)
    
    return {
        "target": target,
        "scan_time": datetime.utcnow().isoformat() + "Z",
        "total_findings": len(unique),
        "findings": unique,
        "meta": scan_meta,
    }


def run_full_scan(targets: List[str], weekly: bool = False) -> Dict[str, Any]:
    """Run scan against all targets, generate reports."""
    ensure_reports_dir()
    
    available_scanners = [s for s in SCANNERS if scanner_available(s)]
    if not available_scanners:
        print("[WARN] No scanners installed. Attempting install...")
        for s in SCANNERS:
            if install_scanner(s):
                available_scanners.append(s)
    
    if not available_scanners:
        print("[ERROR] No scanners available after install attempts.")
        print(f"[INFO] Install manually: {list(SCANNERS.keys())}")
        return {"error": "no_scanners", "reports": []}
    
    print(f"[INFO] Using scanners: {available_scanners}")
    print(f"[INFO] Targets: {targets}")
    
    reports = []
    for target in targets:
        result = scan_target(target, available_scanners)
        
        # Generate huntr-compatible markdown report
        if result["findings"]:
            md = format_huntr_report(result["findings"], target, ", ".join(available_scanners))
            safe_name = target.replace("/", "_").replace("@", "at_")[:50]
            date_slug = datetime.utcnow().strftime("%Y%m%d")
            report_file = REPORTS_DIR / f"mcp_audit_{safe_name}_{date_slug}.md"
            with open(report_file, "w") as f:
                f.write(md)
            result["report_file"] = str(report_file)
            print(f"[REPORT] Saved: {report_file}")
        
        # Also save raw JSON
        json_file = REPORTS_DIR / f"mcp_audit_{safe_name}_{datetime.utcnow().strftime('%Y%m%d')}.json"
        with open(json_file, "w") as f:
            json.dump(result, f, indent=2)
        result["json_file"] = str(json_file)
        
        reports.append(result)
    
    # Weekly master summary
    if weekly:
        master = {
            "scan_date": datetime.utcnow().isoformat() + "Z",
            "total_targets": len(targets),
            "scanners_used": available_scanners,
            "total_findings": sum(r["total_findings"] for r in reports),
            "reports_dir": str(REPORTS_DIR),
            "targets": reports,
        }
        master_file = REPORTS_DIR / f"weekly_master_{datetime.utcnow().strftime('%Y%m%d')}.json"
        with open(master_file, "w") as f:
            json.dump(master, f, indent=2)
        print(f"[MASTER] Weekly summary: {master_file}")
    
    return {
        "scanners": available_scanners,
        "reports": reports,
        "reports_dir": str(REPORTS_DIR),
    }


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MCP Bug Bounty Scanner")
    parser.add_argument("--target", type=str, default=None, help="Single target to scan")
    parser.add_argument("--targets-file", type=str, default=None, help="JSON file with target list")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly master report")
    parser.add_argument("--install", action="store_true", help="Install all scanners")
    parser.add_argument("--list-tools", action="store_true", help="List available scanners")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()
    
    if args.list_tools:
        print("Available scanners:")
        for name, info in SCANNERS.items():
            status = "✅" if scanner_available(name) else "❌ (not installed)"
            print(f"  {status} {name}: {info['cmd']}")
            print(f"     Install: {info['install']}")
        return
    
    if args.install:
        for name in SCANNERS:
            install_scanner(name)
        return
    
    # Determine targets
    targets = []
    if args.target:
        targets = [args.target]
    elif args.targets_file:
        with open(args.targets_file) as f:
            targets = json.load(f)
    else:
        # Default: scan known high-value MCP server packages + local dirs
        targets = DEFAULT_TARGETS + [d for d in LOCAL_MCP_DIRS if os.path.exists(d)]
    
    result = run_full_scan(targets, weekly=args.weekly)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*70}")
        print(f"  MCP BUG BOUNTY SCANNER — {datetime.utcnow().isoformat()[:19]}Z")
        print(f"{'='*70}")
        print(f"  Scanners: {result.get('scanners', [])}")
        print(f"  Targets: {len(result.get('reports', []))}")
        total_findings = sum(r.get("total_findings", 0) for r in result.get("reports", []))
        print(f"  Total findings: {total_findings}")
        
        for r in result.get("reports", []):
            t = r["target"]
            fcount = r["total_findings"]
            print(f"\n  📦 {t}")
            if fcount > 0:
                sev_counts = {}
                for finding in r.get("findings", []):
                    s = finding.get("severity", "UNKNOWN").upper()
                    sev_counts[s] = sev_counts.get(s, 0) + 1
                sev_str = " | ".join(f"{k}: {v}" for k, v in sorted(sev_counts.items()))
                print(f"     Findings: {fcount} ({sev_str})")
                if r.get("report_file"):
                    print(f"     Report: {r['report_file']}")
            else:
                print(f"     Clean — no findings")
        
        print(f"\n  Reports dir: {result.get('reports_dir', 'N/A')}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
