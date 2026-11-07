"""``python -m autoapply_agent.mcp`` — run the read-only job feed MCP server on stdio."""

from autoapply_agent.mcp.server import main

raise SystemExit(main())
