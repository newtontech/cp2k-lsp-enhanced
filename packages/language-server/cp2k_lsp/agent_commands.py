"""Agent-facing LSP workspace/executeCommand handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cp2k_input_tools.agent_lsp import AgentLSP
from cp2k_input_tools.agent_operations import OPERATIONS, with_capabilities
from cp2k_input_tools.rich_diagnostics import agent_check_payload
from cp2k_input_tools.tool import SOFTWARE

COMMAND_CHECK = "cp2k/check"
COMMAND_EXPLAIN = "cp2k/explain"
COMMAND_CAPABILITIES = "cp2k/capabilities"

AGENT_COMMANDS = (COMMAND_CHECK, COMMAND_EXPLAIN, COMMAND_CAPABILITIES)


def parse_command_args(arguments: list[Any] | None) -> dict[str, Any]:
    """Normalize LSP executeCommand arguments to a single kwargs dict."""
    if not arguments:
        return {}
    first = arguments[0]
    if isinstance(first, dict):
        return dict(first)
    if isinstance(first, str):
        try:
            parsed = json.loads(first)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"uri": first}
    return {}


def _resolve_uri(args: dict[str, Any]) -> str | None:
    uri = args.get("uri")
    if isinstance(uri, str) and uri.strip():
        return uri
    path = args.get("path")
    if isinstance(path, str) and path.strip():
        return Path(path).expanduser().resolve().as_uri()
    return None


def _agent_lsp_from_args(server: Any, args: dict[str, Any]) -> AgentLSP | None:
    uri = _resolve_uri(args)
    if uri is None:
        return None

    if server is not None:
        try:
            document = server.workspace.get_text_document(uri)
            return AgentLSP.from_text(document.source, uri=uri)
        except Exception:
            pass

    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path = Path(parsed.path)
        if path.is_file():
            return AgentLSP.from_path(path)
    return None


def _unavailable_payload(operation: str, reason: str) -> dict[str, Any]:
    payload = agent_check_payload(
        software=SOFTWARE,
        uri="",
        operation=operation,
        diagnostics=[],
    )
    payload["ok"] = False
    return with_capabilities(payload, operation, status="unavailable", reason=reason, source="cp2k-lsp")


def run_capabilities(_server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Return the fleet-standard capabilities contract for agent consumers."""
    del arguments
    return {
        "software": SOFTWARE,
        "status": "available",
        "capabilities": {
            "operations": list(OPERATIONS),
            "operation": "capabilities",
            "status": "available",
            "source": "cp2k-lsp",
            "commands": list(AGENT_COMMANDS),
        },
    }


def run_check(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Run Diagnostic Engine v1 check for a workspace document or file URI."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("check", "Missing or unknown uri/path for cp2k/check.")
    payload = agent.check()
    payload["capabilities"]["source"] = "cp2k-lsp"
    return payload


def run_explain(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Explain diagnostics or documentation at a cursor position."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("explain", "Missing or unknown uri/path for cp2k/explain.")
    line = int(args.get("line", 0) or 0)
    character = int(args.get("character", 0) or 0)
    payload = agent.explain(line=line, character=character)
    payload["capabilities"]["source"] = "cp2k-lsp"
    return payload
