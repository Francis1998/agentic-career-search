"""Read-only Model Context Protocol (MCP) server for the persisted job feed.

Lets MCP hosts (Claude Desktop, Claude Code, VS Code, Cursor, ...) search captured jobs,
read their decision traces, explain scores and inspect discovery runs over stdio. The
server is dependency-free (stdlib JSON-RPC on top of the existing services) and
dual-era: stateless ``2026-07-28`` requests and legacy ``initialize`` clients
(``2025-11-25`` / ``2025-06-18``). Every tool is read-only.
"""

from autoapply_agent.mcp.server import (
    LEGACY_PROTOCOL_VERSIONS,
    MODERN_PROTOCOL_VERSIONS,
    SUPPORTED_PROTOCOL_VERSIONS,
    CareerSearchMcpServer,
    main,
    serve_stdio,
)

__all__ = [
    "LEGACY_PROTOCOL_VERSIONS",
    "MODERN_PROTOCOL_VERSIONS",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "CareerSearchMcpServer",
    "main",
    "serve_stdio",
]
