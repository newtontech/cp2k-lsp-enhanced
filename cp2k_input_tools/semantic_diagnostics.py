"""Schema/type/path semantic diagnostics for CP2K inputs (issues #116).

This module produces stable, rule-tagged diagnostics that aggregate the
existing lint, typecheck, version-policy and semantic checks behind a
single entry point.  Each diagnostic carries:

* a canonical ``rule_id`` (e.g. ``cp2k.schema.unknown_enum``);
* a stable legacy ``code`` for backward compatibility;
* a ``severity`` following the policy documented in the issue:
  official schema violation -> ``error``, deprecated/risky -> ``warning``,
  community/style -> ``information``;
* a ``category`` drawn from the Diagnostic Engine v1 vocabulary;
* a ``provenance_id`` describing where the rule comes from; and
* a ``suggested_fix`` with a concrete next action when possible.

The module is deliberately additive: existing public functions in
``cp2k_input_tools.linter`` / ``typecheck`` / ``validator`` are reused,
and only the missing pieces (missing-required-keyword, missing GLOBAL,
explicit path-aware type checks) are implemented locally.

Example::

    from cp2k_input_tools.semantic_diagnostics import collect_semantic_diagnostics

    diagnostics = collect_semantic_diagnostics(text)
    for diag in diagnostics:
        print(diag.rule_id, diag.severity, diag.message)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import DEFAULT_CP2K_INPUT_XML
from .linter import (
    CANONICAL_RULE_LOOSE_SCF_EPS,
    RULE_FEW_SCF,
    RULE_GEO_OPT_MAX_ITER_LOW,
    RULE_LOOSE_SCF_EPS,
    RULE_LOW_CUTOFF,
    RULE_LOW_REL_CUTOFF,
    RULE_LONG_TIMESTEP,
    RULE_LOW_TEMP,
    RULE_MAX_SCF_TOO_LOW,
    RULE_MISSING_BASIS,
    RULE_MISSING_END,
    RULE_MISSING_POTENTIAL,
    RULE_SHORT_TIMESTEP,
    lint,
)
from .linter import RULE_DUPLICATE_KEYWORD as LINT_RULE_DUPLICATE_KEYWORD
from .linter import RULE_DUPLICATE_SECTION as LINT_RULE_DUPLICATE_SECTION
from .linter import RULE_INVALID_NESTING as LINT_RULE_INVALID_NESTING
from .linter import RULE_MISSPELLED_KEYWORD as LINT_RULE_MISSPELLED_KEYWORD
from .linter import RULE_UNKNOWN_ENUM as LINT_RULE_UNKNOWN_ENUM
from .rich_diagnostics import DIAGNOSTIC_ENGINE_VERSION, infer_category
from .schema_index import CP2KSchemaIndex, KeywordSpec, get_schema_index
from .validator import Diagnostic as LintDiagnostic
from .version_policy import lint_version_policy_from_env

# ---------------------------------------------------------------------------
# Canonical rule identifiers (single source of truth for #116)
# ---------------------------------------------------------------------------

RULE_UNKNOWN_SECTION = "cp2k.schema.unknown_section"
RULE_UNKNOWN_KEYWORD = "cp2k.schema.unknown_keyword"
RULE_UNKNOWN_ENUM = "cp2k.schema.unknown_enum"
RULE_INVALID_NESTING = "cp2k.schema.invalid_nesting"
RULE_DUPLICATE_KEYWORD = "cp2k.schema.duplicate_keyword"
RULE_DUPLICATE_SECTION = "cp2k.schema.duplicate_section"
RULE_MISSPELLED_KEYWORD = "cp2k.schema.misspelled_keyword"
RULE_MISSING_END = "cp2k.syntax.missing_end"

RULE_TYPE_INTEGER = "cp2k.type.integer"
RULE_TYPE_REAL = "cp2k.type.real"
RULE_TYPE_LOGICAL = "cp2k.type.logical"
RULE_TYPE_STRING = "cp2k.type.string"
RULE_TYPE_LIST = "cp2k.type.list"

RULE_MISSING_REQUIRED_SECTION = "cp2k.schema.missing_required_section"
RULE_MISSING_REQUIRED_KEYWORD = "cp2k.schema.missing_required_keyword"
RULE_MISSING_GLOBAL = "cp2k.schema.missing_global"

RULE_VERSION_REMOVED = "cp2k.version.removed_keyword"
RULE_VERSION_DEPRECATED = "cp2k.version.deprecated_keyword"
RULE_VERSION_UNKNOWN = "cp2k.version.unknown_keyword"

RULE_RISKY_CUTOFF = "cp2k.dft.cutoff_low"
RULE_RISKY_REL_CUTOFF = "cp2k.dft.rel_cutoff_low"
RULE_RISKY_MAX_SCF = "cp2k.scf.max_scf_low"
RULE_RISKY_EPS_SCF = "cp2k.scf.eps_scf_loose"
RULE_RISKY_FEW_SCF = "cp2k.scf.few_iterations"
RULE_RISKY_GEO_OPT_MAX_ITER = "cp2k.geo_opt.max_iter_low"
RULE_STYLE_TIMESTEP_SHORT = "cp2k.md.timestep_short"
RULE_STYLE_TIMESTEP_LONG = "cp2k.md.timestep_long"
RULE_STYLE_LOW_ELECTRONIC_TEMP = "cp2k.smear.low_electronic_temp"

# Map of legacy lint codes -> canonical rule id + provenance + suggested_fix
# This keeps the canonical behaviour of ``lint()`` intact while attaching
# issue-#116 metadata on top.
_LEGACY_CODE_POLICY: Dict[str, Dict[str, str]] = {
    LINT_RULE_INVALID_NESTING: {
        "rule_id": RULE_INVALID_NESTING,
        "provenance_id": "cp2k_input.xml:section/SECTION",
        "suggested_fix": "Move the section under its valid parent or rename it.",
    },
    LINT_RULE_DUPLICATE_KEYWORD: {
        "rule_id": RULE_DUPLICATE_KEYWORD,
        "provenance_id": "cp2k_input.xml:keyword[@repeats]",
        "suggested_fix": "Remove the duplicate keyword or pick the intended value.",
    },
    LINT_RULE_DUPLICATE_SECTION: {
        "rule_id": RULE_DUPLICATE_SECTION,
        "provenance_id": "cp2k_input.xml:section[@repeats]",
        "suggested_fix": "Remove the duplicate section or set the parent repeats.",
    },
    LINT_RULE_MISSPELLED_KEYWORD: {
        "rule_id": RULE_MISSPELLED_KEYWORD,
        "provenance_id": "cp2k_input.xml:section/KEYWORD/NAME",
        "suggested_fix": "Rename the keyword to the suggested schema spelling.",
    },
    LINT_RULE_UNKNOWN_ENUM: {
        "rule_id": RULE_UNKNOWN_ENUM,
        "provenance_id": "cp2k_input.xml:KEYWORD/DATA_TYPE/ENUMERATION",
        "suggested_fix": "Use one of the allowed enum values listed in the message.",
    },
    RULE_MISSING_BASIS: {
        "rule_id": RULE_MISSING_BASIS,
        "provenance_id": "cp2k_input.xml:FORCE_EVAL/DFT/BASIS_SET_FILE_NAME",
        "suggested_fix": "Add BASIS_SET_FILE_NAME pointing to a readable basis set file.",
    },
    RULE_MISSING_POTENTIAL: {
        "rule_id": RULE_MISSING_POTENTIAL,
        "provenance_id": "cp2k_input.xml:FORCE_EVAL/DFT/POTENTIAL_FILE_NAME",
        "suggested_fix": "Add POTENTIAL_FILE_NAME pointing to a readable potential file.",
    },
    RULE_MISSING_END: {
        "rule_id": RULE_MISSING_END,
        "provenance_id": "cp2k_input.xml:SECTION",
        "suggested_fix": "Add the matching &END <name> line for the section.",
    },
    RULE_LOW_CUTOFF: {
        "rule_id": RULE_RISKY_CUTOFF,
        "provenance_id": "cp2k wiki:dft-convergence",
        "suggested_fix": "Raise CUTOFF to at least 280 Ry for production GPW runs.",
    },
    RULE_LOW_REL_CUTOFF: {
        "rule_id": RULE_RISKY_REL_CUTOFF,
        "provenance_id": "cp2k wiki:dft-convergence",
        "suggested_fix": "Raise REL_CUTOFF (typical range 40-60 Ry).",
    },
    RULE_FEW_SCF: {
        "rule_id": RULE_RISKY_FEW_SCF,
        "provenance_id": "cp2k wiki:scf-convergence",
        "suggested_fix": "Increase MAX_SCF or improve the SCF guess.",
    },
    RULE_LOOSE_SCF_EPS: {
        "rule_id": RULE_RISKY_EPS_SCF,
        "provenance_id": "cp2k wiki:scf-convergence",
        "suggested_fix": "Tighten EPS_SCF to <= 1.0e-6 for production runs.",
    },
    CANONICAL_RULE_LOOSE_SCF_EPS: {
        "rule_id": RULE_RISKY_EPS_SCF,
        "provenance_id": "cp2k wiki:scf-convergence",
        "suggested_fix": "Tighten EPS_SCF to <= 1.0e-6 for production runs.",
    },
    RULE_MAX_SCF_TOO_LOW: {
        "rule_id": RULE_RISKY_MAX_SCF,
        "provenance_id": "cp2k wiki:scf-convergence",
        "suggested_fix": "Increase MAX_SCF (50-100 for OT, more for diagonalisation).",
    },
    RULE_GEO_OPT_MAX_ITER_LOW: {
        "rule_id": RULE_RISKY_GEO_OPT_MAX_ITER,
        "provenance_id": "cp2k manual:MOTION/GEO_OPT/MAX_ITER",
        "suggested_fix": "Increase MAX_ITER under &GEO_OPT.",
    },
    RULE_SHORT_TIMESTEP: {
        "rule_id": RULE_STYLE_TIMESTEP_SHORT,
        "provenance_id": "cp2k manual:MOTION/MD/TIMESTEP",
        "suggested_fix": "Pick a TIMESTEP close to 0.5 fs for atomistic MD.",
    },
    RULE_LONG_TIMESTEP: {
        "rule_id": RULE_STYLE_TIMESTEP_LONG,
        "provenance_id": "cp2k manual:MOTION/MD/TIMESTEP",
        "suggested_fix": "Pick a TIMESTEP close to 0.5 fs for atomistic MD.",
    },
    RULE_LOW_TEMP: {
        "rule_id": RULE_STYLE_LOW_ELECTRONIC_TEMP,
        "provenance_id": "cp2k wiki:smearing",
        "suggested_fix": "Review ELECTRON_TEMPERATURE if smearing is too high.",
    },
}

# Version-policy code -> canonical rule id.
_VERSION_POLICY_RULES = {
    "cp2k.version.removed_keyword": RULE_VERSION_REMOVED,
    "cp2k.version.deprecated_keyword": RULE_VERSION_DEPRECATED,
    "cp2k.version.unknown_keyword": RULE_VERSION_UNKNOWN,
}

# Sections that CP2K expects at the document root.  ``GLOBAL`` is the only
# one we *warn* about when missing because the rest are use-case specific.
ROOT_SECTION_NAMES = (
    "GLOBAL",
    "FORCE_EVAL",
    "MOTION",
    "VIBRATIONAL_ANALYSIS",
    "OPTIMIZE_INPUT",
    "EXT_RESTART",
)

# Required KIND keywords: when a &KIND block is present we expect at least an
# ELEMENT label so CP2K can map the kind to a nuclear charge.
KIND_REQUIRED_KEYWORDS = ("ELEMENT",)


@dataclass
class SemanticDiagnostic:
    """Canonical semantic diagnostic with provenance + suggested fix."""

    rule_id: str
    severity: str
    message: str
    code: str
    source: str
    category: str
    line: int
    column: int
    end_line: int
    end_column: int
    provenance_id: str
    suggested_fix: Optional[str] = None
    section_path: Optional[str] = None
    related_keyword: Optional[str] = None
    related_section: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to the rich-diagnostics dict contract."""
        payload: Dict[str, Any] = {
            "diagnostic_engine": DIAGNOSTIC_ENGINE_VERSION,
            "rule_id": self.rule_id,
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "source": self.source,
            "message": self.message,
            "range": {
                "start": {"line": self.line, "character": self.column},
                "end": {"line": self.end_line, "character": self.end_column},
            },
            "provenance_id": self.provenance_id,
            "suggested_fix": self.suggested_fix,
        }
        if self.section_path:
            payload["section_path"] = self.section_path
        if self.related_keyword:
            payload["related_keyword"] = self.related_keyword
        if self.related_section:
            payload["related_section"] = self.related_section
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SECTION_OPEN_RE = re.compile(r"^\s*&(?P<name>[A-Za-z][A-Za-z0-9_\-]*)(?:\s+(?P<param>[^\n]*))?$")
_SECTION_END_RE = re.compile(r"^\s*&END(?:\s+(?P<name>[A-Za-z][A-Za-z0-9_\-]*))?\s*$", re.IGNORECASE)
_KEYWORD_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z][A-Za-z0-9_\-]*)\b(?P<rest>.*)$")
_INT_RE = re.compile(r"^[-+]?\d+$")
_REAL_RE = re.compile(r"^[-+]?(\d+\.?\d*|\d*\.?\d+)([eE][-+]?\d+)?$")
_LOGICAL_TRUE = {"T", "TRUE", ".TRUE.", "YES", "1", "ON"}
_LOGICAL_FALSE = {"F", "FALSE", ".FALSE.", "NO", "0", "OFF"}
_FREE_FORM_SECTIONS = {
    "COORD",
    "COLLECTIVE",
    "CONSTRAINT_INFO",
    "FORCE",
    "MULTIPLE_UNIT_CELL",
    "SCALED",
    "SHELL_COORD",
    "VELOCITY",
}


def _normalize_severity(severity: str, code: str, rule_id: str) -> str:
    """Apply the issue-#116 severity policy."""
    sev = (severity or "error").lower()
    if sev in {"error", "warning", "information", "hint"}:
        return sev
    return "error"


def _is_data_record_section(stack: Sequence[str]) -> bool:
    return any(name in _FREE_FORM_SECTIONS for name in stack)


def _section_path_string(stack: Sequence[str]) -> str:
    return "/".join(stack) if stack else "/"


def _build_index() -> CP2KSchemaIndex:
    """Return the lazily-built schema index (XML-backed)."""
    return get_schema_index()


def _all_keyword_lookup(index: CP2KSchemaIndex) -> Dict[str, List[Tuple[str, ...]]]:
    """Return a map of upper keyword name -> list of section paths."""
    index._ensure_loaded()
    result: Dict[str, List[Tuple[str, ...]]] = {}
    for section_path, keywords in index._keywords.items():
        for kw_name in keywords:
            result.setdefault(kw_name, []).append(section_path)
    return result


def _all_section_names(index: CP2KSchemaIndex) -> set:
    """Return every section name known to the schema (across all paths)."""
    index._ensure_loaded()
    names: set = set()
    for path in index._sections.keys():
        for part in path:
            names.add(part)
    return names


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_semantic_diagnostics(
    text: str,
    *,
    version_policy_path: Optional[str] = None,
) -> List[SemanticDiagnostic]:
    """Collect schema/type/path semantic diagnostics for a CP2K input.

    Combines:

    * existing ``lint()`` checks (unknown enum, duplicate, nesting, missing
      files, low cutoffs and other risky patterns);
    * version-policy lint (deprecated / removed / unknown keywords) when the
      ``CP2K_VERSION_POLICY`` environment variable is set, or via the
      ``version_policy_path`` argument;
    * path-aware keyword/section presence checks against the schema index;
    * type checks for integer / real / logical values; and
    * the new "missing required section/keyword" rules.

    The function is safe-by-construction: any internal exception is swallowed
    so a single broken check never disables the rest of the diagnostics.
    """
    diagnostics: List[SemanticDiagnostic] = []

    # 1. Re-use the lint pipeline.  Drop the lint layer's enum and
    #    nesting checks because the path-aware walk below already produces
    #    schema-indexed versions with the section context attached.
    try:
        lint_diags = [
            d
            for d in lint(text)
            if d.code not in (LINT_RULE_UNKNOWN_ENUM, LINT_RULE_INVALID_NESTING)
        ]
        diagnostics.extend(_from_legacy_lint(lint_diags))
    except Exception:  # pragma: no cover - defensive
        pass

    # 2. Version policy if requested or env-driven.
    try:
        if version_policy_path:
            from .version_policy import lint_version_policy, load_version_policy

            diagnostics.extend(
                _from_version_policy(lint_version_policy(text, load_version_policy(version_policy_path)))
            )
        else:
            diagnostics.extend(_from_version_policy(lint_version_policy_from_env(text)))
    except Exception:  # pragma: no cover - defensive
        pass

    # 3. Path-aware schema checks (unknown keyword/section, type, required).
    try:
        diagnostics.extend(_path_aware_checks(text))
    except Exception:  # pragma: no cover - defensive
        pass

    # Sort deterministically for stable golden comparisons.
    diagnostics.sort(
        key=lambda d: (
            d.line,
            d.column,
            d.rule_id,
            d.message,
        )
    )
    return diagnostics


def _from_legacy_lint(diagnostics: Sequence[LintDiagnostic]) -> List[SemanticDiagnostic]:
    """Convert legacy ``lint()`` diagnostics into the canonical envelope."""
    result: List[SemanticDiagnostic] = []
    for diag in diagnostics:
        code = diag.code or "cp2k.lint"
        policy = _LEGACY_CODE_POLICY.get(code, {})
        rule_id = policy.get("rule_id", code)
        provenance = policy.get("provenance_id", "cp2k_input.xml")
        suggested = diag.suggested_fix or policy.get("suggested_fix")
        line = diag.line if diag.line is not None else 0
        column = diag.column if diag.column is not None else 0
        end_line = diag.end_line if diag.end_line is not None else line
        end_col = diag.end_column if diag.end_column is not None else max(column + 1, 1)
        result.append(
            SemanticDiagnostic(
                rule_id=rule_id,
                severity=_normalize_severity(diag.severity, code, rule_id),
                message=diag.message,
                code=code,
                source=diag.source or "cp2k-schema",
                category=infer_category(code, diag.message, diag.source or ""),
                line=int(line),
                column=int(column),
                end_line=int(end_line),
                end_column=int(end_col),
                provenance_id=provenance,
                suggested_fix=suggested,
            )
        )
    return result


def _from_version_policy(diagnostics: Sequence[LintDiagnostic]) -> List[SemanticDiagnostic]:
    result: List[SemanticDiagnostic] = []
    for diag in diagnostics:
        rule_id = _VERSION_POLICY_RULES.get(diag.code, RULE_VERSION_UNKNOWN)
        line = diag.line if diag.line is not None else 0
        column = diag.column if diag.column is not None else 0
        result.append(
            SemanticDiagnostic(
                rule_id=rule_id,
                severity=_normalize_severity(diag.severity, diag.code or rule_id, rule_id),
                message=diag.message,
                code=diag.code or rule_id,
                source=diag.source or "cp2k-version-policy",
                category=infer_category(diag.code, diag.message, diag.source or ""),
                line=int(line),
                column=int(column),
                end_line=int(line),
                end_column=max(int(column) + 1, 1),
                provenance_id="cp2k release-diff version policy",
                suggested_fix=diag.suggested_fix,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Path-aware checks
# ---------------------------------------------------------------------------


def _path_aware_checks(text: str) -> List[SemanticDiagnostic]:
    """Walk the section stack and apply path-aware schema checks."""
    index = _build_index()
    keyword_paths = _all_keyword_lookup(index)
    valid_sections = _all_section_names(index)

    diagnostics: List[SemanticDiagnostic] = []

    stack: List[str] = []
    # Track the line where each section was opened, for nesting diagnostics.
    section_open_lines: Dict[int, Tuple[str, ...]] = {}
    # Track keyword occurrences within the current leaf section so we can skip
    # type checks for repeated keywords (the lint layer already flags those).
    seen_keywords_in_section: Dict[Tuple[str, ...], set] = {}
    # Per-KIND block tracking for missing-required-keyword checks.
    section_kind_blocks: List[Dict[str, Any]] = []

    lines = text.split("\n")
    has_global = False
    has_any_root = False

    for line_idx, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith(("!", "#", "@")):
            continue

        end_match = _SECTION_END_RE.match(raw)
        if end_match:
            end_name = (end_match.group("name") or "").upper()
            # Close any active KIND block when its &END is seen.
            if stack and stack[-1] == "KIND":
                if section_kind_blocks and not section_kind_blocks[-1]["_closed"]:
                    section_kind_blocks[-1]["_closed"] = True
            if end_name and end_name in stack:
                while stack and stack[-1] != end_name:
                    stack.pop()
                if stack:
                    stack.pop()
            elif stack:
                stack.pop()
            continue

        section_match = _SECTION_OPEN_RE.match(raw)
        if section_match:
            name = section_match.group("name").upper()
            has_any_root = has_any_root or not stack
            if not stack:
                has_global = has_global or name == "GLOBAL"
                # Root section: must exist in schema index.
                if name not in valid_sections and name not in ROOT_SECTION_NAMES:
                    diagnostics.append(_make_unknown_section(name, line_idx, raw))
            else:
                parent_path = tuple(stack)
                parent_spec = index.get_section(parent_path)
                # Unknown nested section
                if parent_spec is None or name not in parent_spec.subsections:
                    if name not in valid_sections:
                        diagnostics.append(
                            _make_unknown_section(name, line_idx, raw, parent_path="/".join(stack))
                        )
                    else:
                        diagnostics.append(
                            _make_invalid_nesting(name, line_idx, raw, parent_path="/".join(stack))
                        )
            stack.append(name)
            section_open_lines[line_idx] = tuple(stack)
            # Open a new KIND block immediately so missing-keyword detection
            # fires even when the block has no inner keywords at all.
            if name == "KIND":
                section_kind_blocks.append(
                    {"_closed": False, "_line": line_idx, "ELEMENT": False}
                )
            seen_keywords_in_section.setdefault(tuple(stack), set())
            continue

        # Keyword line within a section.
        kw_match = _KEYWORD_RE.match(raw)
        if not kw_match:
            continue
        if _is_data_record_section(stack):
            continue

        kw_name = kw_match.group("key").upper()
        rest = (kw_match.group("rest") or "").strip()
        # Strip a trailing inline comment.
        comment_pos = rest.find("!")
        if comment_pos >= 0:
            rest = rest[:comment_pos].strip()
        column = len(raw) - len(raw.lstrip()) + len(kw_name) + 1

        section_path = tuple(stack)
        section_path_str = _section_path_string(stack)
        seen = seen_keywords_in_section.setdefault(section_path, set())
        is_duplicate = kw_name in seen
        seen.add(kw_name)

        # Per-section lookup of keyword spec.
        kw_spec = index.get_keyword(section_path, kw_name)
        if kw_spec is None:
            # Unknown keyword in current section. If the keyword exists in
            # *some* other section we still flag it (path mismatch).
            diagnostics.append(
                _make_unknown_keyword(
                    kw_name,
                    line_idx,
                    raw,
                    section_path=section_path_str,
                    elsewhere=bool(keyword_paths.get(kw_name)),
                )
            )
            continue

        # Required-keyword bookkeeping for KIND sections.
        if stack and stack[-1] == "KIND":
            if not section_kind_blocks or section_kind_blocks[-1]["_closed"]:
                section_kind_blocks.append(
                    {"_closed": False, "_line": line_idx, "ELEMENT": False}
                )
            section_kind_blocks[-1][kw_name] = True

        # Skip type / enum validation on duplicate occurrences — the lint
        # layer already flags the duplicate and the second value would be
        # reported against the wrong context.
        if is_duplicate:
            continue

        # Type / enum validation using the schema spec.
        diagnostics.extend(
            _type_check(kw_name, rest, kw_spec, line_idx, raw, column, section_path_str)
        )

    # After walking the document, emit the structural diagnostics.
    if has_any_root and not has_global:
        diagnostics.append(
            SemanticDiagnostic(
                rule_id=RULE_MISSING_GLOBAL,
                severity="warning",
                message="No &GLOBAL section found; CP2K requires one for project naming and run type.",
                code=RULE_MISSING_GLOBAL,
                source="cp2k-schema",
                category=infer_category(RULE_MISSING_GLOBAL, "GLOBAL required", "cp2k-schema"),
                line=0,
                column=0,
                end_line=0,
                end_column=1,
                provenance_id="cp2k_input.xml:CP2K_INPUT/GLOBAL",
                suggested_fix="Add an &GLOBAL ... &END GLOBAL block with at least PROJECT_NAME.",
                related_section="GLOBAL",
            )
        )

    # KIND required keywords (ELEMENT/BASIS_SET).
    for block in section_kind_blocks:
        if not block.get("ELEMENT"):
            diagnostics.append(
                SemanticDiagnostic(
                    rule_id=RULE_MISSING_REQUIRED_KEYWORD,
                    severity="warning",
                    message="&KIND block is missing the ELEMENT keyword.",
                    code=RULE_MISSING_REQUIRED_KEYWORD,
                    source="cp2k-schema",
                    category=infer_category(RULE_MISSING_REQUIRED_KEYWORD, "missing KIND/ELEMENT", "cp2k-schema"),
                    line=int(block.get("_line", 0)),
                    column=0,
                    end_line=int(block.get("_line", 0)),
                    end_column=1,
                    provenance_id="cp2k_input.xml:FORCE_EVAL/SUBSYS/KIND/ELEMENT",
                    suggested_fix="Add `ELEMENT <symbol>` inside &KIND.",
                    related_section="KIND",
                    related_keyword="ELEMENT",
                )
            )

    return diagnostics


def _make_unknown_section(
    name: str, line_idx: int, raw: str, *, parent_path: Optional[str] = None
) -> SemanticDiagnostic:
    if parent_path:
        message = f"Section '&{name}' is not defined in the CP2K schema under &{parent_path}."
    else:
        message = f"Section '&{name}' is not a recognised CP2K root section."
    return SemanticDiagnostic(
        rule_id=RULE_UNKNOWN_SECTION,
        severity="error",
        message=message,
        code=RULE_UNKNOWN_SECTION,
        source="cp2k-schema",
        category=infer_category(RULE_UNKNOWN_SECTION, message, "cp2k-schema"),
        line=line_idx,
        column=0,
        end_line=line_idx,
        end_column=max(len(raw.strip()), 1),
        provenance_id="cp2k_input.xml:CP2K_INPUT/SECTIONS",
        suggested_fix=f"Remove &{name} or rename it to a valid CP2K section.",
        related_section=name,
        section_path=parent_path,
    )


def _make_invalid_nesting(
    name: str, line_idx: int, raw: str, *, parent_path: str
) -> SemanticDiagnostic:
    message = f"Section '&{name}' is not valid under '&{parent_path}' per the schema."
    return SemanticDiagnostic(
        rule_id=RULE_INVALID_NESTING,
        severity="error",
        message=message,
        code=RULE_INVALID_NESTING,
        source="cp2k-schema",
        category=infer_category(RULE_INVALID_NESTING, message, "cp2k-schema"),
        line=line_idx,
        column=0,
        end_line=line_idx,
        end_column=max(len(raw.strip()), 1),
        provenance_id="cp2k_input.xml:section[@path]",
        suggested_fix=f"Move &{name} under a valid parent section.",
        related_section=name,
        section_path=parent_path,
    )


def _make_unknown_keyword(
    name: str, line_idx: int, raw: str, *, section_path: str, elsewhere: bool
) -> SemanticDiagnostic:
    if elsewhere:
        message = (
            f"Keyword '{name}' is not valid in section '&{section_path}' "
            f"(it is valid elsewhere in the schema)."
        )
    else:
        message = f"Keyword '{name}' is not defined in section '&{section_path}'."
    return SemanticDiagnostic(
        rule_id=RULE_UNKNOWN_KEYWORD,
        severity="error",
        message=message,
        code=RULE_UNKNOWN_KEYWORD,
        source="cp2k-schema",
        category=infer_category(RULE_UNKNOWN_KEYWORD, message, "cp2k-schema"),
        line=line_idx,
        column=max(len(raw) - len(raw.lstrip()), 0),
        end_line=line_idx,
        end_column=max(len(raw.rstrip()), 1),
        provenance_id="cp2k_input.xml:SECTION/KEYWORD",
        suggested_fix=f"Remove or rename '{name}' to a valid keyword for &{section_path}.",
        related_keyword=name,
        section_path=section_path,
    )


def _type_check(
    name: str,
    raw_value: str,
    spec: KeywordSpec,
    line_idx: int,
    raw_line: str,
    column: int,
    section_path: str,
) -> List[SemanticDiagnostic]:
    diagnostics: List[SemanticDiagnostic] = []
    value = raw_value.strip()
    if not value or spec.variable_type is None:
        return diagnostics

    var_type = spec.variable_type.strip().lower()

    if spec.enumeration_values:
        # First whitespace-separated token must be in the enum.
        token = value.split()[0].upper()
        allowed = [v.upper() for v in spec.enumeration_values]
        if token not in allowed:
            diagnostics.append(
                _make_type_diag(
                    rule_id=RULE_UNKNOWN_ENUM,
                    severity="error",
                    message=(
                        f"Value '{token}' is not allowed for keyword '{name}'. "
                        f"Allowed values: {', '.join(spec.enumeration_values[:8])}"
                        f"{'...' if len(spec.enumeration_values) > 8 else ''}."
                    ),
                    line_idx=line_idx,
                    column=column,
                    raw_line=raw_line,
                    value=token,
                    keyword=name,
                    section_path=section_path,
                    provenance_id=f"cp2k_input.xml:KEYWORD/{name}/DATA_TYPE/ENUMERATION",
                    suggested_fix=f"Use one of the listed enum values for {name}.",
                )
            )
            return diagnostics

    if var_type == "integer":
        for part in value.split():
            if not _INT_RE.match(part):
                diagnostics.append(
                    _make_type_diag(
                        rule_id=RULE_TYPE_INTEGER,
                        severity="error",
                        message=f"Keyword '{name}' expects an integer value; got '{part}'.",
                        line_idx=line_idx,
                        column=column,
                        raw_line=raw_line,
                        value=part,
                        keyword=name,
                        section_path=section_path,
                        provenance_id=f"cp2k_input.xml:KEYWORD/{name}/DATA_TYPE",
                        suggested_fix=f"Provide an integer value for {name}.",
                    )
                )
                break
    elif var_type == "real":
        for part in value.split():
            if _REAL_RE.match(part):
                continue
            diagnostics.append(
                _make_type_diag(
                    rule_id=RULE_TYPE_REAL,
                    severity="error",
                    message=f"Keyword '{name}' expects a real value; got '{part}'.",
                    line_idx=line_idx,
                    column=column,
                    raw_line=raw_line,
                    value=part,
                    keyword=name,
                    section_path=section_path,
                    provenance_id=f"cp2k_input.xml:KEYWORD/{name}/DATA_TYPE",
                    suggested_fix=f"Provide a real (floating-point) value for {name}.",
                )
            )
            break
    elif var_type == "logical":
        token = value.split()[0].upper() if value.split() else ""
        if token not in _LOGICAL_TRUE | _LOGICAL_FALSE:
            diagnostics.append(
                _make_type_diag(
                    rule_id=RULE_TYPE_LOGICAL,
                    severity="error",
                    message=(
                        f"Keyword '{name}' expects a logical value "
                        f"(T/F/TRUE/FALSE/YES/NO); got '{value}'."
                    ),
                    line_idx=line_idx,
                    column=column,
                    raw_line=raw_line,
                    value=value,
                    keyword=name,
                    section_path=section_path,
                    provenance_id=f"cp2k_input.xml:KEYWORD/{name}/DATA_TYPE",
                    suggested_fix=f"Use a logical literal (T or F) for {name}.",
                )
            )
    # string / keyword / etc. accept anything non-empty.

    return diagnostics


def _make_type_diag(
    *,
    rule_id: str,
    severity: str,
    message: str,
    line_idx: int,
    column: int,
    raw_line: str,
    value: str,
    keyword: str,
    section_path: str,
    provenance_id: str,
    suggested_fix: Optional[str],
) -> SemanticDiagnostic:
    return SemanticDiagnostic(
        rule_id=rule_id,
        severity=severity,
        message=message,
        code=rule_id,
        source="cp2k-schema",
        category=infer_category(rule_id, message, "cp2k-schema"),
        line=line_idx,
        column=column,
        end_line=line_idx,
        end_column=max(len(raw_line.rstrip()), column + 1),
        provenance_id=provenance_id,
        suggested_fix=suggested_fix,
        related_keyword=keyword,
        section_path=section_path,
        extra={"actual": value},
    )


__all__ = [
    "SemanticDiagnostic",
    "collect_semantic_diagnostics",
    "RULE_UNKNOWN_SECTION",
    "RULE_UNKNOWN_KEYWORD",
    "RULE_UNKNOWN_ENUM",
    "RULE_INVALID_NESTING",
    "RULE_DUPLICATE_KEYWORD",
    "RULE_DUPLICATE_SECTION",
    "RULE_MISSPELLED_KEYWORD",
    "RULE_MISSING_END",
    "RULE_TYPE_INTEGER",
    "RULE_TYPE_REAL",
    "RULE_TYPE_LOGICAL",
    "RULE_TYPE_STRING",
    "RULE_TYPE_LIST",
    "RULE_MISSING_REQUIRED_SECTION",
    "RULE_MISSING_REQUIRED_KEYWORD",
    "RULE_MISSING_GLOBAL",
    "RULE_VERSION_REMOVED",
    "RULE_VERSION_DEPRECATED",
    "RULE_VERSION_UNKNOWN",
    "ROOT_SECTION_NAMES",
    "KIND_REQUIRED_KEYWORDS",
]
