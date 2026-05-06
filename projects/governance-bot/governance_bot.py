import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from snapshot_client import SnapshotClient
from voting_engine import VotingEngine
from logger import VoteLogger


class GovernanceVoteBot:
    """
    Automated governance vote bot for Snapshot-based DAOs on Base L2.
    Polls for new proposals, evaluates them against configurable rules,
    and casts votes via EIP-712 signed messages.
    """

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.snapshot = SnapshotClient(
            hub_url=self.config.get("snapshot_hub", "https://hub.snapshot.org/graphql"),
            private_key=self.config["private_key"],
            wallet_address=self.config["wallet_address"]
        )

        self.voting_engine = VotingEngine(self.config.get("rules", {}))
        self.logger = VoteLogger(self.config.get("log_file", "votes.log"))

        self.poll_interval = self.config.get("poll_interval_seconds", 300)
        self.spaces = self.config.get("spaces", [])
        self.network = self.config.get("network", "8453")  # Base mainnet

    def run(self):
        """Main polling loop."""
        logging.info(f"🤖 Governance bot started — monitoring {len(self.spaces)} space(s)")
        self.logger.log_event("BOT_START", {"spaces": self.spaces, "network": self.network})

        try:
            while True:
                self._poll_cycle()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.logger.log_event("BOT_STOP", {"reason": "keyboard_interrupt"})
            logging.info("Bot stopped by user")

    def _poll_cycle(self):
        """One polling cycle: fetch proposals, evaluate, vote."""
        for space_id in self.spaces:
            try:
                proposals = self.snapshot.get_active_proposals(space_id, network=self.network)
                logging.info(f"[{space_id}] Found {len(proposals)} active proposal(s)")

                for proposal in proposals:
                    self._process_proposal(space_id, proposal)

            except Exception as e:
                logging.error(f"[{space_id}] Poll error: {e}")
                self.logger.log_event("POLL_ERROR", {"space": space_id, "error": str(e)})

    def _process_proposal(self, space_id: str, proposal: Dict):
        """Evaluate and optionally vote on a single proposal."""
        proposal_id = proposal["id"]
        title = proposal.get("title", "Untitled")
        choices = proposal.get("choices", [])
        end_time = proposal.get("end", 0)

        # Check if already voted
        existing_vote = self.snapshot.get_vote(proposal_id, self.config["wallet_address"])
        if existing_vote:
            self.logger.log_event("ALREADY_VOTED", {
                "space": space_id, "proposal": proposal_id, "choice": existing_vote.get("choice")
            })
            return

        # Evaluate voting rule
        decision = self.voting_engine.evaluate(proposal, choices)
        if decision is None:
            self.logger.log_event("NO_RULE_MATCH", {
                "space": space_id, "proposal": proposal_id, "title": title
            })
            return

        choice_index, reason = decision
        logging.info(f"[{space_id}] Voting on '{title[:60]}...' → choice {choice_index} ({reason})")

        # Cast vote
        try:
            result = self.snapshot.cast_vote(proposal_id, choice_index)
            self.logger.log_event("VOTE_CAST", {
                "space": space_id,
                "proposal": proposal_id,
                "title": title,
                "choice": choice_index,
                "choice_text": choices[choice_index - 1] if choice_index <= len(choices) else "?",
                "reason": reason,
                "result": result
            })
        except Exception as e:
            logging.error(f"Vote failed: {e}")
            self.logger.log_event("VOTE_FAILED", {
                "space": space_id, "proposal": proposal_id, "error": str(e)
            })


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Governance Vote Bot")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")
    parser.add_argument("--list-proposals", metavar="SPACE", help="List active proposals for a space and exit")
    args = parser.parse_args()

    bot = GovernanceVoteBot(args.config)

    if args.list_proposals:
        proposals = bot.snapshot.get_active_proposals(args.list_proposals, network=bot.network)
        for p in proposals:
            print(f"\n{p['id']}")
            print(f"  Title: {p.get('title', 'N/A')}")
            print(f"  Choices: {p.get('choices', [])}")
            print(f"  Ends: {datetime.fromtimestamp(p.get('end', 0), tz=timezone.utc).isoformat()}")
            print(f"  State: {p.get('state', 'unknown')}")
        return

    if args.once:
        bot._poll_cycle()
    else:
        bot.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
