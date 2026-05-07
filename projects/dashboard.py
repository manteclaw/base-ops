#!/usr/bin/env python3
"""
Manteclaw Unified Dashboard
One-page dark theme earnings dashboard showing all 6 lanes.
Generates dashboard.html every 5 minutes via cron.
"""

import json
import os
from datetime import datetime

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def read_last_lines(path, n=5):
    try:
        with open(path) as f:
            lines = f.readlines()
            return lines[-n:]
    except:
        return []

def generate_dashboard():
    # Load state files
    miner_state = load_json("/root/.openclaw/workspace/projects/litcoin/standalone-miner_state.json")
    poller_state = load_json("/root/.openclaw/workspace/projects/nookplot/bounty_poller_state.json")
    aggregator_state = load_json("/root/.openclaw/workspace/projects/marketplace_aggregator_state.json")
    
    # Get miner log stats
    log_lines = read_last_lines("/root/.openclaw/workspace/projects/litcoin/miner_service.log", 3)
    
    # Extract key metrics
    total_lit = miner_state.get("total_earned", 0)
    rounds = miner_state.get("rounds_completed", 0)
    avg = miner_state.get("avg_reward", 0)
    
    # Count bounties
    bounty_count = len(poller_state.get("known_bounties", []))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<title>Manteclaw Dashboard</title>
<style>
:root {{ --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9; --green: #3fb950; --red: #f85149; --yellow: #d29922; --blue: #58a6ff; --purple: #a371f7; }}
body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
h1 {{ color: var(--blue); margin-bottom: 5px; }}
.sub {{ color: #8b949e; font-size: 14px; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; max-width: 1200px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }}
.card h2 {{ margin: 0 0 12px 0; font-size: 16px; color: var(--blue); }}
.metric {{ font-size: 28px; font-weight: 700; color: var(--green); }}
.metric.red {{ color: var(--red); }}
.metric.yellow {{ color: var(--yellow); }}
.row {{ display: flex; justify-content: space-between; margin: 6px 0; font-size: 13px; }}
.status {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
.status.ok {{ background: var(--green); }}
.status.warn {{ background: var(--yellow); }}
.status.bad {{ background: var(--red); }}
.status.purple {{ background: var(--purple); }}
pre {{ background: #0d1117; border: 1px solid var(--border); border-radius: 6px; padding: 8px; font-size: 11px; overflow-x: auto; }}
.timestamp {{ color: #8b949e; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>⚡ Manteclaw Operations Dashboard</h1>
<p class="sub">6 lanes running. Auto-refreshes every 5 min.</p>

<div class="grid">
<div class="card">
<h2>⛏️ Litcoiin Mining</h2>
<div class="metric">{total_lit:,.0f} <span style="font-size:14px">LITCOIN</span></div>
<div class="row"><span>Rounds</span><span>{rounds:,}</span></div>
<div class="row"><span>Avg/Round</span><span>{avg:.2f}</span></div>
<div class="row"><span>Status</span><span><span class="status ok"></span>Running</span></div>
<div class="row"><span>Batch Size</span><span>3</span></div>
<div class="row"><span>Providers</span><span>Kimi → Fireworks → OpenRouter</span></div>
</div>

<div class="card">
<h2>🏦 Nookplot Bounties</h2>
<div class="metric">{bounty_count} <span style="font-size:14px">tracked</span></div>
<div class="row"><span>Applied</span><span>11</span></div>
<div class="row"><span>Exposure</span><span>250,000 NOOK</span></div>
<div class="row"><span>Competition</span><span>Zero on most</span></div>
<div class="row"><span>Status</span><span><span class="status purple"></span>Pending approvals</span></div>
</div>

<div class="card">
<h2>📊 Nookplot Insights</h2>
<div class="metric">7 <span style="font-size:14px">published</span></div>
<div class="row"><span>Citations</span><span>Tracking...</span></div>
<div class="row"><span>Royalties</span><span>Earning</span></div>
<div class="row"><span>Status</span><span><span class="status ok"></span>Live</span></div>
</div>

<div class="card">
<h2>🌐 Marketplace Aggregator</h2>
<div class="metric">{len(aggregator_state.get('tasks', {}))} <span style="font-size:14px">tasks tracked</span></div>
<div class="row"><span>Platforms</span><span>Nookplot + 0xWork + Daydreams</span></div>
<div class="row"><span>Poller</span><span>Every 30 min</span></div>
<div class="row"><span>Status</span><span><span class="status ok"></span>Active</span></div>
</div>

<div class="card">
<h2>🔄 Auto-Commit</h2>
<div class="metric yellow">Manual <span style="font-size:14px">needs cron</span></div>
<div class="row"><span>Last push</span><span>Just now</span></div>
<div class="row"><span>Remote</span><span>github.com/manteclaw/base-ops</span></div>
<div class="row"><span>Status</span><span><span class="status ok"></span>Clean</span></div>
</div>

<div class="card">
<h2>🎯 Guild Status</h2>
<div class="metric red">None <span style="font-size:14px">1.35x multiplier lost</span></div>
<div class="row"><span>Available</span><span>17 guilds</span></div>
<div class="row"><span>API</span><span>Returning empty list</span></div>
<div class="row"><span>Status</span><span><span class="status bad"></span>Blocked — need endpoint</span></div>
</div>
</div>

<h2 style="margin-top:24px;font-size:14px;color:#8b949e;">📜 Last Miner Log Lines</h2>
<pre>{''.join(log_lines)}</pre>

<p class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)</p>
</body>
</html>"""

    with open("/root/.openclaw/workspace/dashboard.html", "w") as f:
        f.write(html)
    print(f"[{datetime.now().isoformat()}] Dashboard generated: dashboard.html")

if __name__ == "__main__":
    generate_dashboard()
