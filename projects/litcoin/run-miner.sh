#!/bin/bash
# Live miner runner — sources credentials from .env (NEVER commit this file with hardcoded keys)
cd /root/.openclaw/workspace/projects/litcoin

# Load env from workspace .env
set -a
source /root/.openclaw/workspace/.env
set +a

# Verify seed is set
if [ -z "$LITCOIN_SEED" ]; then
    echo "ERROR: LITCOIN_SEED not set in .env"
    exit 1
fi

venv/bin/pip install requests eth-account mnemonic 2>&1
venv/bin/python3 standalone-miner.py 10
