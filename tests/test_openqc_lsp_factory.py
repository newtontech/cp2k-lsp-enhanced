from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from cp2k_lsp.features.code_action import CodeActionProvider
from lsprotocol import types as lsp

from cp2k_input_tools.openqc_lsp_factory import main as factory_main
from cp2k_input_tools.tool import check_path
from cp2k_input_tools.version_policy import lint_version_policy


def _write_manifest(root: Path, version: str, *, confidence: float = 0.95, keywords: list[dict] | None = None) -> Path:
    raw_dir = root / "raw" / "assets"
    raw_dir.mkdir(parents=True, exist_ok=True)
    source_path = raw_dir / f"cp2k-{version}.md"
    source_path.write_text(
        f"# CP2K {version}\n\nRUN_TYPE controls the calculation task.\n",
        encoding="utf-8",
    )
    source_ref = f"raw/assets/cp2k-{version}.md"
    manifest = {
        "manifest_version": 1,
        "software": "cp2k",
        "software_version": version,
        "generated_at": "2026-06-12T00:00:00Z",
        "sources": [
            {
                "source_ref": source_ref,
                "kind": "documentation",
                "path": source_ref,
                "sha256": "0" * 64,
                "size_bytes": source_path.stat().st_size,
                "version": version,
                "confidence": confidence,
            }
        ],
        "dsl_ir": {
            "keywords": keywords
            or [
                {
                    "name": "RUN_TYPE",
                    "section": "GLOBAL",
                    "type": "enum",
                    "enum": ["ENERGY", "ENERGY_FORCE"],
                    "default": "ENERGY_FORCE",
                    "description": "Selects the CP2K calculation task.",
                    "status": "active",
                    "confidence": confidence,
                    "source_ref": source_ref,
                }
            ]
        },
    }
    manifest_path = root / "sources" / "cp2k" / f"{version}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _init_wiki_root(root: Path) -> None:
    for rel in ("wiki/entities", "wiki/concepts", "wiki/synthesis"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / "index.md").write_text("# CP2K Wiki\n", encoding="utf-8")
    (root / "log.md").write_text("# Change Log\n", encoding="utf-8")


def test_generate_runs_factory_dag_and_updates_wiki(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(tmp_path, "2026.1")

    assert factory_main(["--root", str(tmp_path), "generate", "--software", "cp2k", "--version", "2026.1"]) == 0
    assert factory_main(["--root", str(tmp_path), "generate", "--software", "cp2k", "--version", "2026.1"]) == 0

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "2026.1"
    dsl_ir = json.loads((run_dir / "dsl_ir.json").read_text(encoding="utf-8"))
    assert dsl_ir["software"] == "cp2k"
    assert dsl_ir["version"] == "2026.1"
    assert dsl_ir["status"] == "success"
    assert {item["name"] for item in dsl_ir["keywords"]} == {"RUN_TYPE"}

    handoffs = sorted((run_dir / "handoffs").glob("*.json"))
    assert [json.loads(path.read_text(encoding="utf-8"))["skill"] for path in handoffs] == [
        "doc-ingest",
        "keyword-extract",
        "grammar-infer",
        "schema-normalize",
        "parser-generate",
        "linter-generate",
        "formatter-generate",
        "lsp-generate",
        "test-generate",
        "wiki-update",
        "wiki-lint",
        "verifier",
    ]
    assert all(json.loads(path.read_text(encoding="utf-8"))["status"] == "success" for path in handoffs)
    assert all(
        json.loads(path.read_text(encoding="utf-8"))["outputs"]["run_dir"] == "generated/openqc_lsp_factory/cp2k/2026.1"
        for path in handoffs
    )
    log_text = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert "openqc-lsp-factory generate --software cp2k --version 2026.1" in log_text
    assert log_text.count("openqc-lsp-factory generate --software cp2k --version 2026.1") == 1
    current_state = (tmp_path / "wiki" / "current-state.md").read_text(encoding="utf-8")
    assert "cp2k 2026.1" in current_state
    assert "## Sources" in current_state
    assert "generated/openqc_lsp_factory/cp2k/2026.1/dsl_ir.json" in current_state


def test_generate_routes_low_confidence_sources_to_review_queue(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(tmp_path, "2026.2", confidence=0.35)

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "generate",
                "--software",
                "cp2k",
                "--version",
                "2026.2",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    review = json.loads(
        (tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "2026.2" / "review" / "generate-review.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["status"] == "review_required"
    assert review["items"][0]["reason"] == "low_confidence_source"
    assert not (tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "2026.2" / "artifacts" / "lsp_stub.json").exists()


def test_generate_routes_low_confidence_keywords_to_review_queue(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(
        tmp_path,
        "2026.3",
        confidence=0.95,
        keywords=[
            {
                "name": "RUN_TYPE",
                "status": "active",
                "confidence": 0.35,
                "source_ref": "raw/assets/cp2k-2026.3.md",
            }
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "generate",
                "--software",
                "cp2k",
                "--version",
                "2026.3",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "2026.3"
    review = json.loads((run_dir / "review" / "generate-review.json").read_text(encoding="utf-8"))
    assert review["status"] == "review_required"
    assert review["items"][0]["reason"] == "low_confidence_keyword"
    assert review["items"][0]["keyword"] == "RUN_TYPE"
    assert not (run_dir / "artifacts" / "lsp_stub.json").exists()


def test_release_diff_outputs_structured_changes_policy_and_wiki_updates(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(
        tmp_path,
        "2025.2",
        keywords=[
            {"name": "OLD_KEY", "status": "active", "confidence": 0.95, "source_ref": "raw/assets/cp2k-2025.2.md"},
            {"name": "RENAMED_KEY", "status": "active", "confidence": 0.95, "source_ref": "raw/assets/cp2k-2025.2.md"},
            {
                "name": "EPS_SCF",
                "section": "SCF",
                "type": "float",
                "default": "1e-6",
                "enum": ["1e-6"],
                "unit": "",
                "description": "SCF threshold.",
                "status": "active",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2025.2.md",
            },
        ],
    )
    _write_manifest(
        tmp_path,
        "2026.1",
        keywords=[
            {
                "name": "NEW_NAME",
                "renamed_from": "RENAMED_KEY",
                "status": "active",
                "replacement": "NEW_NAME",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2026.1.md",
            },
            {
                "name": "EPS_SCF",
                "section": "SCF",
                "type": "float",
                "default": "1e-7",
                "enum": ["1e-7", "1e-8"],
                "unit": "hartree",
                "description": "Tighter SCF threshold.",
                "status": "active",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2026.1.md",
            },
            {
                "name": "DEPRECATED_KEY",
                "status": "deprecated",
                "replacement": "NEW_NAME",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2026.1.md",
            },
            {"name": "ADDED_KEY", "status": "active", "confidence": 0.95, "source_ref": "raw/assets/cp2k-2026.1.md"},
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "release-diff",
                "--software",
                "cp2k",
                "--from",
                "2025.2",
                "--to",
                "2026.1",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "release-diff-2025.2-to-2026.1"
    diff = json.loads((run_dir / "release_diff.json").read_text(encoding="utf-8"))
    kinds = {change["kind"] for change in diff["changes"]}
    assert {"added", "removed", "renamed", "deprecated", "changed"} <= kinds
    assert any(change["field"] == "default" for change in diff["changes"] if change["kind"] == "changed")
    assert any(change["field"] == "enum" for change in diff["changes"] if change["kind"] == "changed")
    version_policy = json.loads((run_dir / "version_policy.json").read_text(encoding="utf-8"))
    policy_by_name = {item["name"]: item for item in version_policy["keywords"]}
    assert policy_by_name["OLD_KEY"]["status"] == "removed"
    assert policy_by_name["RENAMED_KEY"]["status"] == "removed"
    assert policy_by_name["RENAMED_KEY"]["replacement"] == "NEW_NAME"
    assert not (run_dir / "review" / "release-diff-review.json").exists()

    handoffs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir / "handoffs").glob("*.json"))]
    assert any(item["skill"] == "release-diff" and item["agent_role"] == "ReleaseDiffAgent" for item in handoffs)
    assert all(
        item["outputs"]["run_dir"] == "generated/openqc_lsp_factory/cp2k/release-diff-2025.2-to-2026.1"
        for item in handoffs
    )
    notes = (tmp_path / "wiki" / "synthesis" / "release-diff-cp2k-2025.2-to-2026.1.md").read_text(encoding="utf-8")
    assert "RENAMED_KEY -> NEW_NAME" in notes
    assert "DEPRECATED_KEY -> NEW_NAME" in notes
    assert "## Sources" in notes
    assert "generated/openqc_lsp_factory/cp2k/release-diff-2025.2-to-2026.1/version_policy.json" in notes
    assert "openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1" in (
        tmp_path / "log.md"
    ).read_text(encoding="utf-8")


def test_release_diff_routes_low_confidence_sources_to_review_queue(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(
        tmp_path,
        "2025.2",
        confidence=0.95,
        keywords=[
            {
                "name": "RUN_TYPE",
                "section": "GLOBAL",
                "type": "enum",
                "enum": ["ENERGY", "ENERGY_FORCE"],
                "default": "ENERGY",
                "description": "Selects the CP2K calculation task.",
                "status": "active",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2025.2.md",
            }
        ],
    )
    _write_manifest(
        tmp_path,
        "2026.1",
        confidence=0.2,
        keywords=[
            {
                "name": "RUN_TYPE",
                "section": "GLOBAL",
                "type": "enum",
                "enum": ["ENERGY", "ENERGY_FORCE"],
                "default": "ENERGY",
                "description": "Selects the CP2K calculation task.",
                "status": "active",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2026.1.md",
            }
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "release-diff",
                "--software",
                "cp2k",
                "--from",
                "2025.2",
                "--to",
                "2026.1",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "release-diff-2025.2-to-2026.1"
    diff = json.loads((run_dir / "release_diff.json").read_text(encoding="utf-8"))
    assert diff["status"] == "review_required"
    review = json.loads((run_dir / "review" / "release-diff-review.json").read_text(encoding="utf-8"))
    assert review["status"] == "review_required"
    assert review["items"][0]["reason"] == "low_confidence_source"
    assert review["items"][0]["release_side"] == "to"
    assert not (run_dir / "version_policy.json").exists()
    assert not (tmp_path / "wiki" / "synthesis" / "release-diff-cp2k-2025.2-to-2026.1.md").exists()
    current_state = tmp_path / "wiki" / "current-state.md"
    assert not current_state.exists() or "release diff from 2025.2" not in current_state.read_text(encoding="utf-8")
    assert "openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1" not in (
        tmp_path / "log.md"
    ).read_text(encoding="utf-8")


def test_release_diff_review_required_does_not_promote_version_policy_or_wiki(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(
        tmp_path,
        "2025.2",
        keywords=[
            {
                "name": "EPS_SCF",
                "section": "SCF",
                "type": "float",
                "default": "1e-6",
                "status": "active",
                "confidence": 0.95,
                "source_ref": "raw/assets/cp2k-2025.2.md",
            }
        ],
    )
    _write_manifest(
        tmp_path,
        "2026.1",
        keywords=[
            {
                "name": "EPS_SCF",
                "section": "SCF",
                "type": "float",
                "default": "1e-7",
                "status": "active",
                "confidence": 0.4,
                "source_ref": "raw/assets/cp2k-2026.1.md",
            }
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "release-diff",
                "--software",
                "cp2k",
                "--from",
                "2025.2",
                "--to",
                "2026.1",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "release-diff-2025.2-to-2026.1"
    review = json.loads((run_dir / "review" / "release-diff-review.json").read_text(encoding="utf-8"))
    assert {item["reason"] for item in review["items"]} >= {"low_confidence_keyword", "low_confidence_change"}
    assert not (run_dir / "version_policy.json").exists()
    assert not (tmp_path / "wiki" / "synthesis" / "release-diff-cp2k-2025.2-to-2026.1.md").exists()
    assert "openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1" not in (
        tmp_path / "log.md"
    ).read_text(encoding="utf-8")


def test_release_diff_low_confidence_rerun_removes_stale_promotions(tmp_path: Path) -> None:
    _init_wiki_root(tmp_path)
    _write_manifest(
        tmp_path,
        "2025.2",
        keywords=[
            {"name": "OLD_KEY", "status": "active", "confidence": 0.95, "source_ref": "raw/assets/cp2k-2025.2.md"},
        ],
    )
    _write_manifest(
        tmp_path,
        "2026.1",
        keywords=[
            {"name": "NEW_KEY", "status": "active", "confidence": 0.95, "source_ref": "raw/assets/cp2k-2026.1.md"},
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "release-diff",
                "--software",
                "cp2k",
                "--from",
                "2025.2",
                "--to",
                "2026.1",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "release-diff-2025.2-to-2026.1"
    assert (run_dir / "version_policy.json").exists()
    assert (tmp_path / "wiki" / "synthesis" / "release-diff-cp2k-2025.2-to-2026.1.md").exists()

    current_state = (tmp_path / "wiki" / "current-state.md").read_text(encoding="utf-8")
    assert "release diff from 2025.2" in current_state

    log_text = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert "openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1" in log_text

    _write_manifest(
        tmp_path,
        "2026.1",
        keywords=[
            {"name": "NEW_KEY", "status": "active", "confidence": 0.3, "source_ref": "raw/assets/cp2k-2026.1.md"},
        ],
    )

    assert (
        factory_main(
            [
                "--root",
                str(tmp_path),
                "release-diff",
                "--software",
                "cp2k",
                "--from",
                "2025.2",
                "--to",
                "2026.1",
                "--min-confidence",
                "0.8",
            ]
        )
        == 0
    )

    review = json.loads((run_dir / "review" / "release-diff-review.json").read_text(encoding="utf-8"))
    assert review["status"] == "review_required"
    assert not (run_dir / "version_policy.json").exists()
    assert not (tmp_path / "wiki" / "synthesis" / "release-diff-cp2k-2025.2-to-2026.1.md").exists()

    current_state_after = (tmp_path / "wiki" / "current-state.md").read_text(encoding="utf-8")
    assert "release diff from 2025.2" not in current_state_after

    log_text_after = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert "openqc-lsp-factory release-diff --software cp2k --from 2025.2 --to 2026.1" not in log_text_after


def test_version_policy_lint_distinguishes_removed_deprecated_and_unknown_keywords() -> None:
    policy = {
        "software": "cp2k",
        "version": "2026.1",
        "keywords": [
            {"name": "OLD_KEY", "status": "removed", "replacement": "NEW_KEY"},
            {"name": "DEPRECATED_KEY", "status": "deprecated", "replacement": "NEW_KEY"},
            {"name": "NEW_KEY", "status": "active"},
        ],
    }
    diagnostics = lint_version_policy("OLD_KEY yes\nDEPRECATED_KEY yes\nUNKNOWN_KEY yes\n", policy)

    by_code = {item.code: item for item in diagnostics}
    assert by_code["cp2k.version.removed_keyword"].severity == "error"
    assert "NEW_KEY" in (by_code["cp2k.version.removed_keyword"].suggested_fix or "")
    assert by_code["cp2k.version.deprecated_keyword"].severity == "warning"
    assert "NEW_KEY" in (by_code["cp2k.version.deprecated_keyword"].suggested_fix or "")
    assert by_code["cp2k.version.unknown_keyword"].severity == "warning"


def test_version_policy_lint_skips_coordinate_data_rows() -> None:
    policy = {
        "software": "cp2k",
        "version": "2026.1",
        "keywords": [
            {"name": "PROJECT", "status": "active"},
            {"name": "RUN_TYPE", "status": "active"},
        ],
    }
    text = """&GLOBAL
  PROJECT demo
&END GLOBAL
&FORCE_EVAL
  &SUBSYS
    &COORD
      H 0.0 0.0 0.0
      O 0.0 0.0 1.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""

    diagnostics = lint_version_policy(text, policy)

    assert not any(item.code == "cp2k.version.unknown_keyword" for item in diagnostics)


def test_version_policy_reaches_agent_check_payload(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "version_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "software": "cp2k",
                "version": "2026.1",
                "keywords": [
                    {"name": "OLD_KEY", "status": "removed", "replacement": "NEW_KEY"},
                    {"name": "DEPRECATED_KEY", "status": "deprecated", "replacement": "NEW_KEY"},
                    {"name": "NEW_KEY", "status": "active"},
                ],
            }
        ),
        encoding="utf-8",
    )
    input_path = tmp_path / "input.inp"
    input_path.write_text("OLD_KEY yes\nDEPRECATED_KEY yes\n", encoding="utf-8")
    monkeypatch.setenv("CP2K_VERSION_POLICY", str(policy_path))

    payload = check_path(input_path)
    by_code = {item["code"]: item for item in payload["diagnostics"]}
    assert by_code["cp2k.version.removed_keyword"]["severity"] == "error"
    assert by_code["cp2k.version.deprecated_keyword"]["severity"] == "warning"
    assert by_code["cp2k.version.removed_keyword"]["fix_hints"] == ["Replace OLD_KEY with NEW_KEY."]


def test_version_policy_reaches_cp2k_lsp_tool_console_script(tmp_path: Path, monkeypatch, script_runner) -> None:
    policy_path = tmp_path / "version_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "software": "cp2k",
                "version": "2026.1",
                "keywords": [
                    {"name": "OLD_KEY", "status": "removed", "replacement": "NEW_KEY"},
                    {"name": "NEW_KEY", "status": "active"},
                ],
            }
        ),
        encoding="utf-8",
    )
    input_path = tmp_path / "input.inp"
    input_path.write_text("OLD_KEY yes\n", encoding="utf-8")
    monkeypatch.setenv("CP2K_VERSION_POLICY", str(policy_path))

    result = script_runner.run(["cp2k-lsp-tool", "check", str(input_path)])

    assert result.success
    payload = json.loads(result.stdout)
    by_code = {item["code"]: item for item in payload["diagnostics"]}
    assert by_code["cp2k.version.removed_keyword"]["fix_hints"] == ["Replace OLD_KEY with NEW_KEY."]


def test_version_policy_lsp_code_action_suggests_replacement() -> None:
    diagnostic = lsp.Diagnostic(
        range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
        message="Keyword 'OLD_KEY' was removed in CP2K 2026.1.",
        severity=lsp.DiagnosticSeverity.Error,
        source="cp2k-version-policy",
        code="cp2k.version.removed_keyword",
        data={"suggested_fix": "Replace OLD_KEY with NEW_KEY."},
    )
    provider = CodeActionProvider.__new__(CodeActionProvider)

    action = provider._create_quick_fix(diagnostic, "file:///input.inp")

    assert action is not None
    assert action.title == "Replace with NEW_KEY"
    assert action.edit is not None
    assert action.edit.changes["file:///input.inp"][0].new_text == "NEW_KEY"


def test_source_manifests_validate_against_json_schema() -> None:
    schema = json.loads(Path("sources/manifest.schema.json").read_text(encoding="utf-8"))

    for manifest_path in sorted(Path("sources").glob("*/*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)


def test_capabilities_subcommand_returns_json_and_exits_zero(script_runner) -> None:
    result = script_runner.run(["cp2k-lsp-tool", "capabilities"])

    assert result.success
    payload = json.loads(result.stdout)
    assert payload["software"] == "cp2k"
    assert payload["status"] == "available"
    assert "capabilities" in payload
    caps = payload["capabilities"]
    assert caps["operation"] == "capabilities"
    assert caps["status"] == "available"
    assert "check" in caps["operations"]
    assert "context" in caps["operations"]
    assert "complete" in caps["operations"]
    assert "hover" in caps["operations"]
    assert "symbols" in caps["operations"]
    assert "fix" in caps["operations"]
    assert "capabilities" in caps["operations"]


# ---------------------------------------------------------------------------
# DSL IR validator subcommand tests (issue #67)
# ---------------------------------------------------------------------------

DSL_IR_DIR = Path("generated/openqc_lsp_factory/cp2k/0.9.1")


def test_validate_dsl_ir_accepts_generated_artifact() -> None:
    """The shipped dsl_ir.json must validate against the co-located schema."""
    dsl_ir_path = DSL_IR_DIR / "dsl_ir.json"
    assert dsl_ir_path.is_file(), f"Expected generated DSL IR at {dsl_ir_path}"
    assert factory_main(["validate-dsl-ir", str(dsl_ir_path)]) == 0


def test_validate_dsl_ir_schema_exists_next_to_artifact() -> None:
    schema_path = DSL_IR_DIR / "dsl_ir.schema.json"
    assert schema_path.is_file(), f"DSL IR schema not found at {schema_path}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "OpenQC DSL IR"


def test_validate_dsl_ir_rejects_missing_file() -> None:
    assert factory_main(["validate-dsl-ir", "/nonexistent/dsl_ir.json"]) == 2


def test_validate_dsl_ir_rejects_invalid_json() -> None:
    tmp = Path(__import__("tempfile").mkdtemp()) / "bad.json"
    tmp.write_text("{not valid json", encoding="utf-8")
    assert factory_main(["validate-dsl-ir", str(tmp)]) == 2


def test_validate_dsl_ir_rejects_payload_missing_keywords(tmp_path: Path) -> None:
    dsl_ir_path = tmp_path / "dsl_ir.json"
    schema_path = tmp_path / "dsl_ir.schema.json"
    # Write a co-located schema
    schema_path.write_text(
        Path("generated/openqc_lsp_factory/cp2k/0.9.1/dsl_ir.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    dsl_ir_path.write_text(
        json.dumps({"software": "cp2k", "version": "0.9.1", "status": "success"}),
        encoding="utf-8",
    )
    assert factory_main(["validate-dsl-ir", str(dsl_ir_path)]) == 1


def test_validate_dsl_ir_rejects_keyword_missing_required_fields(tmp_path: Path) -> None:
    dsl_ir_path = tmp_path / "dsl_ir.json"
    schema_path = tmp_path / "dsl_ir.schema.json"
    schema_path.write_text(
        Path("generated/openqc_lsp_factory/cp2k/0.9.1/dsl_ir.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    dsl_ir_path.write_text(
        json.dumps(
            {
                "software": "cp2k",
                "version": "0.9.1",
                "status": "success",
                "keywords": [
                    {"name": "FOO"},  # missing status, confidence, source_ref
                ],
            }
        ),
        encoding="utf-8",
    )
    assert factory_main(["validate-dsl-ir", str(dsl_ir_path)]) == 1


def test_validate_dsl_ir_rejects_unknown_status(tmp_path: Path) -> None:
    dsl_ir_path = tmp_path / "dsl_ir.json"
    schema_path = tmp_path / "dsl_ir.schema.json"
    schema_path.write_text(
        Path("generated/openqc_lsp_factory/cp2k/0.9.1/dsl_ir.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    dsl_ir_path.write_text(
        json.dumps(
            {
                "software": "cp2k",
                "version": "0.9.1",
                "status": "unknown_status",
                "keywords": [
                    {"name": "FOO", "status": "active", "confidence": 0.9, "source_ref": "test"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert factory_main(["validate-dsl-ir", str(dsl_ir_path)]) == 1


def test_generate_writes_dsl_ir_schema_next_to_artifact(tmp_path: Path) -> None:
    """Schema should be co-located whenever generate writes dsl_ir.json."""
    _init_wiki_root(tmp_path)
    _write_manifest(tmp_path, "2026.4")

    assert factory_main(["--root", str(tmp_path), "generate", "--software", "cp2k", "--version", "2026.4"]) == 0
    run_dir = tmp_path / "generated" / "openqc_lsp_factory" / "cp2k" / "2026.4"
    schema_path = run_dir / "dsl_ir.schema.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "OpenQC DSL IR"
