#!/usr/bin/env python3
"""
marketplace_lister.py — Skill Marketplace Auto-Lister
Pushes Manteclaw's skills to ALL marketplaces with one command.

Usage:
  python3 marketplace_lister.py --status    # Scan current state, no mutations
  python3 marketplace_lister.py --sync      # Push all missing listings
  python3 marketplace_lister.py --missing   # Show gaps only
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────
WORKSPACE = Path("/root/.openclaw/workspace")
SKILLS_DIR = WORKSPACE / "skills-for-sale"
REGISTRY_PATH = WORKSPACE / "marketplace_registry.json"
ENV_PATH = WORKSPACE / ".env"

# ── Load .env ───────────────────────────────────────────────────────
def _load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())

_load_dotenv(ENV_PATH)
# Also load project-specific env files
_load_dotenv(WORKSPACE / "projects" / "meshledger" / ".env")
_load_dotenv(WORKSPACE / "projects" / "0xwork" / ".env")
_load_dotenv(WORKSPACE / ".nookplot.env")
_load_dotenv(WORKSPACE / "nookplot.yaml")  # not a real env, skip if fails

# Marketplace configs

# Marketplace configs

# Marketplace configs
MARKETPLACES = {
    "meshledger": {
        "name": "MeshLedger",
        "enabled": True,
        "env_key": "MESHLEDGER_API_KEY",
        "env_id": "MESHLEDGER_AGENT_ID",
        "endpoint": "https://meshledger.io/api/v1",
    },
    "nookplot": {
        "name": "Nookplot",
        "enabled": True,
        "env_key": "NOOKPLOT_API_KEY",
        "env_id": None,
        "gateway": "https://gateway.nookplot.com",
    },
    "moltlaunch": {
        "name": "MoltLaunch",
        "enabled": False,  # CLI hangs; enable manually with --marketplace moltlaunch
        "cli": "mltl",
        "timeout": 10,
    },
    "0xwork": {
        "name": "0xWork",
        "enabled": False,  # npx hangs; enable manually with --marketplace 0xwork
        "cli": "npx",
        "cli_args": ["-y", "@0xwork/cli"],
        "timeout": 30,
    },
    "openagent": {
        "name": "OpenAgent Market",
        "enabled": True,
        "project_dir": WORKSPACE / "manteclaw",
        "index_file": WORKSPACE / "manteclaw" / "index.ts",
    },
    "mcp_so": {
        "name": "mcp.so",
        "enabled": True,
        "repo": "manteclaw/base-ops",
        "issue_number": 1,  # target issue for skill listing comments
    },
    "glama": {
        "name": "Glama",
        "enabled": True,
        "json_file": WORKSPACE / "glama.json",
    },
}

# ── Skill Data Class ────────────────────────────────────────────────
@dataclass
class Skill:
    name: str
    description: str
    price: float
    currency: str
    tags: list[str]
    marketplaces: list[str]
    source_dir: str
    file_hash: str

    def to_dict(self):
        d = asdict(self)
        return d


# ── Selfheal Retry ────────────────────────────────────────────────
def selfheal_retry(fn, service: str, max_retries: int = 3, base_delay: float = 1.0):
    """Retry wrapper with exponential backoff + jitter."""
    import random
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"  ⚠️ {service} attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(min(delay, 30))
    raise last_err


def shell(cmd: list[str], cwd=None, timeout=30) -> tuple[int, str, str]:
    """Run shell command, return (code, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ── SKILL.md Parser ───────────────────────────────────────────────
def parse_skill_md(path: Path) -> Skill | None:
    """Parse a SKILL.md for name, description, price, tags, marketplaces."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    name = None
    description_lines = []
    price = 0.0
    currency = "USDC"
    tags = []
    marketplaces = []
    in_desc = False
    in_markets = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# Skill:") or stripped.startswith("# Skill -"):
            name = stripped.split(":", 1)[1].strip() if ":" in stripped else stripped.split("-", 1)[1].strip()
        elif stripped.startswith("## Overview"):
            in_desc = True
            continue
        elif stripped.startswith("##") and in_desc:
            in_desc = False
        elif stripped.startswith("## Installation") or stripped.startswith("## Price"):
            in_desc = False
        elif stripped.startswith("## Marketplaces"):
            in_markets = True
            continue
        elif stripped.startswith("##") and in_markets:
            in_markets = False
        elif stripped.startswith("## Tags"):
            in_markets = False
            # Extract tags from this section
            pass
        elif stripped.startswith("## What") or stripped.startswith("## Reference"):
            in_desc = False
            in_markets = False

        if in_desc and stripped and not stripped.startswith("##"):
            description_lines.append(stripped)

        if in_markets and stripped.startswith("-"):
            marketplaces.append(stripped.lstrip("- ").strip().lower())

        # Price parsing
        if "price" in stripped.lower() or "setup:" in stripped.lower() or "per scan:" in stripped.lower():
            m = re.search(r"(\d+(?:\.\d+)?)\s*(USDC|ETH|NOOK|USD)", stripped, re.I)
            if m:
                price = float(m.group(1))
                currency = m.group(2).upper()

        # Tags parsing
        if stripped.startswith("#") and not stripped.startswith("##"):
            words = stripped.split()
            for w in words:
                w = w.strip("#.,")
                if w and w.lower() not in {"skill", "overview", "installation", "price", "marketplaces", "tags"}:
                    if len(w) > 2:
                        tags.append(w.lower())

    # Fallback: extract tags from a dedicated Tags section
    tags_match = re.search(r"## Tags\s*\n(.+?)(?=\n##|\Z)", text, re.S | re.I)
    if tags_match:
        tag_text = tags_match.group(1)
        # Handle backtick-quoted tags like `#defi` `#yield`
        raw_tokens = re.findall(r'`#([^`]+)`', tag_text)
        if raw_tokens:
            tags = [t.strip().lower() for t in raw_tokens if t.strip()]
        else:
            tags = [t.strip().strip("#.,`\"'").lower() for t in tag_text.split() if '#' in t]
    if not tags:
        # Fallback: extract hashtags anywhere in the doc
        tags = list(set(re.findall(r'(?<![\w])#([a-zA-Z0-9_-]+)', text)))
        tags = [t.lower() for t in tags]

    description = " ".join(description_lines[:3])  # first 3 lines
    if not description:
        description = "No description extracted."
    if not name:
        name = path.parent.name

    # Deduplicate tags
    tags = list(dict.fromkeys(tags))

    file_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return Skill(
        name=name,
        description=description,
        price=price,
        currency=currency,
        tags=tags,
        marketplaces=marketplaces,
        source_dir=path.parent.name,
        file_hash=file_hash,
    )


def load_skills() -> list[Skill]:
    """Load all skills from skills-for-sale/."""
    skills = []
    if not SKILLS_DIR.exists():
        print(f"❌ skills-for-sale/ not found at {SKILLS_DIR}")
        return skills

    for subdir in sorted(SKILLS_DIR.iterdir()):
        skill_md = subdir / "SKILL.md"
        if skill_md.exists():
            skill = parse_skill_md(skill_md)
            if skill:
                skills.append(skill)
    return skills


# ── Registry I/O ────────────────────────────────────────────────────
def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except Exception:
            pass
    return {
        "version": 1,
        "last_updated": None,
        "skills": {},  # skill_hash -> { name, listings: {marketplace: status} }
    }


def save_registry(reg: dict):
    reg["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2))


# ── Status Scanners (read-only) ───────────────────────────────────
def status_meshledger(skill: Skill, reg: dict) -> str:
    """Check if skill is listed on MeshLedger."""
    api_key = os.getenv("MESHLEDGER_API_KEY")
    agent_id = os.getenv("MESHLEDGER_AGENT_ID")
    if not api_key or not agent_id:
        return "unconfigured"
    try:
        import requests
        url = f"{MARKETPLACES['meshledger']['endpoint']}/agents/{agent_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return f"error:{resp.status_code}"
        data = resp.json()
        skills_list = data.get("data", {}).get("skills", [])
        for s in skills_list:
            if s.get("name", "").lower() == skill.name.lower():
                return "listed"
        return "missing"
    except ImportError:
        return "no-requests"
    except Exception as e:
        return f"error:{e}"


def status_nookplot(skill: Skill, reg: dict) -> str:
    """Check Nookplot profile for skill mentions."""
    api_key = os.getenv("NOOKPLOT_API_KEY")
    if not api_key:
        return "unconfigured"
    try:
        import requests
        gateway = MARKETPLACES["nookplot"]["gateway"]
        headers = {"Authorization": f"Bearer {api_key}"}
        # Try to get agent profile / services
        resp = requests.get(
            f"{gateway}/api/v1/agents/me",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            profile = resp.json()
            services = profile.get("services", profile.get("skills", []))
            for svc in services:
                if svc.get("name", "").lower() == skill.name.lower():
                    return "listed"
            return "missing"
        # Fallback: check if CLI works
        code, out, err = shell(["nookplot", "status"], timeout=15)
        if code == 0 and skill.name.lower() in out.lower():
            return "listed"
        return "missing"
    except Exception as e:
        return f"error:{e}"


def status_moltlaunch(skill: Skill, reg: dict) -> str:
    """Check MoltLaunch agent gigs."""
    timeout = MARKETPLACES["moltlaunch"].get("timeout", 10)
    try:
        code, out, err = shell(["mltl", "agents", "--id", "46864"], timeout=timeout)
        if code != 0:
            # Try general agents list
            code2, out2, err2 = shell(["mltl", "agents"], timeout=timeout)
            if code2 == 0 and skill.name.lower() in out2.lower():
                return "listed"
            return "missing"
        if skill.name.lower() in out.lower():
            return "listed"
        return "missing"
    except Exception as e:
        return f"error:{e}"


def status_0xwork(skill: Skill, reg: dict) -> str:
    """Check 0xWork profile."""
    timeout = MARKETPLACES["0xwork"].get("timeout", 30)
    try:
        code, out, err = shell(
            ["npx", "-y", "@0xwork/cli", "profile"],
            timeout=timeout,
        )
        if code != 0:
            return f"cli-error:{code}"
        if skill.name.lower() in out.lower():
            return "listed"
        return "missing"
    except Exception as e:
        return f"error:{e}"


def status_openagent(skill: Skill, reg: dict) -> str:
    """Check OpenAgent index.ts skills array."""
    idx = MARKETPLACES["openagent"]["index_file"]
    if not idx.exists():
        return "missing-project"
    text = idx.read_text()
    # Look for skill name in the skills array or onTask handlers
    skill_key = skill.name.lower().replace(" ", "-")
    if skill_key in text.lower() or skill.name.lower() in text.lower():
        return "listed"
    return "missing"


def status_mcp_so(skill: Skill, reg: dict) -> str:
    """Check mcp.so via GitHub issue comments."""
    try:
        import requests
        repo = MARKETPLACES["mcp_so"]["repo"]
        issue = MARKETPLACES["mcp_so"]["issue_number"]
        url = f"https://api.github.com/repos/{repo}/issues/{issue}/comments"
        # Try without auth first (public repo)
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return f"error:{resp.status_code}"
        comments = resp.json()
        for c in comments:
            body = c.get("body", "")
            if skill.name.lower() in body.lower():
                return "listed"
        return "missing"
    except Exception as e:
        return f"error:{e}"


def status_glama(skill: Skill, reg: dict) -> str:
    """Check glama.json for skill entry."""
    gj = MARKETPLACES["glama"]["json_file"]
    if not gj.exists():
        return "missing"
    try:
        data = json.loads(gj.read_text())
        skills = data.get("skills", [])
        for s in skills:
            if s.get("name", "").lower() == skill.name.lower():
                return "listed"
        return "missing"
    except Exception as e:
        return f"error:{e}"


STATUS_SCANNERS = {
    "meshledger": status_meshledger,
    "nookplot": status_nookplot,
    "moltlaunch": status_moltlaunch,
    "0xwork": status_0xwork,
    "openagent": status_openagent,
    "mcp_so": status_mcp_so,
    "glama": status_glama,
}


# ── Sync Pushers (mutating) ───────────────────────────────────────
def sync_meshledger(skill: Skill, reg: dict) -> str:
    """Push skill to MeshLedger."""
    api_key = os.getenv("MESHLEDGER_API_KEY")
    agent_id = os.getenv("MESHLEDGER_AGENT_ID")
    if not api_key or not agent_id:
        return "unconfigured"
    try:
        import requests
        url = f"{MARKETPLACES['meshledger']['endpoint']}/skills"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "agent_id": agent_id,
            "name": skill.name,
            "description": skill.description,
            "price": skill.price,
            "price_token": skill.currency,
            "price_chain": "base",
            "capabilities": skill.tags,
            "estimated_delivery_minutes": 15,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            return "listed"
        return f"failed:{resp.status_code}:{resp.text[:100]}"
    except Exception as e:
        return f"error:{e}"


def sync_nookplot(skill: Skill, reg: dict) -> str:
    """Update Nookplot profile / publish skill as service."""
    # Nookplot doesn't have a direct "list skill" API; best effort via profile update
    try:
        import requests
        gateway = MARKETPLACES["nookplot"]["gateway"]
        api_key = os.getenv("NOOKPLOT_API_KEY")
        if not api_key:
            return "unconfigured"
        # Try nookplot_update_profile MCP tool via direct API
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.patch(
            f"{gateway}/api/v1/agents/me",
            headers=headers,
            json={"services": [{"name": skill.name, "description": skill.description, "price": skill.price}]},
            timeout=15,
        )
        if resp.status_code in (200, 201, 204):
            return "listed"
        # Fallback: use CLI if available
        return "manual-needed"
    except Exception as e:
        return f"error:{e}"


def sync_moltlaunch(skill: Skill, reg: dict) -> str:
    """Create gig on MoltLaunch."""
    try:
        # mltl doesn't seem to have a direct 'gig create' from CLI help;
        # we might need to use the API or browser. Mark as manual.
        return "manual-needed"
    except Exception as e:
        return f"error:{e}"


def sync_0xwork(skill: Skill, reg: dict) -> str:
    """Update 0xWork profile with skills."""
    try:
        code, out, err = shell(
            ["npx", "-y", "@0xwork/cli", "profile", "update", "--skills", ",".join(skill.tags)],
            timeout=60,
        )
        if code == 0:
            return "listed"
        return f"failed:{code}:{err[:200]}"
    except Exception as e:
        return f"error:{e}"


def sync_openagent(skill: Skill, reg: dict) -> str:
    """Update manteclaw/index.ts skills array."""
    idx = MARKETPLACES["openagent"]["index_file"]
    if not idx.exists():
        return "missing-project"
    try:
        text = idx.read_text()
        skill_key = skill.name.lower().replace(" ", "-").replace("_", "-")
        if skill_key in text.lower():
            return "already-listed"
        # Append skill to skills array and add onTask handler
        # Simple heuristic: find skills array line and append
        new_skill_line = f'    "{skill_key}",'
        if 'skills: [' in text:
            text = text.replace(
                'skills: [',
                f'skills: [\n      "{skill_key}",'
            )
        # Add onTask handler before final closing brace or existing handlers
        handler = f'''
agent.onTask("{skill_key}", async (input) => {{
  return {{ message: `Handled {skill_key} with ${{JSON.stringify(input)}}` }};
}});
'''
        # Append before the last closing brace if main() ends there
        if "agent.onTask" in text:
            # Insert after last onTask block
            text = text.rstrip() + "\n" + handler
        else:
            text = text.rstrip() + "\n" + handler
        idx.write_text(text)
        return "listed"
    except Exception as e:
        return f"error:{e}"


def sync_mcp_so(skill: Skill, reg: dict) -> str:
    """Create GitHub issue comment for mcp.so listing."""
    try:
        import requests
        token = os.getenv("GITHUB_TOKEN")
        repo = MARKETPLACES["mcp_so"]["repo"]
        issue = MARKETPLACES["mcp_so"]["issue_number"]
        if not token:
            return "unconfigured"
        url = f"https://api.github.com/repos/{repo}/issues/{issue}/comments"
        headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
        body = f"""## Skill Listing: {skill.name}

**Description:** {skill.description}
**Price:** {skill.price} {skill.currency}
**Tags:** {', '.join(skill.tags)}
**Repo:** https://github.com/{repo}

---
*Auto-posted by marketplace_lister.py*"""
        resp = requests.post(url, headers=headers, json={"body": body}, timeout=15)
        if resp.status_code == 201:
            return "listed"
        return f"failed:{resp.status_code}"
    except Exception as e:
        return f"error:{e}"


def sync_glama(skill: Skill, reg: dict) -> str:
    """Ensure glama.json has skill entry."""
    gj = MARKETPLACES["glama"]["json_file"]
    try:
        if gj.exists():
            data = json.loads(gj.read_text())
        else:
            data = {
                "name": "Manteclaw Agent Utilities",
                "description": "Production-grade Python utilities for AI agent operations.",
                "author": "manteclaw",
                "repository": "https://github.com/manteclaw/base-ops",
                "tags": [],
                "skills": [],
            }
        skills = data.setdefault("skills", [])
        for s in skills:
            if s.get("name", "").lower() == skill.name.lower():
                return "already-listed"
        skills.append({
            "name": skill.name,
            "description": skill.description,
            "file": f"skills-for-sale/{skill.source_dir}/SKILL.md",
            "price": skill.price,
            "currency": skill.currency,
        })
        gj.write_text(json.dumps(data, indent=2))
        return "listed"
    except Exception as e:
        return f"error:{e}"


SYNC_PUSHERS = {
    "meshledger": sync_meshledger,
    "nookplot": sync_nookplot,
    "moltlaunch": sync_moltlaunch,
    "0xwork": sync_0xwork,
    "openagent": sync_openagent,
    "mcp_so": sync_mcp_so,
    "glama": sync_glama,
}


# ── Main Commands ───────────────────────────────────────────────────
def run_status(skills: list[Skill]) -> dict:
    """Scan all marketplaces for current listing state."""
    reg = load_registry()
    results = {}
    print(f"\n📊 STATUS SCAN — {len(skills)} skills × {len(STATUS_SCANNERS)} marketplaces\n", flush=True)

    for skill in skills:
        print(f"🔹 {skill.name} (${skill.price} {skill.currency})", flush=True)
        skill_key = f"{skill.source_dir}:{skill.file_hash}"
        reg_entry = reg["skills"].setdefault(skill_key, {"name": skill.name, "listings": {}})
        skill_results = {}

        for mp_key, scanner in STATUS_SCANNERS.items():
            mp_name = MARKETPLACES[mp_key]["name"]
            if not MARKETPLACES[mp_key].get("enabled", True):
                status = "disabled"
            else:
                try:
                    status = selfheal_retry(
                        lambda: scanner(skill, reg),
                        service=f"{mp_name}-status",
                        max_retries=2,
                    )
                except Exception as e:
                    status = f"error:{e}"
            skill_results[mp_key] = status
            reg_entry["listings"][mp_key] = status
            icon = "✅" if status == "listed" else "❌" if status == "missing" else "⚠️"
            print(f"   {icon} {mp_name}: {status}", flush=True)

        results[skill.name] = skill_results
        print(flush=True)

    save_registry(reg)
    return results


def run_missing(skills: list[Skill]) -> dict:
    """Show only gaps (skills not listed on a marketplace)."""
    status_results = run_status(skills)
    print("\n🚨 GAPS (missing listings only)\n")
    gaps = {}
    for skill_name, mp_results in status_results.items():
        missing = [mp for mp, st in mp_results.items() if st == "missing"]
        if missing:
            gaps[skill_name] = missing
            print(f"🔹 {skill_name}: missing on {', '.join(missing)}")
    if not gaps:
        print("🎉 No gaps! All skills listed on all reachable marketplaces.")
    return gaps


def run_sync(skills: list[Skill]) -> dict:
    """Push all missing skills to all marketplaces."""
    reg = load_registry()
    print(f"\n🚀 SYNC — Pushing {len(skills)} skills to marketplaces\n")
    results = {}

    for skill in skills:
        print(f"🔹 {skill.name}")
        skill_key = f"{skill.source_dir}:{skill.file_hash}"
        reg_entry = reg["skills"].setdefault(skill_key, {"name": skill.name, "listings": {}})
        skill_results = {}

        for mp_key, pusher in SYNC_PUSHERS.items():
            mp_name = MARKETPLACES[mp_key]["name"]
            if not MARKETPLACES[mp_key].get("enabled", True):
                status = "disabled"
            else:
                current = reg_entry["listings"].get(mp_key, "unknown")
                if current == "listed":
                    status = "already-listed"
                else:
                    try:
                        status = selfheal_retry(
                            lambda: pusher(skill, reg),
                            service=f"{mp_name}-sync",
                            max_retries=2,
                        )
                    except Exception as e:
                        status = f"error:{e}"
            skill_results[mp_key] = status
            reg_entry["listings"][mp_key] = status
            icon = "✅" if status in ("listed", "already-listed") else "⚠️"
            print(f"   {icon} {mp_name}: {status}")

        results[skill.name] = skill_results
        print()

    save_registry(reg)
    return results


def print_summary(results: dict):
    """Print a summary table of all results."""
    print("\n📋 SUMMARY\n")
    print(f"{'Skill':<35} {'Marketplace':<18} {'Status'}")
    print("-" * 80)
    for skill_name, mp_results in results.items():
        for mp_key, status in mp_results.items():
            mp_name = MARKETPLACES.get(mp_key, {}).get("name", mp_key)
            print(f"{skill_name:<35} {mp_name:<18} {status}")
        print()


# ── CLI ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Skill Marketplace Auto-Lister for Manteclaw"
    )
    parser.add_argument("--status", action="store_true", help="Scan current listing state (read-only)")
    parser.add_argument("--sync", action="store_true", help="Push all missing skills to marketplaces")
    parser.add_argument("--missing", action="store_true", help="Show only gaps")
    parser.add_argument("--marketplace", type=str, help="Target only one marketplace (key)")
    args = parser.parse_args()

    skills = load_skills()
    if not skills:
        print("❌ No skills found in skills-for-sale/")
        sys.exit(1)

    print(f"✅ Loaded {len(skills)} skills from skills-for-sale/", flush=True)

    # Filter to single marketplace if requested
    if args.marketplace:
        mp = args.marketplace
        if mp not in STATUS_SCANNERS:
            print(f"❌ Unknown marketplace: {mp}. Valid: {', '.join(STATUS_SCANNERS.keys())}", flush=True)
            sys.exit(1)
        # Temporarily disable others
        for k in MARKETPLACES:
            MARKETPLACES[k]["enabled"] = (k == mp)

    if args.status:
        results = run_status(skills)
        print_summary(results)
    elif args.missing:
        run_missing(skills)
    elif args.sync:
        results = run_sync(skills)
        print_summary(results)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
