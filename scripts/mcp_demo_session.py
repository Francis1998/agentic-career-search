"""Drive the read-only MCP server over real stdio, the way an MCP host does.

Starts ``python -m autoapply_agent.mcp`` as a subprocess, then plays a modern
(``2026-07-28``) stateless client — discover, list tools, search the feed, explain the top
score, inspect a run, try a write tool and an unsupported protocol version — followed by
a legacy client that performs the ``initialize`` handshake. Requests are printed exactly
as sent (the per-request ``_meta`` is abbreviated to ``{…}`` after it is shown once);
replies show the server's own text content or, for errors, the raw JSON-RPC line.

Usage::

    uv run python scripts/mcp_demo_session.py --database-url sqlite+aiosqlite:///$PWD/mcp-demo.db
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from autoapply_agent.core.config import Settings

MODERN = "2026-07-28"
META: dict[str, Any] = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientCapabilities": {},
}
_META_PLACEHOLDER = "__META__"


def _compact(message: dict[str, Any]) -> str:
    """Serialize a message as one compact JSON line (as it travels on stdio)."""

    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


class StdioClient:
    """Minimal newline-delimited JSON-RPC client for one server subprocess."""

    def __init__(self, server_args: list[str]) -> None:
        """Spawn the server (STDERR passes through; STDOUT is the protocol channel)."""

        self._process = subprocess.Popen(
            [sys.executable, "-m", "autoapply_agent.mcp", *server_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self._next_id = 0

    def request(
        self, method: str, params: dict[str, Any], *, modern: bool = True
    ) -> dict[str, Any]:
        """Send a request, print it, and return the response (answered in order)."""

        payload = {**params, "_meta": META} if modern else params
        shown = {**params, "_meta": _META_PLACEHOLDER} if modern else params
        return self.send_raw(method, payload, shown=shown)

    def send_raw(
        self, method: str, params: dict[str, Any], *, shown: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send ``params`` verbatim, print the request, and return the response."""

        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        printed = {**message, "params": params if shown is None else shown}
        print("→ " + _compact(printed).replace(f'"{_META_PLACEHOLDER}"', "{…}"))
        self._send(message)
        if self._process.stdout is None:
            raise RuntimeError("server stdout is not connected")
        response: dict[str, Any] = json.loads(self._process.stdout.readline())
        if response.get("id") != self._next_id:
            raise RuntimeError(f"unexpected response id: {response.get('id')!r}")
        return response

    def notify(self, method: str) -> None:
        """Send and print a notification (no response expected)."""

        message = {"jsonrpc": "2.0", "method": method}
        print("→ " + _compact(message))
        self._send(message)

    def close(self) -> int:
        """Close stdin (the stdio shutdown signal) and return the server's exit code."""

        if self._process.stdin is not None:
            self._process.stdin.close()
        return self._process.wait(timeout=30)

    def _send(self, message: dict[str, Any]) -> None:
        """Write one message as a single line."""

        if self._process.stdin is None:
            raise RuntimeError("server stdin is not connected")
        self._process.stdin.write(json.dumps(message) + "\n")
        self._process.stdin.flush()


def _print_text(response: dict[str, Any]) -> dict[str, Any]:
    """Print a tool result's text content (the server's own rendering) and return it."""

    result: dict[str, Any] = response["result"]
    print(f"← isError={str(result['isError']).lower()} · content[0].text:")
    for line in result["content"][0]["text"].splitlines():
        print(f"  {line}")
    return result


def _print_error(response: dict[str, Any]) -> None:
    """Print a JSON-RPC error response exactly as received."""

    print("← " + _compact(response))


def modern_session(server_args: list[str]) -> None:
    """Stateless 2026-07-28 client."""

    client = StdioClient(server_args)
    print(f"modern client: every request carries _meta {_compact(META)}, shown as {{…}}")
    discover = client.request("server/discover", {})["result"]
    info = discover["_meta"]["io.modelcontextprotocol/serverInfo"]
    print(
        f"← supportedVersions {_compact(discover['supportedVersions'])} · "
        f"serverInfo {info['name']} {info['version']}"
    )
    tools = client.request("tools/list", {})["result"]["tools"]
    read_only = all(tool["annotations"]["readOnlyHint"] for tool in tools)
    print(f"← {len(tools)} tools, readOnlyHint={str(read_only).lower()} on all:")
    print("  " + ", ".join(tool["name"] for tool in tools))

    search = _print_text(
        client.request(
            "tools/call",
            {
                "name": "search_jobs",
                "arguments": {"remote": True, "sort": "score", "dedupe": True, "limit": 3},
            },
        )
    )
    top_job = search["structuredContent"]["jobs"][0]["id"]
    _print_text(
        client.request(
            "tools/call", {"name": "explain_job_score", "arguments": {"job_id": top_job}}
        )
    )
    runs = _print_text(client.request("tools/call", {"name": "list_runs", "arguments": {}}))
    first_run = runs["structuredContent"]["runs"][-1]["id"]
    _print_text(
        client.request(
            "tools/call", {"name": "get_run", "arguments": {"run_id": first_run, "event_limit": 4}}
        )
    )
    _print_error(
        client.request("tools/call", {"name": "create_run", "arguments": {"query": "rust"}})
    )
    _print_error(
        client.send_raw(
            "tools/list",
            {"_meta": {**META, "io.modelcontextprotocol/protocolVersion": "1900-01-01"}},
        )
    )
    print(f"stdin closed → server exit code {client.close()}")


def legacy_session(server_args: list[str]) -> None:
    """Legacy client: initialize handshake, then a tool call with the legacy result shape."""

    client = StdioClient(server_args)
    print("legacy client (new process):")
    initialized = client.request(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "legacy-demo", "version": "1.0"},
        },
        modern=False,
    )["result"]
    print(
        f"← protocolVersion {initialized['protocolVersion']} · "
        f"serverInfo {initialized['serverInfo']['name']}"
    )
    client.notify("notifications/initialized")
    result = client.request("tools/call", {"name": "list_sources", "arguments": {}}, modern=False)[
        "result"
    ]
    shape = "no resultType (legacy shape)" if "resultType" not in result else "resultType present"
    print(f"← isError={str(result['isError']).lower()} · {shape} · content[0].text:")
    for line in result["content"][0]["text"].splitlines():
        print(f"  {line}")
    print(f"stdin closed → server exit code {client.close()}")


def main() -> int:
    """Run both sessions against the configured database."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database-url", default=Settings().database_url)
    parser.add_argument("--audit-log", type=Path, default=None)
    args = parser.parse_args()
    server_args = ["--database-url", args.database_url]
    if args.audit_log is not None:
        server_args += ["--audit-log", str(args.audit_log)]
    modern_session(server_args)
    legacy_session(server_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
