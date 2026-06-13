"""Offline loader for docs_digest artifacts.

Provides deterministic, network-free access to the hover index, wiki JSONL,
and rules YAML produced by the digest pipeline.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_DOCS_DIGEST_DIR = Path(__file__).resolve().parent.parent / "docs_digest"


def _get_digest_dir() -> Path:
    env = os.environ.get("CP2K_DOCS_DIGEST_DIR")
    if env:
        return Path(env)
    return _DOCS_DIGEST_DIR


def load_hover_index() -> Optional[Dict[str, Any]]:
    """Load cp2k_hover_index.json from the digest directory.

    Returns the parsed JSON dict, or None if the file is missing or invalid.
    """
    path = _get_digest_dir() / "cp2k_hover_index.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_wiki_entries() -> List[Dict[str, Any]]:
    """Load all entries from cp2k_wiki.jsonl.

    Returns a list of parsed JSON dicts, one per line. Invalid lines are
    skipped silently.
    """
    path = _get_digest_dir() / "cp2k_wiki.jsonl"
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return entries


def load_rules() -> Optional[Dict[str, Any]]:
    """Load cp2k_rules.yaml from the digest directory.

    Returns the parsed YAML dict, or None if pyyaml is not installed or the
    file is missing/invalid.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return None
    path = _get_digest_dir() / "cp2k_rules.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def search_wiki(
    query: str,
    entry_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search wiki entries by name, description, or content.

    Parameters
    ----------
    query:
        Case-insensitive substring to match against name or description.
    entry_type:
        Optional filter: "keyword", "section", "recipe", or "rule".
    limit:
        Maximum number of results to return.

    Returns
    -------
    Matching entries sorted by relevance (exact name match first, then
    partial matches).
    """
    query_lower = query.lower()
    entries = load_wiki_entries()

    results: List[Dict[str, Any]] = []
    for entry in entries:
        if entry_type and entry.get("type") != entry_type:
            continue
        name = entry.get("name", "").lower()
        desc = entry.get("description", "").lower()
        content = entry.get("content", {}).lower() if isinstance(entry.get("content"), str) else ""

        if query_lower in name or query_lower in desc or query_lower in content:
            results.append(entry)

    def _sort_key(e: Dict[str, Any]) -> tuple:
        name = e.get("name", "").lower()
        if name == query_lower:
            return (0, name)
        if name.startswith(query_lower):
            return (1, name)
        return (2, name)

    results.sort(key=_sort_key)
    return results[:limit]


def get_provenance(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract provenance dict from a wiki entry.

    Returns the provenance sub-dict, or a minimal default if missing.
    """
    return entry.get("provenance", {
        "source": "unknown",
        "cp2k_version": "unknown",
        "crawl_date": "unknown",
    })
