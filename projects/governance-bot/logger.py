import json
import os
from datetime import datetime, timezone
from typing import Dict


class VoteLogger:
    """
    Structured activity logger for governance bot events.
    Writes newline-delimited JSON for easy downstream processing.
    """

    def __init__(self, log_file: str = "votes.log"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

    def log_event(self, event_type: str, data: Dict):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            **data
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
