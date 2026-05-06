#!/usr/bin/env python3
"""
GitHub Actions API utility for Manteclaw
Trigger workflows, monitor runs, manage secrets
"""

import requests
import json
import sys
import os

OWNER = "manteclaw"
REPO = "litcoiin-solutions"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def list_workflows():
    """List all workflows in the repo"""
    url = f"{BASE_URL}/actions/workflows"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()
    workflows = data.get("workflows", [])
    print(f"\n📋 Workflows in {OWNER}/{REPO}:")
    for wf in workflows:
        print(f"  {wf['id']}: {wf['name']} ({wf['state']})")
        print(f"    Path: {wf['path']}")
    return workflows

def trigger_workflow(workflow_id, ref="main", inputs=None):
    """Trigger a workflow run"""
    url = f"{BASE_URL}/actions/workflows/{workflow_id}/dispatches"
    payload = {"ref": ref}
    if inputs:
        payload["inputs"] = inputs
    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code == 204:
        print(f"✅ Workflow {workflow_id} triggered on {ref}")
        return True
    else:
        print(f"❌ Failed: {resp.status_code} - {resp.text}")
        return False

def list_runs(workflow_id=None, status=None):
    """List recent workflow runs"""
    url = f"{BASE_URL}/actions/runs"
    params = {}
    if workflow_id:
        params["workflow_id"] = workflow_id
    if status:
        params["status"] = status
    resp = requests.get(url, headers=HEADERS, params=params)
    data = resp.json()
    runs = data.get("workflow_runs", [])
    print(f"\n🏃 Recent Runs:")
    for run in runs[:10]:
        print(f"  #{run['run_number']}: {run['name']} — {run['status']} ({run['conclusion'] or 'in_progress'})")
        print(f"    Branch: {run['head_branch']} | Started: {run['created_at']}")
    return runs

def get_run_logs(run_id):
    """Get logs for a specific run"""
    url = f"{BASE_URL}/actions/runs/{run_id}/logs"
    resp = requests.get(url, headers=HEADERS)
    print(f"Logs URL: {resp.url}")
    return resp

if __name__ == "__main__":
    if not TOKEN:
        print("❌ GITHUB_TOKEN not set")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print("Usage: python github_actions.py <command> [args]")
        print("Commands: list, trigger <workflow_id>, runs [workflow_id], logs <run_id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "list":
        list_workflows()
    elif cmd == "trigger":
        if len(sys.argv) < 3:
            print("Usage: github_actions.py trigger <workflow_id>")
            sys.exit(1)
        trigger_workflow(sys.argv[2])
    elif cmd == "runs":
        wf_id = sys.argv[2] if len(sys.argv) > 2 else None
        list_runs(wf_id)
    elif cmd == "logs":
        if len(sys.argv) < 3:
            print("Usage: github_actions.py logs <run_id>")
            sys.exit(1)
        get_run_logs(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
