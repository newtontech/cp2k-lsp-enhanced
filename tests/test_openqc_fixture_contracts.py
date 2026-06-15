"""OpenQC closed-loop fixture contracts for CP2K (#138-#140).

Exercises canonical valid/invalid/log fixture paths declared in
``lsp-capabilities.json`` and asserts stable DiagnosticEnvelope/v1 JSON from
``cp2k-lsp-tool check``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cp2k_input_tools.log_parser import parse_log_file
from cp2k_input_tools.rich_diagnostics import agent_check_payload, diagnostic_to_dict

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_PATH = REPO_ROOT / "lsp-capabilities.json"

ENVELOPE_FIELDS = (
    "code",
    "severity",
    "category",
    "confidence",
    "source",
    "range",
    "software",
    "path",
    "blocking",
    "fix_hints",
    "message",
)


def _load_capabilities() -> dict:
    return json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))


def _fixture_dirs(key: str) -> list[Path]:
    caps = _load_capabilities()
    dirs: list[Path] = []
    for rel in caps["fixturePaths"][key]:
        path = REPO_ROOT / rel
        if path.is_dir():
            dirs.append(path)
    return dirs


def _run_check(path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "cp2k_input_tools.tool", "check", str(path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_lsp_capabilities_fixture_paths_exist() -> None:
    """OpenQC gate paths from lsp-capabilities.json must exist on disk."""
    caps = _load_capabilities()
    assert caps["openqc"]["diagnosticEnvelope"] == "DiagnosticEnvelope/v1"
    assert _fixture_dirs("valid"), "expected at least one valid fixture directory"
    assert _fixture_dirs("invalid"), "expected at least one invalid fixture directory"
    log_dir = REPO_ROOT / "tests" / "fixtures" / "logs"
    assert log_dir.is_dir()
    assert any(log_dir.glob("*.out"))


def test_valid_fixtures_emit_clean_diagnostic_envelope() -> None:
    """Valid fixtures must not produce blocking diagnostics."""
    for directory in _fixture_dirs("valid"):
        for fixture in sorted(directory.glob("*.inp")):
            payload = _run_check(fixture)
            assert payload["diagnostic_engine"] == "1.0"
            assert payload["ok"] is True, f"{fixture.name} unexpectedly blocked: {payload['diagnostics']}"
            for item in payload["diagnostics"]:
                for field in ENVELOPE_FIELDS:
                    assert field in item, f"{fixture.name}: missing {field!r}"
                assert item["blocking"] is False


def test_invalid_fixture_blocking_error_envelope() -> None:
    """A canonical invalid fixture must surface a blocking error."""
    blocking = REPO_ROOT / "tests/fixtures/invalid/blocking_misspelled_keyword.inp"
    assert blocking.exists()
    payload = _run_check(blocking)
    assert payload["ok"] is False
    blocking_items = [item for item in payload["diagnostics"] if item["blocking"]]
    assert blocking_items, payload["diagnostics"]
    assert any(item["severity"] == "error" for item in blocking_items)


def test_invalid_fixture_warning_envelope() -> None:
    """A canonical invalid fixture must surface at least one warning."""
    warning = REPO_ROOT / "tests/fixtures/invalid/warning_low_cutoff.inp"
    assert warning.exists()
    payload = _run_check(warning)
    warnings = [item for item in payload["diagnostics"] if item["severity"] == "warning"]
    assert warnings, payload["diagnostics"]
    assert all(not item["blocking"] for item in warnings)


def test_log_fixture_produces_runtime_diagnostic_envelope() -> None:
    """Log fixtures must map to runtime rule IDs with envelope fields."""
    log_path = REPO_ROOT / "tests/fixtures/logs/scf_not_converged.out"
    assert log_path.exists()
    raw = parse_log_file(str(log_path))
    assert raw, "expected log parser diagnostics"
    serialized = [
        diagnostic_to_dict(
            {
                "code": item.rule_id,
                "severity": item.severity,
                "message": item.message,
                "line": item.line_number,
                "column": 1,
                "fix_hints": [item.hint] if item.hint else [],
            },
            software="cp2k",
            path=str(log_path),
            file_type="log",
        )
        for item in raw
    ]
    assert serialized[0]["code"] == "cp2k.log.scf_not_converged"
    assert serialized[0]["blocking"] is True


def test_asset_manifest_lists_provenance_for_core_rules() -> None:
    """raw/assets/asset-manifest.json must anchor docs -> wiki -> rules pipeline."""
    manifest_path = REPO_ROOT / "raw/assets/asset-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["software"] == "cp2k"
    assert manifest["assets"]
    upstream = next(a for a in manifest["assets"] if a["path"].endswith("upstream-cp2k-reference.md"))
    assert upstream["url"].startswith("https://manual.cp2k.org/")
    assert upstream["sha256"]


def test_source_provenance_in_capabilities_matches_manifest() -> None:
    """lsp-capabilities sourceProvenance must include official doc anchors."""
    caps = _load_capabilities()
    urls = {entry["url"] for entry in caps["sourceProvenance"] if "url" in entry}
    assert "https://manual.cp2k.org/trunk/CP2K_INPUT.html" in urls
    assert "https://www.cp2k.org/input_file" in urls


def test_agent_check_payload_shape_for_empty_run() -> None:
    """Sanity check DiagnosticEnvelope/v1 top-level contract."""
    payload = agent_check_payload(software="cp2k", uri="file:///tmp/x.inp", diagnostics=[])
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["ok"] is True
