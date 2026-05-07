#!/usr/bin/env python3
"""
MCP Server wrapper for Multi-Provider LLM Router.
Exposes router.chat and router.health as MCP tools.

Install: pip install mcp fastmcp
Run: python3 mcp_server.py
"""

from mcp.server.fastmcp import FastMCP
from router import LLMRouter

mcp = FastMCP("llm-router")
router = LLMRouter()

@mcp.tool()
def chat(prompt: str, system: str = None, provider: str = "auto", 
         temperature: float = 0.1, max_tokens: int = 2048) -> dict:
    """Send a chat completion through the best available LLM provider."""
    try:
        content, used_provider = router.chat(prompt, system, None, provider, temperature, max_tokens)
        return {"success": True, "content": content, "provider": used_provider}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def health() -> dict:
    """Get health status of all configured LLM providers."""
    return router.health()

@mcp.tool()
def set_priority(order: list) -> dict:
    """Set provider priority order (e.g., ["nvidia", "groq", "deepseek"])."""
    router.priority = order
    return {"success": True, "priority": order}

if __name__ == "__main__":
    mcp.run()
