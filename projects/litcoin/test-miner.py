#!/usr/bin/env python3
"""
Litcoiin Mining Test Script — Quick diagnostic + single task execution
"""
import os
import sys

# Add venv packages if running outside activated venv
VENV_PATH = os.path.join(os.path.dirname(__file__), "venv", "lib", "python3.12", "site-packages")
if os.path.isdir(VENV_PATH) and VENV_PATH not in sys.path:
    sys.path.insert(0, VENV_PATH)

# Config
BANKR_KEY = os.environ.get("BANKR_API_KEY", "")
if not BANKR_KEY:
    raise ValueError("BANKR_API_KEY environment variable required")
AI_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not AI_KEY:
    print("❌ OPENROUTER_API_KEY not set")
    sys.exit(1)
AI_URL = "https://openrouter.ai/api/v1"

def main():
    print("=" * 60)
    print("LITCOIIN MINER DIAGNOSTIC")
    print("=" * 60)

    # 1. Check SDK
    try:
        import litcoin
        print(f"[OK] litcoin SDK v{litcoin.__version__ if hasattr(litcoin, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"[FAIL] litcoin SDK not found: {e}")
        sys.exit(1)

    # 2. Create agent
    try:
        from litcoin import Agent
        agent = Agent(bankr_key=BANKR_KEY, ai_key=AI_KEY, ai_url=AI_URL)
        print(f"[OK] Agent created — wallet: {agent.wallet}")
    except Exception as e:
        print(f"[FAIL] Agent creation failed: {e}")
        sys.exit(1)

    # 3. Check balance
    try:
        bal = agent.balance()
        print(f"[OK] Balance — LITCOIN: {bal.get('litcoin', 'N/A'):.0f}, LitCredit: {bal.get('litcredit', 'N/A'):.0f}")
    except Exception as e:
        print(f"[WARN] Balance check failed: {e}")

    # 4. Check status
    try:
        st = agent.status()
        print(f"[OK] Status — totalEarned: {st.get('totalEarnedFormatted', 'N/A')}, claimable: {st.get('claimableFormatted', 'N/A')}")
    except Exception as e:
        print(f"[WARN] Status check failed: {e}")

    # 5. Check miner status
    try:
        ms = agent.miner_status()
        print(f"[OK] Miner — active: {ms.get('active')}, solves: {ms.get('solves')}, health: {ms.get('health', {}).get('overall')}")
    except Exception as e:
        print(f"[WARN] Miner status failed: {e}")

    # 6. Fetch research tasks
    try:
        tasks = agent.research_tasks()
        print(f"[OK] Research tasks available: {len(tasks)}")
    except Exception as e:
        print(f"[WARN] Task fetch failed: {e}")

    # 7. Attempt single mine (optional — remove if you just want diagnostics)
    print("\n" + "=" * 60)
    print("ATTEMPTING SINGLE RESEARCH_MINE...")
    print("=" * 60)
    try:
        result = agent.research_mine()
        print(f"[OK] Mine result: {result}")
    except Exception as e:
        print(f"[FAIL] Mine failed: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
