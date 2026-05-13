#!/usr/bin/env python3
"""
Manteclaw Revenue Aggregator — CLI wrapper around revenue_tracker.py.
Generates unified reports, triggers dashboard rebuild, and optionally
serves the dashboard over HTTP.

Usage:
    python3 revenue_aggregate.py           # Single aggregation + dashboard
    python3 revenue_aggregate.py --serve  # Start local HTTP server on :8080
    python3 revenue_aggregate.py --cron    # Append-only mode for cron jobs
"""

import argparse
import http.server
import json
import os
import socketserver
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
TRACKER = WORKSPACE / "projects" / "revenue_tracker.py"
DASHBOARD_DIR = WORKSPACE / "projects" / "revenue-dashboard"
DASHBOARD_FILE = DASHBOARD_DIR / "dashboard.html"
SNAP_FILE = WORKSPACE / "projects" / "revenue_snapshot.json"
REPORT_FILE = WORKSPACE / "projects" / "revenue_reports"


def run_tracker():
    """Run the revenue tracker to generate latest snapshot."""
    result = subprocess.run(
        [sys.executable, str(TRACKER), "--html"],
        capture_output=True, text=True, cwd=WORKSPACE
    )
    return result.stdout, result.stderr, result.returncode


def generate_text_report(snapshot):
    """Generate a human-readable text report."""
    lanes = snapshot["lanes"]
    s = snapshot["summary"]
    ts = snapshot["timestamp"]
    
    lines = []
    lines.append("=" * 60)
    lines.append(f"  MANTECLAW REVENUE REPORT — {ts}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  📊 SUMMARY")
    lines.append(f"  Total LITCOIN pending:     {s['total_lit_pending']:>12,.0f}")
    lines.append(f"  Total ETH PnL:             {s['total_pnl_eth']:>+12.4f}")
    lines.append(f"  NOOK exposure potential:   {s['total_nook_exposure']:>12,.0f}")
    lines.append(f"  Active lanes:              {s['active_lanes']:>12}/6")
    lines.append(f"  Est. daily LIT:            {s['estimated_daily_lit']:>12,.0f}")
    lines.append(f"  Claim ready:               {'YES':>12}" if s['claim_ready'] else f"  Claim ready:               {'NO':>12}")
    lines.append("")
    
    for lane_id in ["A", "B", "C", "D", "E", "F"]:
        l = lanes.get(lane_id)
        if not l:
            continue
        lines.append(f"  [{lane_id}] {l['name']} — {l['status'].upper()}")
        
        if lane_id == "A":
            lines.append(f"       Balance: {l['balance_lit']:,.0f} LITCOIN | Rounds: {l['rounds']:,} | Avg: {l['avg_per_round']:.2f}")
            lines.append(f"       Best task: {l['best_task_type'] or 'N/A'} ({l['best_task_avg']:.1f}) | Best hour: {l['best_hour'] or 'N/A'}")
            lines.append(f"       Providers: {', '.join(l['providers'])}")
        elif lane_id == "B":
            lines.append(f"       Tracked: {l['tracked_bounties']} | Applied: {l['applied']} | Submitted: {l['submitted']}")
            lines.append(f"       Zero-competition: {l['zero_competition_bounties']} | Exposure: {l['potential_exposure_nook']:,.0f} NOOK")
        elif lane_id == "C":
            lines.append(f"       Published: {l['published']} | Failed: {l.get('failed', 0)} | Est. NOOK: {l.get('estimated_nook_earned', 0):,.0f}")
        elif lane_id == "D":
            lines.append(f"       Trades: {l['trades_executed']} | Total PnL: {l['total_pnl_eth']:.4f} ETH")
            if l['recent_trades']:
                last = l['recent_trades'][-1]
                lines.append(f"       Last trade: {last['pnl_eth']:>+.4f} ETH")
        elif lane_id == "E":
            lines.append(f"       Tasks: {l['tracked_tasks']} | Potential: {l['total_potential_reward']:,.0f} NOOK")
            lines.append(f"       Platforms: {dict(l.get('platforms', {}))}")
        elif lane_id == "F":
            if l['status'] == 'idle':
                lines.append(f"       Status: Idle — run yield scanner")
            else:
                lines.append(f"       Best APY: {l['best_apy']:,.0f}% | Protocol: {l['best_protocol']} | Pool: {l['best_symbol']}")
        lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def save_report(report_text):
    """Save dated report to revenue_reports directory."""
    REPORT_FILE.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = REPORT_FILE / f"report-{date_str}.txt"
    with open(path, "w") as f:
        f.write(report_text)
    return str(path)


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)
    
    # SSE clients
    self.sse_clients = []

    def do_GET(self):
        if self.path == '/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            # Send initial connection event
            self.wfile.write(b'data: {"type":"connected"}\n\n')
            self.wfile.flush()
            # Register client
            if self not in self.sse_clients:
                self.sse_clients.append(self)
            # Keep connection alive
            try:
                while True:
                    self.wfile.write(b':heartbeat\n\n')
                    self.wfile.flush()
                    import time
                    time.sleep(15)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if self in self.sse_clients:
                    self.sse_clients.remove(self)
            return
        super().do_GET()

    @classmethod
    def broadcast(cls, data: dict):
        """Broadcast an SSE event to all connected clients."""
        msg = f'data: {json.dumps(data)}\n\n'
        dead = []
        for client in cls.sse_clients:
            try:
                client.wfile.write(msg.encode())
                client.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                dead.append(client)
        for client in dead:
            if client in cls.sse_clients:
                cls.sse_clients.remove(client)

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def serve_dashboard(port=8080):
    """Serve dashboard.html on specified port."""
    os.chdir(str(DASHBOARD_DIR))
    handler = DashboardHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 Serving dashboard at http://0.0.0.0:{port}/dashboard.html")
        print("   Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")


def main():
    parser = argparse.ArgumentParser(description="Manteclaw Revenue Aggregator")
    parser.add_argument("--serve", action="store_true", help="Serve dashboard on :8080")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default 8080)")
    parser.add_argument("--cron", action="store_true", help="Cron mode: quiet, append-only")
    parser.add_argument("--report", action="store_true", help="Save text report to file")
    args = parser.parse_args()
    
    if args.serve:
        # Make sure dashboard exists first
        if not DASHBOARD_FILE.exists():
            print("Generating dashboard first...")
            stdout, stderr, rc = run_tracker()
            if rc != 0:
                print(f"Tracker failed: {stderr}")
                sys.exit(1)
        serve_dashboard(args.port)
        return
    
    # Run tracker
    if not args.cron:
        print("Running revenue tracker...")
    stdout, stderr, rc = run_tracker()
    
    if rc != 0:
        print(f"Tracker error (rc={rc}): {stderr}", file=sys.stderr)
        sys.exit(1)
    
    if not args.cron:
        print(stdout)
    
    # Load snapshot and generate report
    if SNAP_FILE.exists():
        with open(SNAP_FILE) as f:
            snapshot = json.load(f)
        
        report = generate_text_report(snapshot)
        
        if args.report:
            path = save_report(report)
            print(f"Report saved: {path}")
        
        if not args.cron:
            print("\n" + report)
            print(f"\nDashboard: file://{DASHBOARD_FILE}")
    else:
        print("No snapshot generated.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
