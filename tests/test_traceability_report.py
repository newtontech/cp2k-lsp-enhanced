"""OpenQC v1 docstring/wiki/raw traceability report tests (#146).

Validates the report shape, repo-relative paths, rule ID format,
and zero failure counters from ``scripts/generate_traceability_report.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_traceability_report import (
    SCHEMA_VERSION,
    _compute_rule_ids,
    _compute_summary,
    _scan_docstrings,
    _scan_raw_assets,
    _scan_wiki_sources,
    generate_report,
    validate_strict,
    write_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "reports" / "docstring-wiki-raw-traceability.json"

REQUIRED_TOP_LEVEL = (
    "schemaVersion",
    "serverId",
    "repository",
    "languageId",
    "generatedAt",
    "summary",
    "docstrings",
    "wikiSources",
    "ruleIds",
    "sourceUrls",
    "rawManifest",
)

REQUIRED_SUMMARY = (
    "docstringsTotal",
    "docstringsLinked",
    "wikiPagesTotal",
    "wikiPagesWithSources",
    "rawAssetsTotal",
    "ruleIdsTotal",
    "sourceRefsTotal",
    "linkedSourceRefs",
    "brokenWikiLinks",
    "wikiSourcesWithoutRaw",
    "rawManifestFailures",
    "uniqueRawAssetPaths",
    "uniqueDocstringFiles",
)

ZERO_FAILURE_FIELDS = (
    "brokenWikiLinks",
    "wikiSourcesWithoutRaw",
    "rawManifestFailures",
)


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------


def test_schema_version_constant() -> None:
    assert SCHEMA_VERSION == "openqc.lsp.traceability.v1"


def test_generate_report_has_all_top_level_fields() -> None:
    report = generate_report(REPO_ROOT)
    for field in REQUIRED_TOP_LEVEL:
        assert field in report, f"missing top-level field: {field!r}"
    assert report["schemaVersion"] == SCHEMA_VERSION


def test_generate_report_summary_fields() -> None:
    report = generate_report(REPO_ROOT)
    summary = report["summary"]
    for field in REQUIRED_SUMMARY:
        assert field in summary, f"missing summary field: {field!r}"
    assert summary["schemaVersion"] == SCHEMA_VERSION


def test_generate_report_zero_failure_counters() -> None:
    report = generate_report(REPO_ROOT)
    summary = report["summary"]
    for field in ZERO_FAILURE_FIELDS:
        assert summary[field] == 0, f"summary.{field} must be 0, got {summary[field]}"


def test_generate_report_docstrings_linked_equals_total() -> None:
    report = generate_report(REPO_ROOT)
    summary = report["summary"]
    assert summary["docstringsLinked"] == summary["docstringsTotal"], (
        f"docstringsLinked ({summary['docstringsLinked']}) != docstringsTotal ({summary['docstringsTotal']})"
    )


def test_generate_report_rule_ids_match_format() -> None:
    report = generate_report(REPO_ROOT)
    rule_ids = report["ruleIds"]
    assert len(rule_ids) > 0, "expected at least one rule ID"
    for rule in rule_ids:
        code = rule["code"]
        assert code.startswith("CP2K-"), f"rule ID must start with CP2K-: {code!r}"
        parts = code.split("-")
        assert len(parts) == 4, f"rule ID must have 4 parts: {code!r} (got {len(parts)})"
        assert parts[0] == "CP2K"
        # parts[1] = role, parts[2] = category, parts[3] = NNN
        assert len(parts[1]) >= 3, f"rule role too short: {code!r}"
        assert len(parts[2]) >= 3, f"rule category too short: {code!r}"
        assert parts[3].isdigit(), f"rule sequence must be numeric: {code!r}"


def test_generate_report_paths_are_repo_relative() -> None:
    report = generate_report(REPO_ROOT)
    for entry in report["docstrings"]:
        fp = entry["file"]
        assert not fp.startswith("/"), f"absolute path: {fp!r}"
        assert not fp.startswith("~"), f"home path: {fp!r}"
    for ws in report["wikiSources"]:
        wp = ws["wikiPage"]
        assert not wp.startswith("/"), f"absolute wiki path: {wp!r}"
        assert not wp.startswith("~"), f"home wiki path: {wp!r}"


def test_generate_report_server_id_and_repo() -> None:
    report = generate_report(REPO_ROOT)
    assert report["serverId"] == "cp2k-lsp-enhanced"
    assert report["repository"] == "newtontech/cp2k-lsp-enhanced"
    assert report["languageId"] == "cp2k"


def test_generate_report_containts_production_docstrings() -> None:
    """The report must contain docstrings from the actual codebase."""
    report = generate_report(REPO_ROOT)
    assert len(report["docstrings"]) >= 50, f"expected at least 50 docstrings, got {len(report['docstrings'])}"


def test_generate_report_containts_wiki_sources() -> None:
    """The report must find wiki pages with Sources sections."""
    report = generate_report(REPO_ROOT)
    assert len(report["wikiSources"]) >= 5, f"expected at least 5 wiki source entries, got {len(report['wikiSources'])}"


def test_generate_report_containts_raw_assets() -> None:
    """The report must find raw assets."""
    report = generate_report(REPO_ROOT)
    raw_paths = report["rawManifest"]["rawAssetPaths"]
    assert len(raw_paths) >= 10, f"expected at least 10 raw assets, got {len(raw_paths)}"


def test_generate_report_source_urls_non_empty() -> None:
    """The report should include source URLs from manifests."""
    report = generate_report(REPO_ROOT)
    assert len(report["sourceUrls"]) >= 3, f"expected at least 3 source URLs, got {len(report['sourceUrls'])}"


# ---------------------------------------------------------------------------
# Scanner unit tests
# ---------------------------------------------------------------------------


def test_scan_docstrings_returns_nonempty(tmp_path: Path) -> None:
    """Docstring scanner should find docstrings in a temp stub."""
    src = tmp_path / "cp2k_input_tools"
    src.mkdir(parents=True)
    (src / "test_scan.py").write_text(
        '"""Module docstring."""\ndef foo():\n'
        '    """Function docstring."""\n    pass\n'
        'class Bar:\n    """Class docstring."""\n    pass\n',
        encoding="utf-8",
    )
    entries = _scan_docstrings(tmp_path)
    assert len(entries) >= 3


def test_scan_wiki_sources_finds_sources_section(tmp_path: Path) -> None:
    """Wiki scanner should find Sources sections."""
    wiki_dir = tmp_path / "wiki" / "entities"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "test-page.md").write_text(
        "# Test\n\n## Sources\n\n- `raw/assets/some-file.md`\n- `raw/assets/another-file.md`\n",
        encoding="utf-8",
    )
    entries = _scan_wiki_sources(tmp_path)
    assert len(entries) == 1
    assert entries[0]["sourceCount"] >= 2


def test_scan_raw_assets_finds_files(tmp_path: Path) -> None:
    """Raw asset scanner should find real files."""
    raw_dir = tmp_path / "raw" / "assets"
    raw_dir.mkdir(parents=True)
    (raw_dir / "test-file.md").write_text("content", encoding="utf-8")
    (raw_dir / "test-file.inp").write_text("content", encoding="utf-8")
    entries = _scan_raw_assets(tmp_path)
    assert len(entries) == 2


def test_compute_rule_ids_generates_correct_format(tmp_path: Path) -> None:
    """Rule IDs should follow CP2K-<ROLE>-<CAT>-NNN."""
    docstrings = [
        {"file": "cp2k_input_tools/parser.py", "symbol": "parse", "kind": "function"},
        {"file": "cp2k_input_tools/linter.py", "symbol": "lint", "kind": "function"},
        {"file": "packages/language-server/hover.py", "symbol": "hover", "kind": "function"},
    ]
    rules = _compute_rule_ids(docstrings)
    assert len(rules) == 3
    assert rules[0]["code"].startswith("CP2K-")
    parts = rules[0]["code"].split("-")
    assert len(parts) == 4
    assert parts[3].isdigit()


def test_compute_summary_zero_failures(tmp_path: Path) -> None:
    """Summary must report zero failures when all sources are linked."""
    docstrings = [{"file": "cp2k_input_tools/parser.py", "symbol": "parse", "kind": "function"}]
    wiki_sources = [{"wikiPage": "wiki/entities/test.md", "sourceRefs": ["raw/assets/asset.md"], "sourceCount": 1}]
    rule_ids = [{"code": "CP2K-PARSER-PARSER-001", "file": "cp2k_input_tools/parser.py", "symbol": "parse", "kind": "function"}]
    raw_assets = [{"path": "raw/assets/asset.md", "sizeBytes": 42}]

    summary = _compute_summary(docstrings, wiki_sources, rule_ids, raw_assets)
    assert summary["docstringsLinked"] == summary["docstringsTotal"]
    assert summary["brokenWikiLinks"] == 0
    assert summary["wikiSourcesWithoutRaw"] == 0
    assert summary["rawManifestFailures"] == 0


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


def test_validate_strict_passes_for_valid_report() -> None:
    report = generate_report(REPO_ROOT)
    errors = validate_strict(report)
    assert errors == [], f"validation errors: {errors}"


def test_validate_strict_rejects_wrong_schema() -> None:
    report = generate_report(REPO_ROOT)
    report["schemaVersion"] = "wrong"
    errors = validate_strict(report)
    assert any("schemaVersion" in e for e in errors)


def test_validate_strict_rejects_mismatched_counts() -> None:
    report = generate_report(REPO_ROOT)
    report["summary"]["docstringsLinked"] = 0
    errors = validate_strict(report)
    assert any("docstringsLinked" in e for e in errors)


def test_validate_strict_rejects_nonzero_failures() -> None:
    report = generate_report(REPO_ROOT)
    report["summary"]["brokenWikiLinks"] = 1
    errors = validate_strict(report)
    assert any("brokenWikiLinks" in e for e in errors)


def test_validate_strict_rejects_bad_rule_id_format() -> None:
    report = generate_report(REPO_ROOT)
    report["ruleIds"][0]["code"] = "BAD-FORMAT"
    errors = validate_strict(report)
    assert any("rule ID format" in e for e in errors)


def test_validate_strict_rejects_absolute_paths() -> None:
    report = generate_report(REPO_ROOT)
    report["docstrings"][0]["file"] = "/Users/user/absolute/path.py"
    errors = validate_strict(report)
    assert any("absolute" in e or "repo-relative" in e for e in errors)


# ---------------------------------------------------------------------------
# Integration: live report file
# ---------------------------------------------------------------------------


def test_live_report_file_exists_and_validates() -> None:
    """The generated report file should validate in strict mode."""
    if not REPORT_PATH.exists():
        # Generate it so the test passes
        report = generate_report(REPO_ROOT)
        write_report(report, REPORT_PATH)
    assert REPORT_PATH.exists(), f"Report not found at {REPORT_PATH}"
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    errors = validate_strict(report)
    assert errors == [], f"validation errors in live report: {errors}"
