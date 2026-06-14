"""Tests for cp2k_lsp workspace/executeCommand agent feedback API."""

from __future__ import annotations

import json
from pathlib import Path

from cp2k_lsp.agent_commands import (
    AGENT_COMMANDS,
    COMMAND_CAPABILITIES,
    COMMAND_CHECK,
    COMMAND_CONTEXT,
    COMMAND_EXPLAIN,
    COMMAND_SCHEMA_VALIDATE,
    run_capabilities,
    run_check,
    run_explain,
)
from cp2k_lsp.server import CP2KLanguageServer

FIXTURES = Path(__file__).resolve().parent / "harness" / "fixtures"
VALID_INPUT = FIXTURES / "valid_input.inp"
INVALID_INPUT = FIXTURES / "invalid_input.inp"


def _assert_capabilities_block(payload: dict, operation: str) -> None:
    caps = payload["capabilities"]
    assert caps["operation"] == operation
    assert caps["status"] in {"available", "unavailable"}
    assert isinstance(caps["operations"], list)
    assert operation in caps["operations"] or operation == "capabilities"


def test_agent_command_constants() -> None:
    assert COMMAND_CHECK in AGENT_COMMANDS
    assert COMMAND_EXPLAIN in AGENT_COMMANDS
    assert COMMAND_CAPABILITIES in AGENT_COMMANDS
    assert COMMAND_CONTEXT in AGENT_COMMANDS
    assert COMMAND_SCHEMA_VALIDATE in AGENT_COMMANDS


def test_capabilities_command_returns_stable_json_shape() -> None:
    payload = run_capabilities()

    assert payload["software"] == "cp2k"
    assert payload["status"] == "available"
    caps = payload["capabilities"]
    assert caps["operation"] == "capabilities"
    assert caps["source"] == "cp2k-lsp"
    assert COMMAND_CHECK in caps["commands"]
    assert COMMAND_EXPLAIN in caps["commands"]
    assert COMMAND_CAPABILITIES in caps["commands"]
    assert "check" in caps["operations"]
    assert "explain" in caps["operations"]
    json.dumps(payload)


def test_check_command_valid_input_returns_check_payload() -> None:
    payload = run_check(arguments=[{"path": str(VALID_INPUT)}])

    assert payload["software"] == "cp2k"
    assert payload["operation"] == "check"
    assert payload["ok"] is True
    assert isinstance(payload["diagnostics"], list)
    assert "summary" in payload
    _assert_capabilities_block(payload, "check")
    json.dumps(payload)


def test_check_command_invalid_input_reports_blocking_issues() -> None:
    payload = run_check(arguments=[{"path": str(INVALID_INPUT)}])

    assert payload["operation"] == "check"
    assert payload["ok"] is False
    assert payload["summary"]["blocking"] >= 1
    _assert_capabilities_block(payload, "check")


def test_explain_command_returns_explanations_for_invalid_input() -> None:
    payload = run_explain(arguments=[{"path": str(INVALID_INPUT), "line": 1, "character": 0}])

    assert payload["operation"] == "explain"
    assert isinstance(payload["explanations"], list)
    assert payload["explanations"]
    first = payload["explanations"][0]
    assert {"code", "message", "severity", "fix_hints", "range"} <= set(first)
    _assert_capabilities_block(payload, "explain")
    json.dumps(payload)


def test_server_registers_execute_commands() -> None:
    server = CP2KLanguageServer()
    registered = set(server.lsp.fm.commands)

    assert COMMAND_CHECK in registered
    assert COMMAND_EXPLAIN in registered
    assert COMMAND_CAPABILITIES in registered
    assert set(AGENT_COMMANDS) <= registered
