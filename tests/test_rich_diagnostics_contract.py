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
    assert item["actions"] == []
    assert item["artifact_role"] == "input"
    assert item["source_provenance"] == [
        {
            "kind": "official_schema",
            "label": "Bundled CP2K input XML schema",
            "path": "cp2k_input_tools/cp2k_input.xml",
        }
    ]
    assert item["version_assumption"] == {
        "software": "cp2k",
        "version": "unknown",
        "source": "bundled cp2k_input.xml",
    }


def test_diagnostic_envelope_preserves_generic_preflight_fields() -> None:
    diagnostic = {
        "code": "cp2k.files.missing_basis",
        "severity": "error",
        "message": "BASIS_SET_FILE_NAME could not be resolved",
        "line": 3,
        "column": 1,
        "source_provenance": [
            {
                "kind": "official_docs",
                "label": "CP2K manual",
                "url": "https://manual.cp2k.org/",
            }
        ],
        "version_assumption": {
            "software": "cp2k",
            "version": "2026.1",
            "source": "fixture metadata",
        },
        "artifact_role": "basis_set",
        "fix_hints": ["Provide a readable BASIS_SET_FILE_NAME."],
        "actions": [{"kind": "edit", "title": "Set BASIS_SET_FILE_NAME"}],
    }

    item = diagnostic_to_dict(diagnostic, software="cp2k", path="input.inp", file_type="inp")

    assert item["category"] == "cross-file reference"
    assert item["source_provenance"][0]["kind"] == "official_docs"
    assert item["version_assumption"]["version"] == "2026.1"
    assert item["artifact_role"] == "basis_set"
    assert item["fix_hints"] == ["Provide a readable BASIS_SET_FILE_NAME."]
    assert item["actions"] == [{"kind": "edit", "title": "Set BASIS_SET_FILE_NAME"}]
