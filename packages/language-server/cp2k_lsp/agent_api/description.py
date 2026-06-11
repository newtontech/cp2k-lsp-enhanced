"""Domain language description API (#36).

Exposes structured, JSON-serialisable descriptions of CP2K sections and
keywords so that LLM agents and tooling can discover the CP2K input DSL
without parsing source files.
"""

from typing import Any, Dict, List, Optional

from cp2k_lsp.data.keywords import CP2K_KEYWORDS, KeywordType, get_keyword_info
from cp2k_lsp.data.sections import CP2K_SECTIONS, get_section_info

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _keyword_type_str(kt: KeywordType) -> str:
    return kt.value


def _keyword_to_dict(name: str) -> Dict[str, Any]:
    """Serialise a single keyword definition to a plain dict."""
    info = get_keyword_info(name)
    if info is None:
        return {"name": name, "description": "", "type": "unknown"}
    d: Dict[str, Any] = {
        "name": info.name,
        "description": info.description,
        "type": _keyword_type_str(info.keyword_type),
        "default": info.default,
        "required": info.required,
    }
    if info.enum_values:
        d["enum_values"] = info.enum_values
    if info.units:
        d["units"] = info.units
    return d


def _section_to_dict(name: str, *, recurse: bool = False, depth: int = 0) -> Dict[str, Any]:
    """Serialise a section definition to a plain dict.

    Parameters
    ----------
    recurse:
        If *True*, inline subsection definitions recursively.
    depth:
        Current recursion depth (used to limit recursion).
    """
    info = get_section_info(name)
    if info is None:
        return {"name": name, "description": "", "keywords": [], "subsections": []}

    d: Dict[str, Any] = {
        "name": info.name,
        "description": info.description,
        "required": info.required,
        "repeats": info.repeats,
        "keywords": [_keyword_to_dict(kw) for kw in info.keywords],
        "subsections": info.subsections[:],
    }

    if recurse and depth < 6:
        d["subsections_detail"] = [
            _section_to_dict(sub, recurse=True, depth=depth + 1)
            for sub in info.subsections
            if get_section_info(sub) is not None
        ]

    return d


# ---------------------------------------------------------------------------
# Public API – #36
# ---------------------------------------------------------------------------

def describe_section(name: str) -> Optional[Dict[str, Any]]:
    """Return a structured description of a CP2K section.

    Example::

        >>> desc = describe_section("GLOBAL")
        >>> desc["name"]
        'GLOBAL'
        >>> "PROJECT_NAME" in [k["name"] for k in desc["keywords"]]
        True
    """
    info = get_section_info(name)
    if info is None:
        return None
    return _section_to_dict(name)


def describe_keyword(name: str) -> Optional[Dict[str, Any]]:
    """Return a structured description of a CP2K keyword.

    Example::

        >>> desc = describe_keyword("RUN_TYPE")
        >>> desc["type"]
        'enum'
        >>> "ENERGY" in desc["enum_values"]
        True
    """
    info = get_keyword_info(name)
    if info is None:
        return None
    return _keyword_to_dict(name)


def describe_section_tree(name: str) -> Optional[Dict[str, Any]]:
    """Return a full recursive description of a section and its subsections.

    This is equivalent to :func:`describe_section` but with all subsections
    expanded inline (up to 6 levels deep).
    """
    info = get_section_info(name)
    if info is None:
        return None
    return _section_to_dict(name, recurse=True)


def list_all_sections() -> List[Dict[str, Any]]:
    """Return a flat list of all known CP2K section descriptors."""
    return [
        {"name": info.name, "description": info.description,
         "required": info.required, "repeats": info.repeats}
        for info in CP2K_SECTIONS.values()
    ]


def list_all_keywords() -> List[Dict[str, Any]]:
    """Return a flat list of all known CP2K keyword descriptors."""
    return [_keyword_to_dict(info.name) for info in CP2K_KEYWORDS.values()]
