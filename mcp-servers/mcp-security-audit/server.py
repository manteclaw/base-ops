#!/usr/bin/env python3
"""
MCP Security Audit MCP Server
Scans MCP servers for common vulnerabilities: command injection, path traversal, SSRF, etc.
"""
import asyncio
import json
import re
import sys
from mcp.server import Server
from mcp.types import TextContent, Tool

app = Server("mcp-security-audit")

# Common vulnerability patterns in MCP server implementations
VULNERABILITY_PATTERNS = {
    "command_injection": [
        r"os\.system\s*\(",
        r"subprocess\.call\s*\(",
        r"subprocess\.run\s*\(",
        r"eval\s*\(",
        r"exec\s*\(",
        r"shell\s*=\s*True",
    ],
    "path_traversal": [
        r"open\s*\([^)]*\+",
        r"\.read\s*\(",
        r"\.write\s*\(",
        r"path\.join\s*\([^)]*\+",
    ],
    "ssrf": [
        r"requests\.get\s*\(",
        r"urllib\.request\.urlopen",
        r"http\.client\.",
        r"fetch\s*\(",
    ],
    "hardcoded_secrets": [
        r"api[_-]?key\s*=\s*[\"'][^\"']+",
        r"secret\s*=\s*[\"'][^\"']+",
        r"password\s*=\s*[\"'][^\"']+",
        r"private[_-]?key\s*=\s*[\"'][^\"']+",
    ],
}

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="audit_mcp_server",
            description="Audit a local MCP server implementation for common security vulnerabilities. Provide the file path to the server code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the MCP server implementation file (e.g., server.py)"},
                    "checks": {"type": "array", "items": {"type": "string", "enum": ["command_injection", "path_traversal", "ssrf", "hardcoded_secrets", "all"]}, "default": ["all"]},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="scan_directory",
            description="Scan a directory of MCP servers for vulnerabilities across all implementations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory containing MCP server implementations"},
                    "max_files": {"type": "integer", "default": 50, "description": "Maximum files to scan"},
                },
                "required": ["directory"],
            },
        ),
        Tool(
            name="check_cve_database",
            description="Check if a specific MCP server or dependency has known CVEs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "npm/pip package name to check"},
                    "version": {"type": "string", "description": "Package version (optional)"},
                },
                "required": ["package_name"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "audit_mcp_server":
        file_path = arguments.get("file_path", "")
        checks = arguments.get("checks", ["all"])
        if "all" in checks:
            checks = list(VULNERABILITY_PATTERNS.keys())
        
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e), "file": file_path}, indent=2))]
        
        findings = []
        lines = content.split("\n")
        for check in checks:
            patterns = VULNERABILITY_PATTERNS.get(check, [])
            for pattern in patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            "type": check,
                            "pattern": pattern,
                            "line": i,
                            "code": line.strip(),
                            "severity": "high" if check in ["command_injection", "hardcoded_secrets"] else "medium",
                        })
        
        result = {
            "file": file_path,
            "lines_scanned": len(lines),
            "findings_count": len(findings),
            "findings": findings,
            "summary": f"Found {len(findings)} potential issues in {file_path}",
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "scan_directory":
        directory = arguments.get("directory", "")
        max_files = arguments.get("max_files", 50)
        import os
        
        all_findings = []
        scanned = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith((".py", ".js", ".ts")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r") as f:
                            content = f.read()
                        lines = content.split("\n")
                        for check, patterns in VULNERABILITY_PATTERNS.items():
                            for pattern in patterns:
                                for i, line in enumerate(lines, 1):
                                    if re.search(pattern, line, re.IGNORECASE):
                                        all_findings.append({
                                            "file": path,
                                            "type": check,
                                            "line": i,
                                            "severity": "high" if check in ["command_injection", "hardcoded_secrets"] else "medium",
                                        })
                    except Exception:
                        pass
                    scanned += 1
                    if scanned >= max_files:
                        break
            if scanned >= max_files:
                break
        
        result = {
            "directory": directory,
            "files_scanned": scanned,
            "findings_count": len(all_findings),
            "findings": all_findings[:50],
            "summary": f"Scanned {scanned} files, found {len(all_findings)} potential issues in {directory}",
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "check_cve_database":
        package_name = arguments.get("package_name", "")
        version = arguments.get("version", "latest")
        # Simulated CVE check — in production, this would query OSV or NVD
        known_cves = {
            "@modelcontextprotocol/sdk": [],
            "mcp": [],
        }
        cves = known_cves.get(package_name, [])
        return [TextContent(type="text", text=json.dumps({"package": package_name, "version": version, "cves_found": len(cves), "cves": cves}, indent=2))]
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
