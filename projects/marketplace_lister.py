#!/usr/bin/env python3
"""
Marketplace Auto-Lister v1.0
Pushes skill packages to all configured marketplaces with metadata.

Usage:
    python3 marketplace_lister.py --skill multi-provider-llm-router --marketplace all
"""

import os
import sys
import json
import glob
from pathlib import Path

MARKETPLACES = {
    "meshledger": {"url": "https://meshledger.ai/api/v1/skills", "auth": "MESHLEDGER_API_KEY"},
    "nookplot": {"url": "https://nookplot.com/api/v1/marketplace/skills", "auth": "NOOKPLOT_API_KEY"},
    "smithery": {"url": "https://smithery.ai/api/skills", "auth": "SMITHERY_API_KEY"},
    "mcp.so": {"url": "https://mcp.so/api/skills", "auth": "MCPSO_API_KEY"},
    "clawhub": {"url": "https://clawhub.ai/api/v1/skills", "auth": "CLAWHUB_API_KEY"},
    "mulerun": {"url": "https://mulerun.com/api/agents/skills", "auth": "MULERUN_API_KEY"},
    "swarmzero": {"url": "https://api.swarmzero.ai/v1/skills", "auth": "SWARMZERO_API_KEY"},
}

SKILLS_DIR = Path("/root/.openclaw/workspace/projects/skills")

def load_skill(skill_name: str) -> dict:
    skill_path = SKILLS_DIR / skill_name / "skill.json"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill {skill_name} not found at {skill_path}")
    with open(skill_path) as f:
        return json.load(f)

def list_skills() -> list:
    return [d.name for d in SKILLS_DIR.iterdir() if (d / "skill.json").exists()]

def push_skill(skill: dict, marketplace: str) -> dict:
    config = MARKETPLACES.get(marketplace)
    if not config:
        return {"success": False, "error": f"Unknown marketplace: {marketplace}"}
    
    api_key = os.environ.get(config["auth"], "")
    if not api_key:
        return {"success": False, "error": f"Missing {config['auth']} env var"}
    
    # For now, just log what would be sent
    payload = {
        "name": skill["name"],
        "version": skill["version"],
        "description": skill["description"],
        "price": skill.get("price", 0),
        "currency": skill.get("currency", "USDC"),
        "tags": skill.get("tags", []),
        "entry_point": skill.get("entry_point"),
    }
    
    print(f"[{marketplace}] Would POST to {config['url']}")
    print(f"  Payload: {json.dumps(payload, indent=2)[:200]}...")
    return {"success": True, "marketplace": marketplace, "payload": payload}

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 marketplace_lister.py [--list | --skill <name> --marketplace <name|all>]")
        print(f"\nAvailable skills: {', '.join(list_skills())}")
        print(f"Available marketplaces: {', '.join(MARKETPLACES.keys())}")
        return
    
    if sys.argv[1] == "--list":
        skills = list_skills()
        for s in skills:
            meta = load_skill(s)
            print(f"  {s}: {meta['name']} ({meta.get('price', 0)} {meta.get('currency', 'USDC')})")
        return
    
    if sys.argv[1] == "--skill":
        skill_name = sys.argv[2]
        skill = load_skill(skill_name)
        marketplace = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--marketplace" else "all"
        
        if marketplace == "all":
            for mp in skill.get("marketplaces", list(MARKETPLACES.keys())):
                result = push_skill(skill, mp)
                print(json.dumps(result, indent=2))
        else:
            result = push_skill(skill, marketplace)
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
