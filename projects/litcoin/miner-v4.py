#!/usr/bin/env python3
"""
LITCOIIN Miner v4 — Official SDK Integration
Uses the `litcoin` PyPI package with Bankr + OpenRouter keys
"""

import os
import sys
import json
from pathlib import Path

# Add local venv if exists
venv_path = Path(__file__).parent / "venv"
if venv_path.exists():
    site_packages = list(venv_path.glob("lib/python*/site-packages"))
    if site_packages:
        sys.path.insert(0, str(site_packages[0]))

from litcoin import Agent

# === KEYS ===
BANKR_KEY = os.getenv("BANKR_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
FIREWORKS_KEY = os.getenv("FIREWORKS_API_KEY", "")
WALLET_ADDRESS = os.getenv("LITCOIIN_WALLET_ADDRESS", "0x8b8AAC89E101b77E5A917278120151FC496e5c39")

# === CONFIG ===
# Fallback chain: OpenRouter → Fireworks
MODEL_PRIMARY = "inclusionai/ling-2.6-1t:free"
MODEL_FALLBACK = "accounts/fireworks/models/llama-v3p1-70b-instruct"
AI_URL_PRIMARY = "https://openrouter.ai/api/v1"
AI_URL_FALLBACK = "https://api.fireworks.ai/inference/v1"

class LitcoiinMinerV4:
    """Official litcoin SDK wrapper"""
    
    def __init__(self):
        self.bankr_key = BANKR_KEY
        self.openrouter_key = OPENROUTER_KEY
        self.fireworks_key = FIREWORKS_KEY
        self.wallet = WALLET_ADDRESS
        
        if not self.bankr_key:
            raise ValueError("BANKR_API_KEY not set")
        
        # Try OpenRouter first, fallback to Fireworks
        ai_key = self.openrouter_key or self.fireworks_key
        ai_url = AI_URL_PRIMARY if self.openrouter_key else AI_URL_FALLBACK
        model = MODEL_PRIMARY if self.openrouter_key else MODEL_FALLBACK
        
        if not ai_key:
            raise ValueError("No AI API key set. Need OPENROUTER_API_KEY or FIREWORKS_API_KEY")
        
        # Create agent with both keys for research mining
        self.agent = Agent(
            bankr_key=self.bankr_key,
            ai_key=ai_key,
            ai_url=ai_url,
            model=model
        )
        provider = "OpenRouter" if self.openrouter_key else "Fireworks"
        print(f"✅ Agent initialized — Provider: {provider} | Wallet: {self.wallet[:10]}...")
    
    def _get_llm_config(self):
        """Get current LLM config (for dynamic switching)"""
        if self.openrouter_key:
            return {"key": self.openrouter_key, "url": AI_URL_PRIMARY, "model": MODEL_PRIMARY, "provider": "OpenRouter"}
        if self.fireworks_key:
            return {"key": self.fireworks_key, "url": AI_URL_FALLBACK, "model": MODEL_FALLBACK, "provider": "Fireworks"}
        return None
    
    def mine_comprehension(self, rounds=1):
        """Comprehension mining — no LLM needed"""
        print(f"⛏️  Comprehension mining ({rounds} rounds)...")
        return self.agent.mine(rounds=rounds)
    
    def mine_research(self):
        """Research mining — uses OpenRouter LLM"""
        print("⛏️  Research mining...")
        return self.agent.research_mine()
    
    def check_balance(self):
        """Check LITCOIN balance"""
        # The SDK may have this — if not, we'll query the chain directly
        print("💰 Balance check...")
        return {"wallet": self.wallet, "note": "Use litcoin SDK methods or BaseScan"}
    
    def stake(self, tier=1):
        """Stake LITCOIN for mining boost
        Tiers: 1=Spark(1M/7d/1.10x), 2=Circuit(5M/30d/1.25x), 
               3=Core(50M/90d/1.50x), 4=Architect(500M/180d/2.00x)"""
        print(f"🔒 Staking tier {tier}...")
        return self.agent.stake(tier=tier)

if __name__ == "__main__":
    print("=" * 50)
    print("LITCOIIN Miner v4 — Official SDK")
    print("=" * 50)
    
    miner = LitcoiinMinerV4()
    
    # Quick comprehension test
    try:
        result = miner.mine_comprehension(rounds=1)
        print(f"✅ Mine result: {result}")
    except Exception as e:
        print(f"⚠️  Mine issue (may need time): {e}")
    
    print("\n💡 Next: miner.mine_research() for LLM-powered mining")
    print("💡 Or: miner.stake(tier=1) to boost rewards")
