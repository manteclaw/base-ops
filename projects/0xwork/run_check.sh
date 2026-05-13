#!/bin/bash
export WORKPROTOCOL_API_KEY=WORKPROTOCOL_KEY_REDACTED
cd /root/.openclaw/workspace/projects/0xwork
python3 task_matcher.py --min-bounty 10 --json
