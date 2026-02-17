"""
HackGPT – MCP (Model Context Protocol) Module
===============================================
Exposes HackGPT's Kali Linux offensive-security tools to AI assistants
(Claude Desktop, Copilot, etc.) through the Model Context Protocol.

Usage from the main application:
    from hackgpt_mcp import MCPKaliServer
    server = MCPKaliServer(config)
    server.start()            # blocking
    server.start_background() # threaded

Usage from CLI:
    python3 hackgpt_v2.py --mcp
"""

from hackgpt_mcp.server import MCPKaliServer

__all__ = ["MCPKaliServer"]
