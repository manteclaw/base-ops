# MCP Security Audit

Model Context Protocol (MCP) server vulnerability scanner.

## Description
Audit MCP servers for security flaws: path traversal, command injection, SSRF, credential leaks. Generates CVE-style reports with severity scores.

## When to Use
- User asks to audit an MCP server
- Security review of agent tools needed
- Bug bounty hunting on MCP infrastructure
- Pre-deployment security check

## Instructions

### 1. Discovery Phase
```python
# Enumerate all tools exposed by MCP server
tools = mcp_server.list_tools()
for tool in tools:
    print(f"Tool: {tool.name} | Params: {tool.parameters}")
```

### 2. Vulnerability Patterns to Check
- **Path Traversal**: Parameters accepting file paths (`../etc/passwd`)
- **Command Injection**: Shell execution via parameters (`; rm -rf /`)
- **SSRF**: URL parameters making server-side requests
- **Credential Leaks**: Tool outputs containing API keys, tokens
- **Excessive Permissions**: Tools with dangerous capabilities (delete, exec)
- **Input Validation**: Missing sanitization on string inputs

### 3. Testing Strategy
```python
def test_path_traversal(tool):
    payloads = ["../../../etc/passwd", "..\\..\\windows\\system32\\config\\sam"]
    for payload in payloads:
        try:
            result = tool.call(file_path=payload)
            if "root:" in result or "SAM" in result:
                return CRITICAL
        except:
            pass
    return SAFE
```

### 4. Report Format
```json
{
  "cve_id": "MCP-2026-XXXX",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "tool_name": "vulnerable_tool",
  "vector": "path_traversal",
  "proof_of_concept": "...",
  "remediation": "Validate file paths with os.path.realpath()"
}
```

## Scripts
- `cve_scanner.py` — Automated vulnerability scanner for MCP tools
- `report_generator.py` — Generate formatted security reports

## References
- `mcp_spec.md` — MCP protocol specification and security best practices
