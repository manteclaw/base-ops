#!/usr/bin/env python3
"""
Manteclaw Revenue Tracker — Unified earnings aggregation across all lanes.
Reads state files from each lane and produces a single JSON snapshot.

Lanes:
  A — Litcoiin Mining (standalone-miner_state.json)
  B — Nookplot Bounties (bounty_poller_state.json + bounty_submissions.json)
  C — Nookplot Insights (insight_publish_results.json)
  D — Arbitrage Bot (arbitrage_log.txt)
  E — Skill Marketplace (marketplace_aggregator_state.json)
  F — Yield Farming (yield/last_scan.json)

Usage:
    python3 revenue_tracker.py           # Generate snapshot
    python3 revenue_tracker.py --watch   # Continuous mode (every 60s)
    python3 revenue_tracker.py --html    # Also regenerate dashboard.html
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
SNAP_FILE = WORKSPACE / "projects" / "revenue_snapshot.json"
LOG_FILE = WORKSPACE / "projects" / "revenue_history.jsonl"

# ── Helpers ──

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def read_last_lines(path, n=20):
    try:
        with open(path) as f:
            lines = f.readlines()
            return lines[-n:]
    except Exception:
        return []


def parse_arbitrage_log(lines):
    """Extract trades and PnL from arbitrage log."""
    trades = []
    total_pnl = 0.0
    trade_count = 0
    for line in lines:
        # Match: "💰 EXECUTED: BUY 100.5 USDC @ 0.00321 ETH → SELL @ 0.00325 ETH | PnL: +0.0012 ETH"
        m = re.search(r"PnL:\s*([+-]?[\d.]+)\s*ETH", line)
        if m:
            pnl = float(m.group(1))
            trades.append({"pnl_eth": pnl, "line": line.strip()})
            total_pnl += pnl
            trade_count += 1
        # Also match "📊 Session PnL: +0.0045 ETH (3 trades)"
        m2 = re.search(r"Session PnL:\s*([+-]?[\d.]+)\s*ETH\s*\((\d+)\s*trades\)", line)
        if m2:
            total_pnl = float(m2.group(1))
            trade_count = int(m2.group(2))
    return {
        "trade_count": trade_count,
        "total_pnl_eth": round(total_pnl, 6),
        "recent_trades": trades[-5:],
    }


def parse_miner_log(lines):
    """Extract recent earnings from miner service log."""
    rewards = []
    for line in lines:
        m = re.search(r"Reward:\s*([\d.]+)", line)
        if m:
            rewards.append(float(m.group(1)))
    return rewards


def estimate_daily_lit(avg_per_round, log_lines):
    """Estimate daily LIT production from recent log activity."""
    rewards = parse_miner_log(log_lines)
    if len(rewards) >= 3:
        last_10_avg = sum(rewards[-10:]) / min(len(rewards), 10)
        # Count rounds in the log sample to estimate rounds/hour
        round_lines = [l for l in log_lines if "Round " in l and "Reward:" in l]
        if len(round_lines) >= 2:
            # At 3s base + some overhead, ~10-20 rounds/min = 600-1200/hr
            # Use a conservative 10 rounds/min = 14,400/day
            return last_10_avg * 14400
    # Fallback: use historical avg per round * conservative daily rounds
    return avg_per_round * 7200  # ~5 rounds/min average with backoff


def parse_nookplot_mining_log(lines):
    """Extract NOOK earnings from nookplot miner log."""
    total_nook = 0.0
    for line in lines:
        m = re.search(r"earned\s*([\d.]+)\s*NOOK", line, re.I)
        if m:
            total_nook += float(m.group(1))
        m2 = re.search(r"reward\s*[:=]\s*([\d.]+)", line, re.I)
        if m2:
            total_nook += float(m2.group(1))
    return round(total_nook, 2)


# ── Lane Readers ──

def lane_litcoiin():
    state = load_json(WORKSPACE / "projects" / "litcoin" / "standalone-miner_state.json")
    log_lines = read_last_lines(WORKSPACE / "projects" / "litcoin" / "miner_service.log", 500)
    recent_rewards = parse_miner_log(log_lines)
    
    total_earned = state.get("total_earned", 0)
    rounds = state.get("round_count", 0)
    avg = total_earned / max(1, rounds)
    daily_est = estimate_daily_lit(avg, log_lines)
    
    # Best model / best hour for analytics
    model_tracker = state.get("model_tracker", {})
    best_task = None
    best_avg = 0
    for task, models in model_tracker.items():
        for model, stats in models.items():
            if stats.get("count", 0) >= 5 and stats.get("avg", 0) > best_avg:
                best_avg = stats["avg"]
                best_task = task
    
    hourly = state.get("hourly_stats", {})
    best_hour = None
    best_hour_avg = 0
    for h, s in hourly.items():
        if s.get("count", 0) >= 10:
            ha = s["total"] / s["count"]
            if ha > best_hour_avg:
                best_hour_avg = ha
                best_hour = h
    
    return {
        "lane": "A",
        "name": "Litcoiin Mining",
        "status": "active",
        "balance_lit": round(total_earned, 0),
        "rounds": rounds,
        "avg_per_round": round(avg, 2),
        "best_task_type": best_task,
        "best_task_avg": round(best_avg, 2),
        "best_hour": f"{best_hour}:00" if best_hour else None,
        "best_hour_avg": round(best_hour_avg, 2),
        "recent_rewards": recent_rewards[-10:],
        "claim_threshold": 50000,
        "claim_ready": total_earned >= 50000,
        "providers": ["fireworks", "kimi", "nvidia"],
        "estimated_daily_lit": round(daily_est, 0),
    }


def lane_nookplot_bounties():
    state = load_json(WORKSPACE / "projects" / "nookplot" / "bounty_poller_state.json")
    apps = load_json(WORKSPACE / "projects" / "nookplot" / "bounty_applications.json")
    subs = load_json(WORKSPACE / "projects" / "nookplot" / "bounty_submissions.json")
    
    known = state.get("known_bounties", [])
    applied_count = len(apps) if isinstance(apps, list) else 0
    submitted_count = len(subs) if isinstance(subs, list) else 0
    
    # Total potential exposure (sum of rewards on tracked bounties with zero competition)
    aggregator = load_json(WORKSPACE / "projects" / "marketplace_aggregator_state.json")
    exposure = 0.0
    zero_comp = 0
    for tid, task in aggregator.get("tasks", {}).items():
        if task.get("competition", 99) == 0:
            exposure += task.get("reward", 0)
            zero_comp += 1
    
    return {
        "lane": "B",
        "name": "Nookplot Bounties",
        "status": "active",
        "tracked_bounties": len(known),
        "applied": applied_count,
        "submitted": submitted_count,
        "zero_competition_bounties": zero_comp,
        "potential_exposure_nook": round(exposure, 0),
        "platforms": ["nookplot"],
    }


def lane_nookplot_insights():
    results = load_json(WORKSPACE / "projects" / "nookplot" / "insight_publish_results.json")
    if not results:
        return {"lane": "C", "name": "Nookplot Insights", "status": "idle", "published": 0}
    
    published = 0
    failed = 0
    cids = []
    for title, res in results.items():
        if res.get("success"):
            published += 1
            cids.append(res.get("id", "unknown"))
        else:
            failed += 1
    
    # Parse miner log for NOOK earnings
    log_lines = read_last_lines(WORKSPACE / "projects" / "nookplot" / "nookplot-miner.log", 100)
    nook_earned = parse_nookplot_mining_log(log_lines)
    
    return {
        "lane": "C",
        "name": "Nookplot Insights",
        "status": "active" if published > 0 else "idle",
        "published": published,
        "failed": failed,
        "cids": cids,
        "estimated_nook_earned": nook_earned,
    }


def lane_arbitrage():
    log_lines = read_last_lines(WORKSPACE / "projects" / "arbitrage" / "arbitrage_log.txt", 100)
    parsed = parse_arbitrage_log(log_lines)
    
    # Also read config for wallet / reserve info
    config = load_json(WORKSPACE / "projects" / "arbitrage" / "config.json")
    
    return {
        "lane": "D",
        "name": "Base L2 Arbitrage",
        "status": "active" if parsed["trade_count"] > 0 else "warming",
        "trades_executed": parsed["trade_count"],
        "total_pnl_eth": parsed["total_pnl_eth"],
        "recent_trades": parsed["recent_trades"],
        "wallet": config.get("wallet", "0x8b8AAC89E101b77E5A917278120151FC496e5c39"),
        "reserve_eth": config.get("reserve", 0.0025),
    }


def lane_marketplace():
    agg = load_json(WORKSPACE / "projects" / "marketplace_aggregator_state.json")
    tasks = agg.get("tasks", {})
    
    # Count by platform
    platforms = {}
    total_reward = 0.0
    for tid, t in tasks.items():
        plat = t.get("platform", "unknown")
        platforms[plat] = platforms.get(plat, 0) + 1
        total_reward += t.get("reward", 0)
    
    # Check registration packages
    reg_dirs = []
    reg_base = WORKSPACE / "projects" / "marketplace-registrations"
    if reg_base.exists():
        for d in reg_base.iterdir():
            if d.is_dir():
                reg_dirs.append(d.name)
    
    return {
        "lane": "E",
        "name": "Skill Marketplace",
        "status": "active",
        "tracked_tasks": len(tasks),
        "platforms": platforms,
        "total_potential_reward": round(total_reward, 0),
        "registered_marketplaces": reg_dirs,
    }


def lane_yield():
    scan = load_json(WORKSPACE / "projects" / "yield" / "last_scan.json")
    if not scan:
        return {"lane": "F", "name": "Yield Farming", "status": "idle"}
    
    best = scan.get("best_pool", {})
    top = scan.get("top_pools", [])
    
    return {
        "lane": "F",
        "name": "Yield Farming",
        "status": "active",
        "chain": scan.get("chain", "Base"),
        "token": scan.get("token", "USDC"),
        "pools_found": scan.get("pools_found", 0),
        "best_apy": round(best.get("apy", 0), 2),
        "best_protocol": best.get("protocol", "unknown"),
        "best_symbol": best.get("symbol", "unknown"),
        "best_tvl": round(best.get("tvl_usd", 0), 0),
        "top_pools": [
            {"protocol": p.get("protocol"), "symbol": p.get("symbol"), "apy": round(p.get("apy", 0), 2)}
            for p in top[:5]
        ],
    }


# ── Core ──

def build_snapshot():
    lanes = [
        lane_litcoiin(),
        lane_nookplot_bounties(),
        lane_nookplot_insights(),
        lane_arbitrage(),
        lane_marketplace(),
        lane_yield(),
    ]
    
    # Totals
    total_lit = lanes[0]["balance_lit"]
    total_nook_exposure = lanes[1]["potential_exposure_nook"]
    total_pnl_eth = lanes[3]["total_pnl_eth"]
    
    # Estimate daily/weekly from hourly stats
    hourly = load_json(WORKSPACE / "projects" / "litcoin" / "standalone-miner_state.json").get("hourly_stats", {})
    daily_est = 0
    for h, s in hourly.items():
        daily_est += s.get("total", 0)
    # Use the log-based estimate from lane_litcoiin
    daily_est_lit = lanes[0].get("estimated_daily_lit", 0)
    
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lanes": {l["lane"]: l for l in lanes},
        "summary": {
            "total_lit_pending": total_lit,
            "total_nook_exposure": total_nook_exposure,
            "total_pnl_eth": total_pnl_eth,
            "active_lanes": sum(1 for l in lanes if l["status"] in ("active", "warming")),
            "claim_ready": lanes[0]["claim_ready"],
            "estimated_daily_lit": round(daily_est_lit, 0),
        },
    }
    return snapshot


def write_snapshot(snap):
    SNAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAP_FILE, "w") as f:
        json.dump(snap, f, indent=2)
    
    # Append to history log
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": snap["timestamp"],
            "total_lit": snap["summary"]["total_lit_pending"],
            "total_pnl_eth": snap["summary"]["total_pnl_eth"],
            "active_lanes": snap["summary"]["active_lanes"],
        }) + "\n")


def generate_html_dashboard(snapshot):
    """Generate a self-contained dark-theme HTML dashboard."""
    lanes = snapshot["lanes"]
    summary = snapshot["summary"]
    ts = snapshot["timestamp"]
    
    def card(title, icon, content, status="ok"):
        status_color = {"ok": "#3fb950", "warn": "#d29922", "bad": "#f85149", "purple": "#a371f7"}.get(status, "#3fb950")
        return f"""
        <div class="card">
            <h2><span class="status" style="background:{status_color}"></span>{icon} {title}</h2>
            {content}
        </div>
        """
    
    def metric(value, unit=""):
        return f'<div class="metric">{value} <span class="unit">{unit}</span></div>'
    
    def row(left, right):
        return f'<div class="row"><span>{left}</span><span>{right}</span></div>'
    
    # ── Build cards ──
    
    # Lane A: Litcoiin
    a = lanes["A"]
    a_content = metric(f"{a['balance_lit']:,.0f}", "LITCOIN")
    a_content += row("Rounds", f"{a['rounds']:,}")
    a_content += row("Avg/Round", f"{a['avg_per_round']:.2f}")
    a_content += row("Best Task", f"{a['best_task_type'] or 'N/A'} ({a['best_task_avg']:.1f})")
    a_content += row("Best Hour", f"{a['best_hour'] or 'N/A'} ({a['best_hour_avg']:.1f})")
    a_content += row("Claim Ready", "✅ YES" if a['claim_ready'] else "⏳ No")
    a_content += row("Providers", ", ".join(a['providers']))
    a_status = "ok" if a['claim_ready'] else "warn"
    
    # Lane B: Nookplot Bounties
    b = lanes["B"]
    b_content = metric(f"{b['tracked_bounties']}", "tracked")
    b_content += row("Applied", str(b['applied']))
    b_content += row("Submitted", str(b['submitted']))
    b_content += row("Zero-Comp", str(b['zero_competition_bounties']))
    b_content += row("Exposure", f"{b['potential_exposure_nook']:,.0f} NOOK")
    b_status = "purple"
    
    # Lane C: Nookplot Insights
    c = lanes["C"]
    c_content = metric(str(c['published']), "published")
    c_content += row("Failed", str(c.get('failed', 0)))
    c_content += row("Est. NOOK", f"{c.get('estimated_nook_earned', 0):,.0f}")
    c_content += row("CIDs", f"{len(c.get('cids', []))} stored")
    c_status = "ok" if c['published'] > 0 else "warn"
    
    # Lane D: Arbitrage
    d = lanes["D"]
    d_content = metric(f"{d['total_pnl_eth']:.4f}", "ETH")
    d_content += row("Trades", str(d['trades_executed']))
    d_content += row("Reserve", f"{d['reserve_eth']} ETH")
    if d['recent_trades']:
        last = d['recent_trades'][-1]
        d_content += row("Last Trade", f"{last['pnl_eth']:+.4f} ETH")
    d_status = "ok" if d['trades_executed'] > 0 else "warn"
    
    # Lane E: Marketplace
    e = lanes["E"]
    e_content = metric(str(e['tracked_tasks']), "tasks")
    e_content += row("Platforms", ", ".join(f"{k}:{v}" for k,v in e.get('platforms', {}).items()))
    e_content += row("Potential", f"{e['total_potential_reward']:,.0f} NOOK")
    e_content += row("Registered", ", ".join(e.get('registered_marketplaces', [])))
    e_status = "ok"
    
    # Lane F: Yield
    f = lanes["F"]
    if f['status'] == 'idle':
        f_content = metric("—", "scan needed")
        f_content += row("Status", "Idle")
        f_status = "warn"
    else:
        f_content = metric(f"{f['best_apy']:,.0f}%", "APY")
        f_content += row("Protocol", f['best_protocol'])
        f_content += row("Pool", f['best_symbol'])
        f_content += row("TVL", f"${f['best_tvl']:,.0f}")
        f_content += row("Pools", str(f['pools_found']))
        f_status = "ok"
    
    # Summary bar
    summary_html = f"""
    <div class="summary-bar">
        <div class="summary-item">
            <div class="summary-value">{summary['total_lit_pending']:,.0f}</div>
            <div class="summary-label">LITCOIN Pending</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary['total_pnl_eth']:.4f}</div>
            <div class="summary-label">ETH PnL</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary['total_nook_exposure']:,.0f}</div>
            <div class="summary-label">NOOK Exposure</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary['active_lanes']}/6</div>
            <div class="summary-label">Active Lanes</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">{summary['estimated_daily_lit']:,.0f}</div>
            <div class="summary-label">Est. Daily LIT</div>
        </div>
    </div>
    """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manteclaw Revenue Dashboard</title>
<style>
:root {{
  --bg: #0a0c10;
  --surface: #11141a;
  --card: #161b22;
  --border: #2a2f3a;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #3fb950;
  --red: #f85149;
  --yellow: #d29922;
  --blue: #58a6ff;
  --purple: #a371f7;
  --cyan: #39d0d8;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 24px;
  line-height: 1.5;
}}
h1 {{
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
}}
h1 .emoji {{ font-size: 28px; }}
.sub {{
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 20px;
}}
.summary-bar {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}}
.summary-item {{
  background: linear-gradient(135deg, var(--surface) 0%, var(--card) 100%);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}}
.summary-value {{
  font-size: 24px;
  font-weight: 700;
  color: var(--green);
}}
.summary-label {{
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  max-width: 1400px;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  transition: border-color 0.2s;
}}
.card:hover {{ border-color: var(--blue); }}
.card h2 {{
  font-size: 14px;
  font-weight: 600;
  color: var(--blue);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.status {{
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.metric {{
  font-size: 32px;
  font-weight: 700;
  color: var(--green);
  margin-bottom: 12px;
}}
.metric .unit {{
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
}}
.row {{
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.row:last-child {{ border-bottom: none; }}
.row span:first-child {{ color: var(--muted); }}
.row span:last-child {{ color: var(--text); font-weight: 500; }}
.timestamp {{
  color: var(--muted);
  font-size: 11px;
  margin-top: 24px;
  text-align: center;
}}
.history-chart {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  margin-top: 20px;
  max-width: 1400px;
}}
.history-chart h2 {{
  font-size: 14px;
  color: var(--purple);
  margin-bottom: 12px;
}}
pre {{
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 10px;
  color: var(--muted);
  overflow-x: auto;
  white-space: pre-wrap;
}}
a {{ color: var(--blue); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
@media (max-width: 600px) {{
  body {{ padding: 12px; }}
  .grid {{ grid-template-columns: 1fr; }}
  .summary-bar {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<h1><span class="emoji">⚡</span>Manteclaw Revenue Dashboard</h1>
<p class="sub">6 earning lanes · Auto-refreshes every 60s · {ts}</p>

{summary_html}

<div class="grid">
{card("Litcoiin Mining", "⛏️", a_content, a_status)}
{card("Nookplot Bounties", "🏦", b_content, b_status)}
{card("Nookplot Insights", "📊", c_content, c_status)}
{card("Base L2 Arbitrage", "🔄", d_content, d_status)}
{card("Skill Marketplace", "🌐", e_content, e_status)}
{card("Yield Farming", "💰", f_content, f_status)}
</div>

<div class="history-chart">
<h2>📈 Revenue History (last 20 snapshots)</h2>
<pre id="history">Loading...</pre>
</div>

<p class="timestamp">Last updated: {ts} UTC · Generated by revenue_tracker.py</p>

<script>
// Simple sparkline from revenue_history.jsonl if accessible
fetch('revenue_history.jsonl')
  .then(r => r.text())
  .then(text => {{
    const lines = text.trim().split('\n').slice(-20);
    const data = lines.map(l => JSON.parse(l));
    let out = 'Date        LITCOIN    ETH-PnL    Lanes\\n';
    out += '-------------------------------------------\\n';
    data.forEach(d => {{
      const dt = d.timestamp.slice(0,10);
      const lit = String(Math.round(d.total_lit)).padStart(10);
      const eth = String(d.total_pnl_eth.toFixed(4)).padStart(10);
      const lanes = String(d.active_lanes).padStart(5);
      out += `${{dt}}  ${{lit}}  ${{eth}}  ${{lanes}}\\n`;
    }});
    document.getElementById('history').textContent = out;
  }})
  .catch(() => {{
    document.getElementById('history').textContent = 'No history data available yet.';
  }});
</script>
</body>
</html>"""
    
    dash_path = WORKSPACE / "projects" / "revenue-dashboard" / "dashboard.html"
    dash_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dash_path, "w") as f:
        f.write(html)
    return str(dash_path)


def main():
    watch = "--watch" in sys.argv
    html = "--html" in sys.argv
    
    while True:
        snap = build_snapshot()
        write_snapshot(snap)
        
        if html or "--html" in sys.argv:
            dash_path = generate_html_dashboard(snap)
            print(f"[{snap['timestamp']}] Snapshot saved. Dashboard: {dash_path}")
        else:
            print(f"[{snap['timestamp']}] Snapshot saved to {SNAP_FILE}")
        
        # Print summary line
        s = snap["summary"]
        print(f"  LIT:{s['total_lit_pending']:>8,.0f} | ETH:{s['total_pnl_eth']:>+.4f} | NOOK-exp:{s['total_nook_exposure']:>10,.0f} | Lanes:{s['active_lanes']}/6 | Est-LIT/day:{s['estimated_daily_lit']:>8,.0f} | Claim-Ready:{'YES' if s['claim_ready'] else 'NO'}")
        
        if not watch:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
