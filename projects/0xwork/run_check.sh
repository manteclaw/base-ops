#!/bin/bash
export WORKPROTOCOL_API_KEY=KEY=[REDACTED-api_key_assignment]
cd 
cd /root/.openclaw/workspace/projects/0xwork
python3 task_matcher.py --min-bounty 10 --json
