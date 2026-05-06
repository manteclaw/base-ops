import json
import re
from typing import Dict, List, Optional, Tuple


class VotingEngine:
    """
    Rule-based voting engine.
    Evaluates proposals against configurable rules and returns a vote choice.
    """

    def __init__(self, rules_config: Dict):
        self.rules = rules_config.get("rules", [])
        self.default_choice = rules_config.get("default_choice", None)
        self.default_reason = rules_config.get("default_reason", "default policy")

    def evaluate(self, proposal: Dict, choices: List[str]) -> Optional[Tuple[int, str]]:
        """
        Evaluate a proposal against all rules. Returns (choice_index, reason) or None.
        choice_index is 1-based (Snapshot convention).
        """
        title = proposal.get("title", "")
        body = proposal.get("body", "")
        combined = f"{title}\n{body}".lower()
        space = proposal.get("space", {}).get("id", "")

        for rule in self.rules:
            if not self._rule_matches(rule, proposal, combined, space):
                continue

            action = rule.get("action", "")
            reason = rule.get("reason", "rule match")

            if action == "yes":
                return self._resolve_choice("for", choices, reason)
            elif action == "no":
                return self._resolve_choice("against", choices, reason)
            elif action == "abstain":
                return self._resolve_choice("abstain", choices, reason)
            elif action.startswith("choice:"):
                idx = int(action.split(":", 1)[1])
                return (idx, reason)
            elif action == "skip":
                return None

        # No rule matched — use default if configured
        if self.default_choice is not None:
            return (self.default_choice, self.default_reason)

        return None

    def _rule_matches(self, rule: Dict, proposal: Dict, combined: str, space: str) -> bool:
        """Check if a rule's conditions are satisfied."""
        conditions = rule.get("if", [])
        for cond in conditions:
            field = cond.get("field", "")
            operator = cond.get("op", "contains")
            value = cond.get("value", "")

            if field == "title_contains":
                if operator == "contains" and value.lower() not in proposal.get("title", "").lower():
                    return False
                if operator == "regex" and not re.search(value, proposal.get("title", ""), re.I):
                    return False
            elif field == "body_contains":
                if operator == "contains" and value.lower() not in proposal.get("body", "").lower():
                    return False
            elif field == "space":
                if value.lower() != space.lower():
                    return False
            elif field == "author_in":
                if proposal.get("author", "").lower() not in [v.lower() for v in value]:
                    return False
            elif field == "title_regex":
                if not re.search(value, proposal.get("title", ""), re.I):
                    return False

        return True

    def _resolve_choice(self, intent: str, choices: List[str], reason: str) -> Optional[Tuple[int, str]]:
        """Map intent string to a 1-based choice index."""
        intent_lower = intent.lower()

        # Direct index if numeric intent
        if intent.isdigit():
            idx = int(intent)
            if 1 <= idx <= len(choices):
                return (idx, reason)
            return None

        # Heuristic matching against choice text
        for i, choice in enumerate(choices):
            c = choice.lower()
            if intent_lower in c or c in intent_lower:
                return (i + 1, reason)

        # Fallback mappings
        fallback = {
            "for": 1,
            "yes": 1,
            "approve": 1,
            "accept": 1,
            "against": 2,
            "no": 2,
            "reject": 2,
            "abstain": 3,
        }

        if intent_lower in fallback:
            idx = fallback[intent_lower]
            if idx <= len(choices):
                return (idx, reason)

        return None
