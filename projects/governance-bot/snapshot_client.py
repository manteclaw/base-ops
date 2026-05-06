import json
import logging
import time
from typing import Dict, List, Optional

import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

# Import selfheal retry wrapper if available
try:
    import sys
    sys.path.insert(0, "/root/.openclaw/workspace")
    from selfheal import retry
except Exception:
    def retry(fn, *args, **kwargs):
        return fn()


class SnapshotClient:
    """
    Client for Snapshot Hub GraphQL API.
    Handles proposal querying, vote checking, and EIP-712 vote signing.
    """

    def __init__(self, hub_url: str, private_key: str, wallet_address: str):
        self.hub_url = hub_url
        self.private_key = private_key
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.w3 = Web3()

    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query against the Snapshot hub (with retry)."""
        def _do_request():
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            resp = requests.post(self.hub_url, json=payload, headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            return data.get("data", {})

        return retry(_do_request, service="snapshot_graphql", max_retries=5, base_delay=2.0)

    def get_active_proposals(self, space_id: str, network: Optional[str] = None) -> List[Dict]:
        """Fetch active (open) proposals for a Snapshot space."""
        network_filter = f'network: "{network}",' if network else ""
        query = f"""
        query {{
          proposals(
            first: 50,
            skip: 0,
            where: {{
              space_in: ["{space_id}"],
              state: "active"
              {network_filter}
            }},
            orderBy: "created",
            orderDirection: desc
          ) {{
            id
            title
            body
            choices
            start
            end
            snapshot
            state
            author
            created
            scores
            scores_total
            space {{
              id
              name
            }}
          }}
        }}
        """
        data = self._graphql(query)
        return data.get("proposals", [])

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Fetch a single proposal by ID."""
        query = f"""
        query {{
          proposal(id: "{proposal_id}") {{
            id
            title
            body
            choices
            start
            end
            snapshot
            state
            author
            created
            scores
            scores_total
            space {{
              id
              name
            }}
          }}
        }}
        """
        data = self._graphql(query)
        return data.get("proposal")

    def get_vote(self, proposal_id: str, voter: str) -> Optional[Dict]:
        """Check if an address has already voted on a proposal."""
        query = f"""
        query {{
          votes(
            first: 1,
            where: {{
              proposal: "{proposal_id}",
              voter: "{voter}"
            }}
          ) {{
            id
            voter
            choice
            vp
            created
          }}
        }}
        """
        data = self._graphql(query)
        votes = data.get("votes", [])
        return votes[0] if votes else None

    def cast_vote(self, proposal_id: str, choice: int, reason: str = "") -> Dict:
        """
        Cast a vote on a Snapshot proposal via EIP-712 signature.

        Snapshot votes are off-chain signed messages (gasless).
        The message is structured data signed with EIP-712 and relayed
        to the Snapshot hub, which stores it on IPFS.
        """
        # Build EIP-712 typed data for Snapshot vote
        # Domain: snapshot.org — verified against their signer contract
        domain = {
            "name": "snapshot",
            "version": "0.1.4",
            "chainId": 1,  # Snapshot hub uses chainId 1 for EIP-712 domain
        }

        message = {
            "from": self.wallet_address,
            "space": self._get_space_from_proposal(proposal_id),
            "timestamp": int(time.time()),
            "proposal": proposal_id,
            "choice": choice,
            "reason": reason,
            "app": "govbot",
            "metadata": "{}"
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"}
            ],
            "Vote": [
                {"name": "from", "type": "address"},
                {"name": "space", "type": "string"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "proposal", "type": "string"},
                {"name": "choice", "type": "uint256"},
                {"name": "reason", "type": "string"},
                {"name": "app", "type": "string"},
                {"name": "metadata", "type": "string"}
            ]
        }

        # Sign the structured data
        signable = self._encode_eip712(domain, types, "Vote", message)
        signed = self.w3.eth.account.sign_message(signable, private_key=self.private_key)

        # Submit to Snapshot hub relay
        payload = {
            "address": self.wallet_address,
            "sig": signed.signature.hex(),
            "data": {
                "domain": domain,
                "types": types,
                "message": message
            }
        }

        # Submit to Snapshot hub relay (with retry)
        def _submit():
            resp = requests.post(
                f"{hub_base}/api/msg",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            resp.raise_for_status()
            return resp.json()

        return retry(_submit, service="snapshot_vote", max_retries=7, base_delay=3.0)

    def _get_space_from_proposal(self, proposal_id: str) -> str:
        """Resolve space ID from proposal ID."""
        proposal = self.get_proposal(proposal_id)
        if proposal and "space" in proposal:
            return proposal["space"]["id"]
        return "unknown.eth"

    def _encode_eip712(self, domain: Dict, types: Dict, primary_type: str, message: Dict):
        """Encode EIP-712 structured data for signing."""
        from eth_account.messages import encode_structured_data
        data = {
            "types": types,
            "primaryType": primary_type,
            "domain": domain,
            "message": message
        }
        return encode_structured_data(data)
