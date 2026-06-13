"""Precomputed schema and docs indexes for faster LSP startup (issue #125)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import DEFAULT_CP2K_INPUT_XML

if TYPE_CHECKING:
    from .schema_index import CP2KSchemaIndex

GENERATED_DIR = Path(__file__).resolve().parent / "generated"
DEFAULT_SCHEMA_INDEX_JSON = GENERATED_DIR / "schema_index.json"
DEFAULT_DOCS_DIGEST_JSON = GENERATED_DIR / "docs_digest_index.json"
INDEX_VERSION = 1


def _path_key(path: tuple[str, ...]) -> str:
    return "|".join(path)


def _path_from_key(key: str) -> tuple[str, ...]:
    return tuple(part for part in key.split("|") if part)


def build_schema_index_payload(
    index: CP2KSchemaIndex,
    *,
    release_version: str | None = None,
    xml_path: Path = DEFAULT_CP2K_INPUT_XML,
) -> dict[str, Any]:
    """Serialize a loaded schema index to a compact JSON-friendly payload."""
    index._ensure_loaded()
    stat = os.stat(xml_path)
    sections: dict[str, Any] = {}
    keywords: dict[str, Any] = {}

    for path, section in index._sections.items():
        sections[_path_key(path)] = {
            "name": section.name,
            "description": section.description,
            "subsections": list(section.subsections),
            "keywords": list(section.keywords),
        }

    for path, section_keywords in index._keywords.items():
        keywords[_path_key(path)] = {
            name: {
                "name": spec.name,
                "variable_type": spec.variable_type,
                "default_value": spec.default_value,
                "enumeration_values": list(spec.enumeration_values),
                "description": spec.description,
            }
            for name, spec in section_keywords.items()
        }

    return {
        "version": INDEX_VERSION,
        "release_version": release_version,
        "source_xml": xml_path.name,
        "source_mtime": stat.st_mtime,
        "source_size": stat.st_size,
        "root_sections": list(index._root_section_names),
        "sections": sections,
        "keywords": keywords,
    }


def build_docs_digest_payload(
    index: CP2KSchemaIndex,
    *,
    release_version: str | None = None,
) -> dict[str, Any]:
    """Build a searchable docs digest from schema descriptions."""
    index._ensure_loaded()
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for path, section in index._sections.items():
        section_name = path[-1] if path else section.name
        if section.description:
            key = (section_name, "")
            if key not in seen:
                seen.add(key)
                entries.append(
                    {
                        "section": section_name,
                        "keyword": "",
                        "description": section.description,
                        "category": "section",
                    }
                )

    for path, section_keywords in index._keywords.items():
        section_name = path[-1] if path else ""
        for spec in section_keywords.values():
            if not spec.description:
                continue
            key = (section_name, spec.name)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "section": section_name,
                    "keyword": spec.name,
                    "description": spec.description,
                    "category": "keyword",
                }
            )

    entries.sort(key=lambda item: (item["section"], item["keyword"]))
    return {
        "version": INDEX_VERSION,
        "release_version": release_version,
        "entries": entries,
    }


def precomputed_schema_is_stale(json_path: Path, xml_path: Path = DEFAULT_CP2K_INPUT_XML) -> bool:
    """Return True when the precomputed schema index is missing or out of date."""
    if not json_path.is_file():
        return True
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        stat = os.stat(xml_path)
        return (
            payload.get("source_mtime") != stat.st_mtime
            or payload.get("source_size") != stat.st_size
            or payload.get("version") != INDEX_VERSION
        )
    except (OSError, json.JSONDecodeError, TypeError):
        return True


def regenerate_indexes(
    *,
    release_version: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_INDEX_JSON,
    docs_path: Path = DEFAULT_DOCS_DIGEST_JSON,
    xml_path: Path = DEFAULT_CP2K_INPUT_XML,
) -> dict[str, Any]:
    """Regenerate schema and docs digest indexes from cp2k_input.xml."""
    from .schema_index import CP2KSchemaIndex

    index = CP2KSchemaIndex(xml_path)
    index._ensure_loaded()

    schema_payload = build_schema_index_payload(index, release_version=release_version, xml_path=xml_path)
    docs_payload = build_docs_digest_payload(index, release_version=release_version)

    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    docs_path.write_text(json.dumps(docs_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "schema_path": str(schema_path),
        "docs_path": str(docs_path),
        "release_version": release_version,
        "section_count": len(schema_payload["sections"]),
        "docs_entry_count": len(docs_payload["entries"]),
    }


def load_docs_digest_entries(json_path: Path = DEFAULT_DOCS_DIGEST_JSON) -> list[dict[str, Any]]:
    """Load docs digest entries when a precomputed index is present."""
    if not json_path.is_file():
        return []
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        return entries if isinstance(entries, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def apply_precomputed_schema(index: CP2KSchemaIndex, payload: dict[str, Any]) -> None:
    """Hydrate a schema index from a precomputed payload."""
    from .schema_index import KeywordSpec, SectionSpec

    index._root_section_names = list(payload.get("root_sections", []))
    index._sections.clear()
    index._keywords.clear()

    for key, section_data in payload.get("sections", {}).items():
        path = _path_from_key(key)
        index._sections[path] = SectionSpec(
            name=section_data["name"],
            description=section_data.get("description"),
            subsections=list(section_data.get("subsections", [])),
            keywords=list(section_data.get("keywords", [])),
        )

    for key, keyword_map in payload.get("keywords", {}).items():
        path = _path_from_key(key)
        index._keywords[path] = {}
        for name, spec_data in keyword_map.items():
            index._keywords[path][name] = KeywordSpec(
                name=spec_data["name"],
                variable_type=spec_data.get("variable_type"),
                default_value=spec_data.get("default_value"),
                enumeration_values=list(spec_data.get("enumeration_values", [])),
                description=spec_data.get("description"),
            )

    index._loaded = True
    index._capture_file_metadata()
