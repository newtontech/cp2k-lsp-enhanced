#!/usr/bin/env python3
"""Validate the repo-local LLM Wiki provenance contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

RAW_ASSET_MAX_BYTES = 2 * 1024 * 1024
REQUIRED_PATHS = (
    "AGENTS.md",
    "index.md",
    "log.md",
    "wiki/entities",
    "wiki/concepts",
    "wiki/synthesis",
    "raw/assets",
    "sources/manifest.schema.json",
)
REQUIRED_SOURCE_FIELDS = (
    "source_ref",
    "kind",
    "version",
    "confidence",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _validate_manifest(path: Path, root: Path) -> list[str]:
    errors: list[str] = []
    manifest = _load_json(path)
    for field in ("manifest_version", "software", "software_version", "generated_at", "sources"):
        if field not in manifest:
            errors.append(f"{path}: missing top-level field {field}")
    sources = manifest.get("sources", [])
    if not isinstance(sources, list) or not sources:
        errors.append(f"{path}: sources must be a non-empty array")
        return errors

    seen: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"{path}: sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix}: source entry must be an object")
            continue
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(f"{prefix}: missing field {field}")
        source_ref = source.get("source_ref")
        if isinstance(source_ref, str):
            if source_ref in seen:
                errors.append(f"{prefix}: duplicate source_ref {source_ref}")
            seen.add(source_ref)
        confidence = source.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append(f"{prefix}: confidence must be between 0 and 1")

        rel_path = source.get("path")
        if rel_path is None:
            continue
        file_path = root / rel_path
        if not file_path.exists():
            errors.append(f"{prefix}: path does not exist: {rel_path}")
            continue
        expected_size = source.get("size_bytes")
        if expected_size is not None and file_path.stat().st_size != expected_size:
            errors.append(f"{prefix}: size_bytes mismatch for {rel_path}")
        expected_sha = source.get("sha256")
        if expected_sha is not None and _sha256(file_path) != expected_sha:
            errors.append(f"{prefix}: sha256 mismatch for {rel_path}")
    return errors


def _manifest_source_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for manifest_path in sorted((root / "sources").glob("*/*.json")):
        manifest = _load_json(manifest_path)
        for source in manifest.get("sources", []):
            rel_path = source.get("path")
            if isinstance(rel_path, str):
                paths.add(rel_path)
    return paths


def lint(root: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_PATHS:
        if not (root / rel_path).exists():
            errors.append(f"missing required path: {rel_path}")

    manifest_paths = sorted((root / "sources").glob("*/*.json"))
    if not manifest_paths:
        errors.append("missing versioned source manifest under sources/<software>/")
    for manifest_path in manifest_paths:
        errors.extend(_validate_manifest(manifest_path, root))

    manifest_paths_set = _manifest_source_paths(root)
    for asset_path in sorted((root / "raw/assets").glob("*")):
        if not asset_path.is_file():
            continue
        if asset_path.name.startswith("."):
            continue
        rel_path = asset_path.relative_to(root).as_posix()
        if asset_path.stat().st_size > RAW_ASSET_MAX_BYTES:
            errors.append(f"raw asset exceeds {RAW_ASSET_MAX_BYTES} bytes: {rel_path}")
        if rel_path not in manifest_paths_set:
            errors.append(f"raw asset missing from source manifest: {rel_path}")

    for wiki_path in sorted((root / "wiki").glob("**/*.md")):
        text = wiki_path.read_text(encoding="utf-8")
        rel_path = wiki_path.relative_to(root).as_posix()
        if "## 参考来源 (Sources)" not in text and "## Sources" not in text:
            errors.append(f"wiki page missing Sources section: {rel_path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    errors = lint(root)
    if errors:
        for error in errors:
            print(f"wiki-lint: {error}", file=sys.stderr)
        return 1
    print("wiki-lint: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
