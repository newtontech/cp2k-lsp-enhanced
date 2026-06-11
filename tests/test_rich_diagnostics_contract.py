from __future__ import annotations

from cp2k_input_tools.rich_diagnostics import (
    DIAGNOSTIC_CATEGORIES,
    agent_check_payload,
    diagnostic_to_dict,
)


def test_diagnostic_engine_v1_contract_shape() -> None:
    payload = agent_check_payload(
        software="cp2k",
        uri="file:///tmp/input",
        diagnostics=[],
    )
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["ok"] is True
    assert payload["diagnostics"] == []
    assert set(DIAGNOSTIC_CATEGORIES) >= {"syntax", "schema", "type/value"}


def test_legacy_diagnostic_is_enriched() -> None:
    diagnostic = {
        "code": "CP2K001",
        "severity": "error",
        "message": "unknown keyword",
        "line": 2,
        "column": 3,
        "source": "cp2k-lsp",
    }
    item = diagnostic_to_dict(diagnostic, software="cp2k", path="input")
    assert item["severity"] == "error"
    assert item["category"] == "schema"
    assert item["blocking"] is True
    assert item["range"]["start"] == {"line": 1, "character": 2}
    assert item["fix_hints"] == []
