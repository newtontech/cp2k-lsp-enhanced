"""OpenQC traceability report contract tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "reports" / "docstring-wiki-raw-traceability.json"


def load_report() -> dict[str, object]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_traceability_report_matches_openqc_v1_contract() -> None:
    report = load_report()
    assert report["schemaVersion"] == "openqc.lsp.traceability.v1"
    assert report["serverId"]
    assert report["repository"]
    assert report["languageId"]
    assert report["generatedAt"]
    summary = report["summary"]
    assert summary["docstringsTotal"] >= 1
    assert summary["docstringsLinked"] == summary["docstringsTotal"]
    assert summary["brokenWikiLinks"] == 0
    assert summary["wikiSourcesWithoutRaw"] == 0
    assert summary["rawManifestFailures"] == 0
    assert report["docstrings"]
    assert report["wikiSources"]
    assert report["sourceUrls"]
    assert report["rawManifest"]["ok"] is True


def test_traceability_paths_exist_and_urls_are_non_empty() -> None:
    report = load_report()
    for entry in report["docstrings"]:
        assert (REPO_ROOT / entry["path"]).is_file()
        assert (REPO_ROOT / entry["wikiPath"]).is_file()
        assert entry["symbol"]
    for entry in report["wikiSources"]:
        assert (REPO_ROOT / entry["wikiPath"]).is_file()
        assert (REPO_ROOT / entry["rawPath"]).is_file()
        assert entry["sourceUrl"]
    for entry in report["sourceUrls"]:
        assert (REPO_ROOT / entry["rawPath"]).is_file()
        assert entry["url"]


def test_traceability_generator_check_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate-traceability-report.py", "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
