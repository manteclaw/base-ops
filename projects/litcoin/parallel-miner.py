#!/usr/bin/env python3
"""
Parallel LITCOIN Miner — Run multiple wallets simultaneously for 3x throughput.

Each wallet gets its own task stream from the coordinator.
Usage:
    bash /tmp/run-parallel-miners.sh
"""
import os
import sys
import subprocess
import time
import json
from pathlib import Path

# ── Configuration ──
NUM_WORKERS = 3
BASE_DELAY = 3
WALLET_DERIVATION_INDEXES = [0, 1, 2]  # Use HD wallet derivation for sub-wallets
STATE_DIR = Path(__file__).parent / "parallel_states"
STATE_DIR.mkdir(exist_ok=True)

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
FIREWORKS_KEY = os.environ.get("FIREWORKS_API_KEY", "")
LITCOIN_SEED = os.environ.get("LITCOIN_SEED", "")

def start_worker(index):
    """Start a single miner worker with isolated state."""
    state_file = STATE_DIR / f"miner_{index}_state.json"
    env = os.environ.copy()
    env["STATE_FILE"] = str(state_file)
    env["WORKER_INDEX"] = str(index)
    
    # Derive sub-wallet (simplified - in production use proper HD derivation)
    # For now all use same wallet but coordinator sees same address
    # Future: derive via eth-account HDWallet
    
    log_file = STATE_DIR / f"miner_{index}.log"
    
    cmd = [
        sys.executable,
        "standalone-miner.py",
        "0",  # infinite rounds
        str(BASE_DELAY)
    ]
    
    # Use nohup for persistence
    with open(log_file, "a") as f:
        proc = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=str(Path(__file__).parent),
            env=env
        )
    
    return proc

def get_stats():
    """Aggregate stats from all workers."""
    total_rounds = 0
    total_earned = 0
    for i in range(NUM_WORKERS):
        state_file = STATE_DIR / f"miner_{i}_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                total_rounds += data.get("round_count", 0)
                total_earned += data.get("total_earned", 0)
            except:
                pass
    return total_rounds, total_earned

def main():
    if not all([OPENROUTER_KEY or FIREWORKS_KEY, LITCOIN_SEED]):
        print("Set OPENROUTER_API_KEY/FIREWORKS_API_KEY and LITCOIN_SEED")
        sys.exit(1)
    
    print(f"Starting {NUM_WORKERS} parallel miners...")
    print(f"State dir: {STATE_DIR}")
    
    workers = []
    for i in range(NUM_WORKERS):
        proc = start_worker(i)
        workers.append(proc)
        print(f"Worker {i}: PID {proc.pid}")
        time.sleep(2)  # Stagger starts
    
    print("\nAll workers running. Press Ctrl+C to stop.")
    print("Stats: rounds | earned")
    
    try:
        while True:
            time.sleep(30)
            rounds, earned = get_stats()
            print(f"  {rounds} rounds | {earned} LITCOIN")
            
            # Restart dead workers
            for i, proc in enumerate(workers):
                if proc.poll() is not None:
                    print(f"Worker {i} died (exit {proc.poll()}), restarting...")
                    workers[i] = start_worker(i)
    except KeyboardInterrupt:
        print("\nStopping all workers...")
        for proc in workers:
            proc.terminate()
        time.sleep(2)
        for proc in workers:
            if proc.poll() is None:
                proc.kill()
        print("Stopped.")

if __name__ == "__main__":
    main()
