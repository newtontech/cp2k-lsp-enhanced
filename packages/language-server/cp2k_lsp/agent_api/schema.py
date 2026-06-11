"""Section and keyword schema lookup API (#37).

Provides path-based and name-based lookups so that agent tooling can
query the CP2K schema without traversing raw data structures.
"""

from typing import Any, Dict, Optional

from cp2k_lsp.data.keywords import get_keyword_info
from cp2k_lsp.data.sections import get_section_info

# ---------------------------------------------------------------------------
# Schema lookup – #37
# ---------------------------------------------------------------------------

def lookup_section_schema(name: str) -> Optional[Dict[str, Any]]:
    """Lookup the schema for a named section.

    Returns a dict with:
      - ``name``: section name
      - ``description``: human-readable description
      - ``keywords``: list of valid keyword names
      - ``subsections``: list of valid subsection names
      - ``required``: whether the section is required
      - ``repeats``: whether the section can appear multiple times

    Returns *None* if the section is unknown.
    """
    info = get_section_info(name)
    if info is None:
        return None
    return {
        "name": info.name,
        "description": info.description,
        "keywords": list(info.keywords),
        "subsections": list(info.subsections),
        "required": info.required,
        "repeats": info.repeats,
    }


def lookup_keyword_schema(name: str) -> Optional[Dict[str, Any]]:
    """Lookup the schema for a named keyword.

    Returns a dict with:
      - ``name``: keyword name
      - ``description``: human-readable description
      - ``type``: value type string (``"string"``, ``"integer"``, ``"real"``,
        ``"boolean"``, ``"enum"``, ``"file"``, ``"array"``)
      - ``default``: default value (may be *None*)
      - ``required``: whether the keyword must be specified
      - ``enum_values``: list of allowed values (only for enum type)
      - ``units``: list of supported unit strings (may be *None*)

    Returns *None* if the keyword is unknown.
    """
    info = get_keyword_info(name)
    if info is None:
        return None
    result: Dict[str, Any] = {
        "name": info.name,
        "description": info.description,
        "type": info.keyword_type.value,
        "default": info.default,
        "required": info.required,
    }
    if info.enum_values:
        result["enum_values"] = list(info.enum_values)
    if info.units:
        result["units"] = list(info.units)
    return result


def lookup_section_path(path: str) -> Optional[Dict[str, Any]]:
    """Resolve a dot-separated section path to its schema.

    Example paths:
      - ``"FORCE_EVAL"``
      - ``"FORCE_EVAL.DFT"``
      - ``"FORCE_EVAL.DFT.SCF"``

    Returns the resolved section schema (same shape as
    :func:`lookup_section_schema`) or *None* if any segment is unknown.
    """
    parts = [p.strip().upper() for p in path.split(".") if p.strip()]
    if not parts:
        return None

    for i, part in enumerate(parts):
        info = get_section_info(part)
        if info is None:
            return None
        if i < len(parts) - 1:
            # Verify next part is a valid subsection
            next_part = parts[i + 1]
            if next_part not in [s.upper() for s in info.subsections]:
                return None

    return lookup_section_schema(parts[-1])


def resolve_section_children(name: str) -> Optional[Dict[str, Any]]:
    """Resolve all children (keywords + subsections) of a section.

    Returns a dict with:
      - ``section``: the section name
      - ``keywords``: list of keyword schema dicts (same shape as
        :func:`lookup_keyword_schema`)
      - ``subsections``: list of section schema dicts (same shape as
        :func:`lookup_section_schema`)

    Returns *None* if the section is unknown.
    """
    info = get_section_info(name)
    if info is None:
        return None

    keyword_schemas = []
    for kw_name in info.keywords:
        kw_schema = lookup_keyword_schema(kw_name)
        if kw_schema is not None:
            keyword_schemas.append(kw_schema)
        else:
            keyword_schemas.append({"name": kw_name, "type": "unknown", "description": ""})

    subsection_schemas = []
    for sub_name in info.subsections:
        sub_schema = lookup_section_schema(sub_name)
        if sub_schema is not None:
            subsection_schemas.append(sub_schema)
        else:
            subsection_schemas.append({"name": sub_name, "description": ""})

    return {
        "section": info.name,
        "keywords": keyword_schemas,
        "subsections": subsection_schemas,
    }
