"""Validation backend registry contract tests."""

import json
from pathlib import Path

from cp2k_input_tools.tool import _capabilities_payload
from cp2k_input_tools.validation_backends import validation_backends_payload


def test_validation_backends_include_open_source_and_placeholders() -> None:
    backends = validation_backends_payload()
    by_id = {backend["id"]: backend for backend in backends}

    assert by_id["cp2k-lsp-tool-static"]["status"] == "available"
    assert by_id["cp2k-lsp-tool-static"]["kind"] == "open_source"
    assert "check" in by_id["cp2k-lsp-tool-static"]["operations"]
    assert by_id["cp2k-log-parser"]["mode"] == "log"
    assert by_id["cp2k-commercial-static-parser"]["status"] == "unavailable"
    assert by_id["cp2k-commercial-log-parser"]["status"] == "unavailable"


def test_capabilities_payload_exposes_validation_backends() -> None:
    payload = _capabilities_payload()

    assert payload["validationBackends"]
    assert {backend["id"] for backend in payload["validationBackends"]} >= {
        "cp2k-lsp-tool-static",
        "cp2k-commercial-static-parser",
    }


def test_lsp_capabilities_manifest_exposes_validation_backends() -> None:
    payload = json.loads(Path("lsp-capabilities.json").read_text(encoding="utf-8"))

    assert "validation-backends" in payload["capabilities"]
    assert {backend["id"] for backend in payload["validationBackends"]} >= {
        "cp2k-lsp-tool-static",
        "cp2k-commercial-log-parser",
    }
