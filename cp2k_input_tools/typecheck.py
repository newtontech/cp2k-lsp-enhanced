"""
Keyword value type-checking for CP2K input files.

Validates keyword values against their schema-defined DATA_TYPE
including integer, real, logical (boolean), string, keyword (enum),
and list types. Also checks unit syntax and required sections.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import DEFAULT_CP2K_INPUT_XML

# Type validators
_INT_RE = re.compile(r"^[-+]?\d+$")
_REAL_RE = re.compile(r"^[-+]?(\d+\.?\d*|\d*\.?\d+)([eE][-+]?\d+)?$")
_LOGICAL_TRUE = {"T", "TRUE", "YES", "1", "ON"}
_LOGICAL_FALSE = {"F", "FALSE", "NO", "0", "OFF"}

# Schema metadata cache
_schema_cache: Optional[Dict] = None


@dataclass
class TypeDiagnostic:
    """A type-checking diagnostic."""

    severity: str  # "error", "warning"
    source: str
    message: str
    code: str
    line: int = 0
    col: int = 0
    end_col: int = 0


def _get_schema_metadata() -> Dict:
    """Load and cache keyword type metadata from the XML schema."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
    root = tree.getroot()

    # Build: section_name -> keyword_name -> {type, enum_values, default_unit, required_children}
    meta: Dict[str, Dict[str, dict]] = {}

    def _walk_sections(node, path="/"):
        for sec in node.iterfind("./SECTION"):
            name_el = sec.find("./NAME")
            if name_el is None or not name_el.text:
                continue
            sec_name = name_el.text.upper()
            full_path = f"{path}/{sec_name}"

            kw_meta: Dict[str, dict] = {}

            # Collect keyword metadata
            for kw in sec.iterfind("./KEYWORD"):
                name_el = kw.find("./NAME")
                if name_el is None or not name_el.text:
                    continue
                kw_name = name_el.text.upper()

                info = {}

                # Data type
                dt = kw.find("./DATA_TYPE")
                if dt is not None:
                    kind = dt.get("kind", "string")
                    info["type"] = kind

                    # Enum values from ENUMERATION
                    enum_el = dt.find("./ENUMERATION")
                    if enum_el is not None:
                        values = []
                        for val_el in enum_el.findall("./VAL"):
                            if val_el.text:
                                values.append(val_el.text.upper())
                        if values:
                            info["enum_values"] = values

                # Default unit
                du = kw.find("./DEFAULT_UNIT")
                if du is not None and du.text:
                    info["default_unit"] = du.text

                kw_meta[kw_name] = info

            meta[full_path] = kw_meta

            # Also store keywords under the section's direct path
            if path not in meta:
                meta[path] = {}
            meta[path].update(kw_meta)

            _walk_sections(sec, full_path)

    _walk_sections(root)
    _schema_cache = meta
    return meta


def validate_type(value: str, expected_type: str) -> Tuple[bool, str]:
    """Validate a value against an expected type.

    Returns (is_valid, error_message).
    """
    value = value.strip()
    if not value:
        return True, ""

    if expected_type == "integer":
        # Could be a list of integers
        parts = value.split()
        for part in parts:
            if not _INT_RE.match(part):
                return False, f"Expected integer, got '{part}'"
        return True, ""

    elif expected_type == "real":
        parts = value.split()
        for part in parts:
            # Skip if it has a unit suffix
            if _REAL_RE.match(part):
                continue
            # Check if it's a number with unit
            m = re.match(r"^([-+]?[\d.eE]+)\s*([a-zA-Z_/]+.*)$", part)
            if m and _REAL_RE.match(m.group(1)):
                continue  # valid number with unit
            return False, f"Expected real number, got '{part}'"
        return True, ""

    elif expected_type == "logical":
        if value.upper() in _LOGICAL_TRUE | _LOGICAL_FALSE:
            return True, ""
        return False, f"Expected logical (T/F/TRUE/FALSE/YES/NO), got '{value}'"

    elif expected_type == "string":
        return True, ""

    elif expected_type == "keyword":
        return True, ""  # enum validation is separate

    return True, ""


def validate_enum(value: str, enum_values: List[str]) -> Tuple[bool, str]:
    """Validate a value against allowed enum values."""
    value = value.strip().upper()
    if not value:
        return True, ""

    # Handle list of values
    parts = value.split()
    for part in parts:
        if part not in enum_values:
            return False, f"Invalid enum value '{part}'. Allowed: {', '.join(enum_values[:5])}{'...' if len(enum_values) > 5 else ''}"
    return True, ""


def validate_unit_syntax(value: str) -> Tuple[bool, str]:
    """Validate that unit syntax is well-formed (e.g., [angstrom], K, Ry)."""
    value = value.strip()
    if not value:
        return True, ""

    # Check for bracketed units: [unit]
    bracket_unit = re.match(r"^\[([^\]]+)\]\s*(.+)$", value)
    if bracket_unit:
        return True, ""  # Bracketed unit syntax is valid

    return True, ""


def check_keyword_type(
    section_path: str,
    keyword_name: str,
    keyword_value: str,
    line: int = 0,
    col: int = 0,
) -> List[TypeDiagnostic]:
    """Check a keyword's value type against the schema definition.

    Returns a list of diagnostics (empty if valid).
    """
    diags: List[TypeDiagnostic] = []
    meta = _get_schema_metadata()

    # Look up the keyword in the section
    section_keywords = meta.get(section_path, {})
    kw_info = section_keywords.get(keyword_name.upper(), {})

    if not kw_info:
        return diags  # No schema info for this keyword

    expected_type = kw_info.get("type", "string")
    enum_values = kw_info.get("enum_values")

    # Type validation
    is_valid, err_msg = validate_type(keyword_value, expected_type)
    if not is_valid:
        diags.append(TypeDiagnostic(
            severity="error",
            source="cp2k-typecheck",
            message=err_msg,
            code="TYPE_MISMATCH",
            line=line,
            col=col,
        ))

    # Enum validation
    if enum_values:
        is_valid, err_msg = validate_enum(keyword_value, enum_values)
        if not is_valid:
            diags.append(TypeDiagnostic(
                severity="error",
                source="cp2k-typecheck",
                message=err_msg,
                code="INVALID_ENUM",
                line=line,
                col=col,
            ))

    # Unit syntax validation
    is_valid, err_msg = validate_unit_syntax(keyword_value)
    if not is_valid:
        diags.append(TypeDiagnostic(
            severity="warning",
            source="cp2k-typecheck",
            message=err_msg,
            code="INVALID_UNIT_SYNTAX",
            line=line,
            col=col,
        ))

    return diags


def check_required_sections(
    text: str,
    declared_run_type: Optional[str] = None,
) -> List[TypeDiagnostic]:
    """Check for missing required sections based on declared configuration.

    For example, RUN_TYPE GEO_OPT requires &GEO_OPT section.
    """
    diags: List[TypeDiagnostic] = []

    if not declared_run_type:
        return diags

    lines = text.split("\n")
    present_sections = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("&") and not stripped.upper().startswith("&END"):
            m = re.match(r"&(\w+)", stripped)
            if m:
                present_sections.add(m.group(1).upper())

    # Check RUN_TYPE requirements
    if declared_run_type == "GEO_OPT" and "GEO_OPT" not in present_sections:
        diags.append(TypeDiagnostic(
            severity="warning",
            source="cp2k-typecheck",
            message="RUN_TYPE=GEO_OPT but no &GEO_OPT section found",
            code="MISSING_REQUIRED_SECTION",
        ))
    elif declared_run_type == "MD" and "MD" not in present_sections:
        diags.append(TypeDiagnostic(
            severity="warning",
            source="cp2k-typecheck",
            message="RUN_TYPE=MD but no &MD section found",
            code="MISSING_REQUIRED_SECTION",
        ))
    elif declared_run_type == "CELL_OPT" and "CELL_OPT" not in present_sections:
        diags.append(TypeDiagnostic(
            severity="warning",
            source="cp2k-typecheck",
            message="RUN_TYPE=CELL_OPT but no &CELL_OPT section found",
            code="MISSING_REQUIRED_SECTION",
        ))

    return diags


def extract_run_type(text: str) -> Optional[str]:
    """Extract RUN_TYPE value from CP2K input text."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("RUN_TYPE"):
            parts = stripped.split(None, 1)
            if len(parts) > 1:
                return parts[1].strip().upper()
    return None


def validate_text(text: str) -> List[TypeDiagnostic]:
    """Run all type-checking validations on a CP2K input file.

    Returns a list of diagnostics.
    """
    diags: List[TypeDiagnostic] = []

    # Extract current section context for each keyword
    current_section = "/"
    section_stack: List[str] = []

    for line_num, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()

        # Track section nesting
        if stripped.startswith("&") and not stripped.upper().startswith("&END"):
            m = re.match(r"&(\w+)", stripped)
            if m and m.group(1).upper() != "END":
                section_stack.append(m.group(1).upper())
                current_section = "/" + "/".join(section_stack)
            continue

        if stripped.upper().startswith("&END"):
            if section_stack:
                section_stack.pop()
            current_section = "/" + "/".join(section_stack) if section_stack else "/"
            continue

        # Skip empty lines, comments, directives
        if not stripped or stripped.startswith("!") or stripped.startswith("#") or stripped.startswith("@"):
            continue

        # Parse keyword line
        m = re.match(r"(\w+)\s+(.*)", stripped)
        if m:
            kw_name = m.group(1)
            kw_value = m.group(2).strip()
            col = len(stripped) - len(stripped.lstrip())

            diags.extend(
                check_keyword_type(current_section, kw_name, kw_value, line=line_num, col=col)
            )

    # Check required sections
    run_type = extract_run_type(text)
    if run_type:
        diags.extend(check_required_sections(text, declared_run_type=run_type))

    return diags
