"""OpenQC DSL-to-LSP factory CLI for source-manifest driven CP2K updates."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validation_backends import validation_backends_payload

GENERATE_DAG = (
    ("doc-ingest", "DocIngestAgent"),
    ("keyword-extract", "GrammarAgent"),
    ("grammar-infer", "GrammarAgent"),
    ("schema-normalize", "IRAgent"),
    ("parser-generate", "ParserAgent"),
    ("linter-generate", "LinterAgent"),
    ("formatter-generate", "LSPAgent"),
    ("lsp-generate", "LSPAgent"),
    ("test-generate", "TestAgent"),
    ("wiki-update", "WikiMaintainerAgent"),
    ("wiki-lint", "WikiMaintainerAgent"),
    ("verifier", "VerifierAgent"),
)
RELEASE_DIFF_DAG = (
    ("doc-ingest", "DocIngestAgent"),
    ("keyword-extract", "GrammarAgent"),
    ("grammar-infer", "GrammarAgent"),
    ("schema-normalize", "IRAgent"),
    ("release-diff", "ReleaseDiffAgent"),
    ("linter-generate", "LinterAgent"),
    ("lsp-generate", "LSPAgent"),
    ("test-generate", "TestAgent"),
    ("wiki-update", "WikiMaintainerAgent"),
    ("wiki-lint", "WikiMaintainerAgent"),
    ("verifier", "VerifierAgent"),
)
CHANGE_FIELDS = ("default", "enum", "type", "unit", "section", "description")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openqc-lsp-factory")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--software", required=True)
    generate.add_argument("--version", required=True)
    generate.add_argument("--min-confidence", type=float, default=0.8)

    release_diff = subparsers.add_parser("release-diff")
    release_diff.add_argument("--software", required=True)
    release_diff.add_argument("--from", dest="from_version", required=True)
    release_diff.add_argument("--to", dest="to_version", required=True)
    release_diff.add_argument("--min-confidence", type=float, default=0.8)

    validate_dsl = subparsers.add_parser("validate-dsl-ir")
    validate_dsl.add_argument("path", type=Path, help="Path to a dsl_ir.json file to validate.")

    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "generate":
        return run_generate(root, args.software, args.version, args.min_confidence)
    if args.command == "release-diff":
        return run_release_diff(root, args.software, args.from_version, args.to_version, args.min_confidence)
    if args.command == "validate-dsl-ir":
        return run_validate_dsl_ir(args.path)
    return 2


def run_generate(root: Path, software: str, version: str, min_confidence: float = 0.8) -> int:
    manifest = _load_manifest(root, software, version)
    run_dir = _run_dir(root, software, version)
    _ensure_run_dirs(run_dir)
    keywords = _keywords_from_manifest(root, manifest, software, version)
    review_items = _low_confidence_sources(manifest, min_confidence)
    review_items.extend(_low_confidence_keywords(keywords, min_confidence))
    if not keywords:
        review_items.append(
            {
                "reason": "extraction_failed",
                "message": "No keywords were extracted from manifest DSL IR or source registry.",
                "min_confidence": min_confidence,
            }
        )
    status = "review_required" if review_items else "success"

    dsl_ir = {
        "software": software,
        "version": version,
        "status": status,
        "sources": manifest.get("sources", []),
        "keywords": keywords,
    }
    _write_json(run_dir / "dsl_ir.json", dsl_ir)
    _write_dsl_ir_schema(run_dir)
    _write_handoffs(root, run_dir, software, version, status, dsl_ir, review_items, dag=GENERATE_DAG)

    if review_items:
        _write_review(run_dir / "review" / "generate-review.json", "review_required", review_items)
        return 0

    _write_json(
        run_dir / "artifacts" / "lsp_stub.json",
        {
            "software": software,
            "version": version,
            "operations": ["check", "context", "complete", "hover", "symbols", "fix"],
            "validation_backends": validation_backends_payload(),
            "keyword_count": len(keywords),
            "source": str((root / "sources" / software / f"{version}.json").relative_to(root)),
        },
    )
    _update_current_state(
        root,
        f"- {software} {version}: factory generation success with {len(keywords)} keywords.",
        [
            f"sources/{software}/{version}.json",
            str((run_dir / "dsl_ir.json").relative_to(root)),
            str((run_dir / "handoffs" / "12-verifier.json").relative_to(root)),
        ],
    )
    _append_log(root, f"openqc-lsp-factory generate --software {software} --version {version}")
    return 0


def run_release_diff(root: Path, software: str, from_version: str, to_version: str, min_confidence: float = 0.8) -> int:
    old_manifest = _load_manifest(root, software, from_version)
    new_manifest = _load_manifest(root, software, to_version)
    old_keywords = _keywords_from_manifest(root, old_manifest, software, from_version)
    new_keywords = _keywords_from_manifest(root, new_manifest, software, to_version)
    changes = _diff_keywords(old_keywords, new_keywords)
    review_items = [
        *_with_release_context(_low_confidence_sources(old_manifest, min_confidence), "from", from_version),
        *_with_release_context(_low_confidence_sources(new_manifest, min_confidence), "to", to_version),
        *_with_release_context(_low_confidence_keywords(old_keywords, min_confidence), "from", from_version),
        *_with_release_context(_low_confidence_keywords(new_keywords, min_confidence), "to", to_version),
        *_low_confidence_changes(changes, min_confidence),
    ]

    run_dir = _run_dir(root, software, f"release-diff-{from_version}-to-{to_version}")
    _ensure_run_dirs(run_dir)
    status = "review_required" if review_items else "success"
    payload = {
        "software": software,
        "from_version": from_version,
        "to_version": to_version,
        "status": status,
        "changes": changes,
    }
    _write_json(run_dir / "release_diff.json", payload)
    _write_handoffs(root, run_dir, software, to_version, status, payload, review_items, mode="release-diff", dag=RELEASE_DIFF_DAG)
    if review_items:
        _write_review(run_dir / "review" / "release-diff-review.json", "review_required", review_items)
        _remove_release_promotions(root, run_dir, software, from_version, to_version)
        return 0

    _write_json(run_dir / "version_policy.json", _version_policy(software, to_version, new_keywords, changes))
    notes_path = root / "wiki" / "synthesis" / f"release-diff-{software}-{from_version}-to-{to_version}.md"
    _write_release_notes(
        notes_path,
        payload,
        [
            f"sources/{software}/{from_version}.json",
            f"sources/{software}/{to_version}.json",
            str((run_dir / "release_diff.json").relative_to(root)),
            str((run_dir / "version_policy.json").relative_to(root)),
        ],
    )
    _update_current_state(
        root,
        f"- {software} {to_version}: release diff from {from_version} produced {len(changes)} changes.",
        [
            f"sources/{software}/{from_version}.json",
            f"sources/{software}/{to_version}.json",
            str((run_dir / "release_diff.json").relative_to(root)),
        ],
    )
    _append_log(root, f"openqc-lsp-factory release-diff --software {software} --from {from_version} --to {to_version}")
    return 0


def run_validate_dsl_ir(path: Path) -> int:
    """Validate a DSL IR JSON file against the versioned schema.

    Returns 0 on success, 1 on validation failure, 2 on I/O errors.
    """
    import jsonschema  # type: ignore[import-untyped]

    path = path.resolve()
    if not path.is_file():
        print(f"Error: file not found: {path}", file=__import__("sys").stderr)
        return 2

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading {path}: {exc}", file=__import__("sys").stderr)
        return 2

    # Locate the co-located schema: same directory or one level up per version
    schema_path = _find_dsl_ir_schema(path)
    if schema_path is None:
        print("Error: could not locate dsl_ir.schema.json", file=__import__("sys").stderr)
        return 2

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        print(f"Validation error: {exc.message}", file=__import__("sys").stderr)
        return 1

    keyword_count = len(payload.get("keywords", []))
    print(f"OK: {path} is valid ({keyword_count} keywords).")
    return 0


def _find_dsl_ir_schema(dsl_ir_path: Path) -> Path | None:
    """Locate dsl_ir.schema.json next to the IR file or one level up."""
    for candidate in (
        dsl_ir_path.parent / "dsl_ir.schema.json",
        dsl_ir_path.parent.parent / "dsl_ir.schema.json",
    ):
        if candidate.is_file():
            return candidate
    return None


DSL_IR_SCHEMA_BODY: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/newtontech/cp2k-lsp-enhanced/generated/openqc_lsp_factory/cp2k/0.9.1/dsl_ir.schema.json",
    "title": "OpenQC DSL IR",
    "description": "Versioned DSL intermediate-representation artifact produced by the OpenQC LSP factory pipeline.",
    "type": "object",
    "required": ["software", "version", "status", "keywords"],
    "additionalProperties": False,
    "properties": {
        "software": {"type": "string", "minLength": 1},
        "version": {"type": "string", "minLength": 1},
        "status": {"type": "string", "enum": ["success", "review_required"]},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source_ref", "kind", "version", "confidence"],
                "additionalProperties": True,
                "properties": {
                    "source_ref": {"type": "string", "minLength": 1},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "documentation", "example", "schema",
                            "source", "release-notes", "agent-guidance",
                        ],
                    },
                    "path": {"type": "string", "minLength": 1},
                    "url": {"type": "string", "minLength": 1},
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "size_bytes": {"type": "integer", "minimum": 0},
                    "version": {"type": "string", "minLength": 1},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "notes": {"type": "string"},
                },
            },
        },
        "keywords": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "status", "confidence", "source_ref"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "section": {"type": "string"},
                    "type": {"type": "string", "enum": ["integer", "keyword", "logical", "real", "string", "word"]},
                    "enum": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "default": {"type": "string"},
                    "unit": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "deprecated", "removed"]},
                    "replacement": {"type": "string"},
                    "renamed_from": {"type": "string"},
                    "source_ref": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "version": {"type": "string"},
                },
            },
        },
    },
}


def _write_dsl_ir_schema(run_dir: Path) -> None:
    """Write the co-located DSL IR schema next to dsl_ir.json."""
    _write_json(run_dir / "dsl_ir.schema.json", DSL_IR_SCHEMA_BODY)


def _load_manifest(root: Path, software: str, version: str) -> dict[str, Any]:
    path = root / "sources" / software / f"{version}.json"
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return manifest


def _run_dir(root: Path, software: str, version: str) -> Path:
    return root / "generated" / "openqc_lsp_factory" / software / version


def _ensure_run_dirs(run_dir: Path) -> None:
    for rel in ("handoffs", "review", "artifacts"):
        (run_dir / rel).mkdir(parents=True, exist_ok=True)


def _keywords_from_manifest(root: Path, manifest: dict[str, Any], software: str, version: str) -> list[dict[str, Any]]:
    keywords = manifest.get("dsl_ir", {}).get("keywords", [])
    if isinstance(keywords, list) and keywords:
        return [_normalize_keyword(item) for item in keywords if isinstance(item, dict) and item.get("name")]
    if software == "cp2k":
        schema_path = root / "cp2k_input_tools" / "cp2k_input.xml"
        return _keywords_from_cp2k_xml(schema_path, version)
    return []


def _keywords_from_cp2k_xml(path: Path, version: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    keywords: dict[str, dict[str, Any]] = {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    for node in root.iter("KEYWORD"):
        name_node = node.find("./NAME")
        if name_node is None or not name_node.text:
            continue
        name = name_node.text.upper()
        if name in keywords:
            continue
        type_node = node.find("./DATA_TYPE")
        keyword: dict[str, Any] = {
            "name": name,
            "status": "active",
            "version": version,
            "confidence": 0.9,
            "source_ref": "cp2k_input_tools/cp2k_input.xml",
        }
        if type_node is not None:
            keyword["type"] = type_node.get("kind", "")
            enum = [item.text for item in type_node.findall("./ENUMERATION/ITEM/NAME") if item.text]
            if enum:
                keyword["enum"] = enum
        default_node = node.find("./DEFAULT_VALUE")
        if default_node is not None and default_node.text:
            keyword["default"] = default_node.text.strip()
        keywords[name] = keyword
    return sorted(keywords.values(), key=lambda item: item["name"])


def _normalize_keyword(item: dict[str, Any]) -> dict[str, Any]:
    keyword = dict(item)
    keyword["name"] = str(keyword["name"]).upper()
    if keyword.get("renamed_from"):
        keyword["renamed_from"] = str(keyword["renamed_from"]).upper()
    if keyword.get("replacement"):
        keyword["replacement"] = str(keyword["replacement"]).upper()
    keyword.setdefault("status", "active")
    keyword.setdefault("confidence", 1.0)
    return keyword


def _low_confidence_sources(manifest: dict[str, Any], min_confidence: float) -> list[dict[str, Any]]:
    items = []
    for source in manifest.get("sources", []):
        confidence = float(source.get("confidence", 0.0) or 0.0)
        if confidence < min_confidence:
            items.append(
                {
                    "reason": "low_confidence_source",
                    "source_ref": source.get("source_ref"),
                    "confidence": confidence,
                    "min_confidence": min_confidence,
                }
            )
    return items


def _low_confidence_keywords(keywords: list[dict[str, Any]], min_confidence: float) -> list[dict[str, Any]]:
    items = []
    for keyword in keywords:
        confidence = float(keyword.get("confidence", 0.0) or 0.0)
        if confidence < min_confidence:
            items.append(
                {
                    "reason": "low_confidence_keyword",
                    "keyword": keyword.get("name"),
                    "source_ref": keyword.get("source_ref"),
                    "confidence": confidence,
                    "min_confidence": min_confidence,
                }
            )
    return items


def _low_confidence_changes(changes: list[dict[str, Any]], min_confidence: float) -> list[dict[str, Any]]:
    items = []
    for change in changes:
        confidence = float(change.get("confidence", 1.0) or 0.0)
        if confidence < min_confidence:
            items.append(
                {
                    "reason": "low_confidence_change",
                    "keyword": change.get("keyword") or change.get("new_keyword") or change.get("old_keyword"),
                    "kind": change.get("kind"),
                    "confidence": confidence,
                    "min_confidence": min_confidence,
                }
            )
    return items


def _diff_keywords(old_keywords: list[dict[str, Any]], new_keywords: list[dict[str, Any]]) -> list[dict[str, Any]]:
    old_by_name = {item["name"]: item for item in old_keywords}
    new_by_name = {item["name"]: item for item in new_keywords}
    changes: list[dict[str, Any]] = []
    renamed_old: set[str] = set()
    renamed_new: set[str] = set()

    for new_name, new_item in sorted(new_by_name.items()):
        old_name = str(new_item.get("renamed_from", "") or "").upper()
        if old_name and old_name in old_by_name:
            renamed_old.add(old_name)
            renamed_new.add(new_name)
            changes.append(
                {
                    "kind": "renamed",
                    "old_keyword": old_name,
                    "new_keyword": new_name,
                    "replacement": new_name,
                    "confidence": float(new_item.get("confidence", 1.0) or 0.0),
                }
            )

    for old_name in sorted(set(old_by_name) - set(new_by_name) - renamed_old):
        old_item = old_by_name[old_name]
        changes.append(
            {
                "kind": "removed",
                "keyword": old_name,
                "confidence": float(old_item.get("confidence", 1.0) or 0.0),
            }
        )

    for new_name in sorted(set(new_by_name) - set(old_by_name) - renamed_new):
        new_item = new_by_name[new_name]
        status = str(new_item.get("status", "active")).lower()
        if status == "deprecated":
            changes.append(
                {
                    "kind": "deprecated",
                    "keyword": new_name,
                    "replacement": new_item.get("replacement"),
                    "confidence": float(new_item.get("confidence", 1.0) or 0.0),
                }
            )
        else:
            changes.append(
                {
                    "kind": "added",
                    "keyword": new_name,
                    "confidence": float(new_item.get("confidence", 1.0) or 0.0),
                }
            )

    for name in sorted(set(old_by_name) & set(new_by_name)):
        old_item = old_by_name[name]
        new_item = new_by_name[name]
        status = str(new_item.get("status", "active")).lower()
        if status == "deprecated":
            changes.append(
                {
                    "kind": "deprecated",
                    "keyword": name,
                    "replacement": new_item.get("replacement"),
                    "confidence": float(new_item.get("confidence", 1.0) or 0.0),
                }
            )
        for field in CHANGE_FIELDS:
            if old_item.get(field) != new_item.get(field):
                changes.append(
                    {
                        "kind": "changed",
                        "keyword": name,
                        "field": field,
                        "old": old_item.get(field),
                        "new": new_item.get(field),
                        "confidence": min(
                            float(old_item.get("confidence", 1.0) or 0.0),
                            float(new_item.get("confidence", 1.0) or 0.0),
                        ),
                    }
                )
    return changes


def _with_release_context(items: list[dict[str, Any]], release_side: str, version: str) -> list[dict[str, Any]]:
    contextualized = []
    for item in items:
        contextualized.append(
            {
                **item,
                "release_side": release_side,
                "version": version,
            }
        )
    return contextualized


def _version_policy(
    software: str,
    version: str,
    keywords: list[dict[str, Any]],
    changes: list[dict[str, Any]],
) -> dict[str, Any]:
    policy_keywords = [
        {
            key: item[key]
            for key in ("name", "status", "replacement", "renamed_from")
            if key in item
        }
        for item in keywords
    ]
    policy_names = {str(item.get("name", "")).upper() for item in policy_keywords}
    for change in changes:
        if change["kind"] == "removed" and str(change["keyword"]).upper() not in policy_names:
            policy_keywords.append({"name": change["keyword"], "status": "removed"})
            policy_names.add(str(change["keyword"]).upper())
        elif change["kind"] == "renamed" and str(change["old_keyword"]).upper() not in policy_names:
            policy_keywords.append(
                {
                    "name": change["old_keyword"],
                    "status": "removed",
                    "replacement": change["new_keyword"],
                }
            )
            policy_names.add(str(change["old_keyword"]).upper())
    return {
        "software": software,
        "version": version,
        "keywords": policy_keywords,
    }


def _write_handoffs(
    root: Path,
    run_dir: Path,
    software: str,
    version: str,
    status: str,
    payload: dict[str, Any],
    review_items: list[dict[str, Any]],
    *,
    mode: str = "generate",
    dag: tuple[tuple[str, str], ...],
) -> None:
    for index, (skill, role) in enumerate(dag, start=1):
        handoff = {
            "schema_version": 1,
            "mode": mode,
            "software": software,
            "version": version,
            "skill": skill,
            "agent_role": role,
            "status": status,
            "inputs": {
                "software": software,
                "version": version,
            },
            "outputs": {
                "run_dir": _relative_to_root(run_dir, root),
                "payload": "release_diff.json" if mode == "release-diff" else "dsl_ir.json",
            },
            "confidence": 0.5 if review_items else 0.95,
            "open_questions": review_items,
            "next_agent_suggestions": _next_agents(index, dag),
        }
        _write_json(run_dir / "handoffs" / f"{index:02d}-{skill}.json", handoff)


def _next_agents(index: int, dag: tuple[tuple[str, str], ...]) -> list[str]:
    if index >= len(dag):
        return []
    return [dag[index][1]]


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _write_review(path: Path, status: str, items: list[dict[str, Any]]) -> None:
    _write_json(path, {"status": status, "items": items})


def _write_release_notes(path: Path, payload: dict[str, Any], sources: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Release Diff: {payload['software']} {payload['from_version']} to {payload['to_version']}",
        "",
        "## Structured Changes",
        "",
    ]
    for change in payload["changes"]:
        kind = change["kind"]
        if kind == "renamed":
            lines.append(f"- renamed: {change['old_keyword']} -> {change['new_keyword']}")
        elif kind == "deprecated":
            replacement = change.get("replacement")
            suffix = f" -> {replacement}" if replacement else ""
            lines.append(f"- deprecated: {change['keyword']}{suffix}")
        elif kind == "changed":
            lines.append(f"- changed: {change['keyword']} `{change['field']}` from `{change.get('old')}` to `{change.get('new')}`")
        else:
            lines.append(f"- {kind}: {change['keyword']}")
    lines.extend(["", "## Human Review Checklist", "", "- Review low-confidence changes before promoting generated diagnostics."])
    lines.extend(_sources_section(sources))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_current_state(root: Path, line: str, sources: list[str]) -> None:
    path = root / "wiki" / "current-state.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Current State\n\n"
    if existing.strip() == "# Current State":
        existing = "# Current State\n\n"
    if line not in existing:
        existing = _append_state_line(existing, line)
    existing = _merge_sources(existing, sources)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing, encoding="utf-8")


def _append_state_line(text: str, line: str) -> str:
    lines = text.rstrip().splitlines()
    try:
        sources_index = next(index for index, item in enumerate(lines) if item.strip() == "## Sources")
    except StopIteration:
        return text.rstrip() + "\n" + line + "\n"
    body = lines[:sources_index]
    sources = lines[sources_index:]
    while body and not body[-1].strip():
        body.pop()
    return "\n".join([*body, line, "", *sources]) + "\n"


def _merge_sources(text: str, sources: list[str]) -> str:
    lines = text.rstrip().splitlines()
    if not any(line.strip() == "## Sources" for line in lines):
        return text.rstrip() + "\n" + "\n".join(_sources_section(sources)) + "\n"
    existing = set(lines)
    for source in sources:
        entry = f"- `{source}`"
        if entry not in existing:
            lines.append(entry)
    return "\n".join(lines) + "\n"


def _sources_section(sources: list[str]) -> list[str]:
    return ["", "## Sources", "", *[f"- `{source}`" for source in sources]]


def _append_log(root: Path, command: str) -> None:
    path = root / "log.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Change Log\n"
    if f"- `{command}`" in existing:
        return
    entry = f"\n## {_now_date()} - OpenQC LSP Factory\n\n- `{command}`\n"
    path.write_text(existing.rstrip() + entry + "\n", encoding="utf-8")


def _remove_release_promotions(root: Path, run_dir: Path, software: str, from_version: str, to_version: str) -> None:
    notes_path = root / "wiki" / "synthesis" / f"release-diff-{software}-{from_version}-to-{to_version}.md"
    for path in (run_dir / "version_policy.json", notes_path):
        if path.exists():
            path.unlink()
    _remove_state_line(root, f"{software} {to_version}: release diff from {from_version}")
    _remove_log_entry(
        root,
        f"openqc-lsp-factory release-diff --software {software} --from {from_version} --to {to_version}",
    )


def _remove_state_line(root: Path, line_substring: str) -> None:
    path = root / "wiki" / "current-state.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    filtered = [line for line in lines if line_substring not in line]
    path.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def _remove_log_entry(root: Path, command_substring: str) -> None:
    path = root / "log.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    entries = text.split("\n\n")
    filtered = [entry for entry in entries if command_substring not in entry]
    path.write_text("\n\n".join(filtered) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
