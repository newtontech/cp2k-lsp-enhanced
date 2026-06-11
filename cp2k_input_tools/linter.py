"""
CP2K schema-aware static lint rules for LSP diagnostics.

Provides lint checks that go beyond syntax and semantic validation:
- Keyword misspell detection (fuzzy match against schema)
- Invalid section nesting checks
- Duplicate keyword/section detection
- Configuration smell warnings (low cutoff, few SCF iterations, etc.)
"""

import difflib
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Set, Tuple

from . import DEFAULT_CP2K_INPUT_XML
from .validator import Diagnostic

# Lint rule codes
RULE_MISSPELLED_KEYWORD = "lint/misspelled-keyword"
RULE_INVALID_NESTING = "lint/invalid-nesting"
RULE_DUPLICATE_KEYWORD = "lint/duplicate-keyword"
RULE_DUPLICATE_SECTION = "lint/duplicate-section"
RULE_LOW_CUTOFF = "lint/low-cutoff"
RULE_LOW_REL_CUTOFF = "lint/low-rel-cutoff"
RULE_FEW_SCF = "lint/few-scf-iterations"
RULE_LOOSE_SCF_EPS = "lint/loose-scf-eps"
RULE_SHORT_TIMESTEP = "lint/short-timestep"
RULE_LONG_TIMESTEP = "lint/long-timestep"
RULE_LOW_TEMP = "lint/low-electronic-temp"
RULE_MAX_SCF_TOO_LOW = "lint/max-scf-too-low"
RULE_GEO_OPT_MAX_ITER_LOW = "lint/geo-opt-max-iter-low"

# Short forms accepted by existing fixtures/parser behavior but not listed as
# explicit XML aliases in the bundled schema.
ACCEPTED_KEYWORD_ALIASES = {
    "COORD_FILE",
}

# Sections whose child records are data rows rather than ordinary keywords.
DATA_RECORD_SECTIONS = {
    "COORD",
}

# Common CP2K sections that are expected to appear multiple times under one parent.
REPEATABLE_SECTIONS = {
    "FORCE_EVAL",
    "KIND",
    "PRINT",
}

# Section parent-child validity map (common sections)
VALID_SECTION_PARENTS = {
    "GLOBAL": {"/"},
    "FORCE_EVAL": {"/"},
    "MOTION": {"/"},
    "DFT": {"FORCE_EVAL"},
    "SUBSYS": {"FORCE_EVAL"},
    "QS": {"DFT"},
    "MGRID": {"DFT"},
    "SCF": {"DFT"},
    "XC": {"DFT"},
    "XC_FUNCTIONAL": {"XC"},
    "POISSON": {"DFT"},
    "KPOINTS": {"DFT"},
    "PRINT": {"DFT", "MOTION", "FORCE_EVAL", "GLOBAL", "XC"},
    "CELL": {"SUBSYS"},
    "COORD": {"SUBSYS"},
    "TOPOLOGY": {"SUBSYS"},
    "KIND": {"SUBSYS"},
    "GEO_OPT": {"MOTION"},
    "MD": {"MOTION"},
    "CELL_OPT": {"MOTION"},
    "EACH": {"PRINT"},
    "OT": {"SCF"},
    "DIAGONALIZATION": {"SCF"},
    "SMEAR": {"SCF"},
    "MIXING": {"SCF"},
    "BASIS_SET_FILE_NAME": {"FORCE_EVAL"},
    "POTENTIAL_FILE_NAME": {"FORCE_EVAL"},
}

# Common configuration smell thresholds
LOW_CUTOFF_THRESHOLD = 200  # Ry - very low, likely mistake
LOW_REL_CUTOFF_THRESHOLD = 30  # Ry - very low
FEW_SCF_THRESHOLD = 10  # iterations - very few
LOOSE_SCF_EPS = 1.0e-4  # too loose for production
SHORT_TIMESTEP_FS = 0.01  # fs - suspiciously short
LONG_TIMESTEP_FS = 5.0  # fs - suspiciously long for most MD
LOW_ELECTRONIC_TEMP_K = 10  # K - very low
GEO_OPT_MAX_ITER_LOW = 5  # very few iterations for geometry optimization


@dataclass
class SectionNode:
    """Represents a parsed section with its context."""
    name: str
    keywords: List[Tuple[str, str, int]] = field(default_factory=list)  # (name, value, line)
    subsections: List["SectionNode"] = field(default_factory=list)
    parent: Optional["SectionNode"] = None
    line: int = 0


@lru_cache(maxsize=1)
def _get_all_schema_keywords() -> Set[str]:
    """Extract all valid keyword names from the XML schema."""
    keywords = set(ACCEPTED_KEYWORD_ALIASES)
    try:
        tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = tree.getroot()
        for kw_node in root.iter("KEYWORD"):
            for name_node in kw_node.findall("./NAME"):
                if name_node.text:
                    keywords.add(name_node.text.upper())
    except Exception:
        pass
    return keywords


@lru_cache(maxsize=1)
def _get_all_schema_sections() -> Set[str]:
    """Extract all valid section names from the XML schema."""
    sections = set()
    try:
        tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = tree.getroot()
        for sec_node in root.iter("SECTION"):
            for name_node in sec_node.findall("./NAME"):
                if name_node.text:
                    sections.add(name_node.text.upper())
    except Exception:
        pass
    return sections


def _parse_sections(text: str) -> List[SectionNode]:
    """Parse CP2K input text into a section tree."""
    lines = text.split('\n')
    root = SectionNode(name="/", line=0)
    stack = [root]

    section_re = re.compile(r"^(\s*)&(\w[\w\-_]*)\s*(.*)", re.IGNORECASE)
    end_re = re.compile(r"^(\s*)&END\s+(\w[\w\-_]*)", re.IGNORECASE)
    keyword_re = re.compile(r"^(\s*)(\w[\w\-_]*)\s+(.*)")

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("!") or stripped.startswith("#"):
            continue

        # Skip preprocessor directives
        if stripped.startswith("@"):
            continue

        # Check for section end
        end_match = end_re.match(line)
        if end_match:
            end_name = end_match.group(2).upper()
            # Pop the matching section from stack
            for j in range(len(stack) - 1, 0, -1):
                if stack[j].name == end_name:
                    stack = stack[:j]
                    break
            continue

        # Check for section start
        sec_match = section_re.match(line)
        if sec_match:
            sec_name = sec_match.group(2).upper()
            if sec_name == "END":
                continue
            new_node = SectionNode(name=sec_name, line=i)
            new_node.parent = stack[-1]
            stack[-1].subsections.append(new_node)
            stack.append(new_node)
            continue

        # Check for keyword
        kw_match = keyword_re.match(line)
        if kw_match and stack:
            kw_name = kw_match.group(2).upper()
            kw_value = kw_match.group(3).strip()
            stack[-1].keywords.append((kw_name, kw_value, i))

    return root.subsections


def _fuzzy_match(keyword: str, valid_keywords: Set[str], threshold: float = 0.7) -> Optional[str]:
    """Find the closest matching valid keyword using fuzzy matching."""
    matches = difflib.get_close_matches(keyword, list(valid_keywords), n=1, cutoff=threshold)
    return matches[0] if matches else None


def lint_keywords_misspelled(text: str, valid_keywords: Set[str]) -> List[Diagnostic]:
    """Detect potentially misspelled keywords by fuzzy matching against schema."""
    diagnostics = []
    lines = text.split('\n')
    section_re = re.compile(r"^(\s*)&(\w[\w\-_]*)\s*", re.IGNORECASE)
    end_re = re.compile(r"^(\s*)&END\s+(\w[\w\-_]*)", re.IGNORECASE)
    keyword_re = re.compile(r"^(\s*)(\w[\w\-_]*)\s+(.*)")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("!") or stripped.startswith("#") or stripped.startswith("@"):
            continue

        if section_re.match(line) or end_re.match(line):
            continue

        kw_match = keyword_re.match(line)
        if kw_match:
            kw_name = kw_match.group(2).upper()
            if kw_name not in valid_keywords:
                suggestion = _fuzzy_match(kw_name, valid_keywords)
                if suggestion:
                    diagnostics.append(Diagnostic(
                        severity="warning",
                        source="cp2k-lint",
                        code=RULE_MISSPELLED_KEYWORD,
                        message=f"Unknown keyword '{kw_name}'. Did you mean '{suggestion}'?",
                        line=i,
                        column=kw_match.start(2),
                    ))
    return diagnostics


def lint_invalid_nesting(text: str, valid_sections: Set[str]) -> List[Diagnostic]:
    """Detect sections placed under invalid parent sections."""
    diagnostics = []
    sections = _parse_sections(text)

    def check_section(node: SectionNode, parent_name: str):
        valid_parents = VALID_SECTION_PARENTS.get(node.name)
        if valid_parents is not None and parent_name not in valid_parents:
            diagnostics.append(Diagnostic(
                severity="error",
                source="cp2k-lint",
                code=RULE_INVALID_NESTING,
                message=f"Section '&{node.name}' is not valid under '&{parent_name}'. "
                        f"Expected one of: {', '.join(sorted(valid_parents))}",
                line=node.line,
            ))
        for sub in node.subsections:
            check_section(sub, node.name)

    for section in sections:
        check_section(section, "/")

    return diagnostics


def lint_duplicates(text: str) -> List[Diagnostic]:
    """Detect duplicate keywords or non-repeating sections."""
    diagnostics = []
    sections = _parse_sections(text)

    def check_duplicates(node: SectionNode):
        # Check for duplicate keywords
        if node.name not in DATA_RECORD_SECTIONS:
            kw_names = [kw[0] for kw in node.keywords]
            kw_counts = Counter(kw_names)
            for kw_name, count in kw_counts.items():
                if count > 1:
                    # Find the line of the second occurrence
                    lines = [kw[2] for kw in node.keywords if kw[0] == kw_name]
                    diagnostics.append(Diagnostic(
                        severity="warning",
                        source="cp2k-lint",
                        code=RULE_DUPLICATE_KEYWORD,
                        message=f"Keyword '{kw_name}' appears {count} times in section '&{node.name}'. "
                                f"This may be unintended.",
                        line=lines[1] if len(lines) > 1 else lines[0],
                    ))

        # Check for duplicate non-repeating sections
        sec_names = [sub.name for sub in node.subsections]
        sec_counts = Counter(sec_names)
        for sec_name, count in sec_counts.items():
            if count > 1 and sec_name not in REPEATABLE_SECTIONS:
                # Find the line of the second occurrence
                lines = [sub.line for sub in node.subsections if sub.name == sec_name]
                diagnostics.append(Diagnostic(
                    severity="warning",
                    source="cp2k-lint",
                    code=RULE_DUPLICATE_SECTION,
                    message=f"Section '&{sec_name}' appears {count} times under '&{node.name}'. "
                            f"This may be unintended.",
                    line=lines[1] if len(lines) > 1 else lines[0],
                ))

        for sub in node.subsections:
            check_duplicates(sub)

    for section in sections:
        check_duplicates(section)

    return diagnostics


def lint_config_smells(text: str) -> List[Diagnostic]:
    """Detect configuration smells like very low cutoff, few SCF iterations, etc."""
    diagnostics = []
    lines = text.split('\n')
    keyword_re = re.compile(r"^(\s*)(\w[\w\-_]*)\s+(.*)", re.IGNORECASE)

    current_section_path = []  # Track current section context
    section_re = re.compile(r"^(\s*)&(\w[\w\-_]*)\s*", re.IGNORECASE)
    end_re = re.compile(r"^(\s*)&END\s+(\w[\w\-_]*)", re.IGNORECASE)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("!") or stripped.startswith("#") or stripped.startswith("@"):
            continue

        sec_match = section_re.match(line)
        if sec_match:
            sec_name = sec_match.group(2).upper()
            if sec_name != "END":
                current_section_path.append(sec_name)
            continue

        end_match = end_re.match(line)
        if end_match:
            end_name = end_match.group(2).upper()
            while current_section_path and current_section_path[-1] != end_name:
                current_section_path.pop()
            if current_section_path and current_section_path[-1] == end_name:
                current_section_path.pop()
            continue

        kw_match = keyword_re.match(line)
        if kw_match:
            kw_name = kw_match.group(2).upper()
            kw_value = kw_match.group(3).strip()

            # Check CUTOFF
            if kw_name == "CUTOFF":
                try:
                    # Extract numeric value, ignoring unit
                    val_str = re.sub(r'[^\d.eE+-]', '', kw_value.split()[0]) if kw_value.split() else kw_value
                    cutoff_val = float(val_str)
                    if cutoff_val < LOW_CUTOFF_THRESHOLD:
                        diagnostics.append(Diagnostic(
                            severity="warning",
                            source="cp2k-lint",
                            code=RULE_LOW_CUTOFF,
                            message=(
                                f"CUTOFF {cutoff_val} Ry is very low. Consider "
                                f"≥ {LOW_CUTOFF_THRESHOLD} Ry for reasonable accuracy."
                            ),
                            line=i,
                        ))
                except (ValueError, IndexError):
                    pass

            # Check REL_CUTOFF
            if kw_name == "REL_CUTOFF":
                try:
                    val_str = re.sub(r'[^\d.eE+-]', '', kw_value.split()[0]) if kw_value.split() else kw_value
                    rel_cutoff_val = float(val_str)
                    if rel_cutoff_val < LOW_REL_CUTOFF_THRESHOLD:
                        diagnostics.append(Diagnostic(
                            severity="warning",
                            source="cp2k-lint",
                            code=RULE_LOW_REL_CUTOFF,
                            message=f"REL_CUTOFF {rel_cutoff_val} Ry is very low. Consider ≥ {LOW_REL_CUTOFF_THRESHOLD} Ry.",
                            line=i,
                        ))
                except (ValueError, IndexError):
                    pass

            # Check MAX_SCF
            if kw_name == "MAX_SCF":
                try:
                    max_scf = int(kw_value.split()[0]) if kw_value.split() else int(kw_value)
                    if max_scf < FEW_SCF_THRESHOLD:
                        diagnostics.append(Diagnostic(
                            severity="warning",
                            source="cp2k-lint",
                            code=RULE_MAX_SCF_TOO_LOW,
                            message=f"MAX_SCF {max_scf} is very low. SCF may not converge. Consider ≥ {FEW_SCF_THRESHOLD}.",
                            line=i,
                        ))
                except (ValueError, IndexError):
                    pass

            # Check EPS_SCF
            if kw_name == "EPS_SCF":
                try:
                    eps_str = kw_value.split()[0] if kw_value.split() else kw_value
                    eps_val = float(eps_str)
                    if eps_val > LOOSE_SCF_EPS:
                        diagnostics.append(Diagnostic(
                            severity="warning",
                            source="cp2k-lint",
                            code=RULE_LOOSE_SCF_EPS,
                            message=f"EPS_SCF {eps_val} is very loose. Consider ≤ 1.0e-6 for production runs.",
                            line=i,
                        ))
                except (ValueError, IndexError):
                    pass

            # Check TIMESTEP
            if kw_name == "TIMESTEP":
                try:
                    # TIMESTEP can have units like [fs]
                    parts = kw_value.split()
                    if parts:
                        val_str = re.sub(r'[^\d.eE+-]', '', parts[0])
                        timestep_val = float(val_str)
                        if 0 < timestep_val < SHORT_TIMESTEP_FS:
                            diagnostics.append(Diagnostic(
                                severity="warning",
                                source="cp2k-lint",
                                code=RULE_SHORT_TIMESTEP,
                                message=f"TIMESTEP {timestep_val} fs is very short. Is this intentional?",
                                line=i,
                            ))
                        elif timestep_val > LONG_TIMESTEP_FS:
                            diagnostics.append(Diagnostic(
                                severity="warning",
                                source="cp2k-lint",
                                code=RULE_LONG_TIMESTEP,
                                message=f"TIMESTEP {timestep_val} fs is very long. Most MD simulations use 0.5-2.0 fs.",
                                line=i,
                            ))
                except (ValueError, IndexError):
                    pass

            # Check MAX_ITER in GEO_OPT
            if kw_name == "MAX_ITER" and "GEO_OPT" in current_section_path:
                try:
                    max_iter = int(kw_value.split()[0]) if kw_value.split() else int(kw_value)
                    if max_iter < GEO_OPT_MAX_ITER_LOW:
                        diagnostics.append(Diagnostic(
                            severity="warning",
                            source="cp2k-lint",
                            code=RULE_GEO_OPT_MAX_ITER_LOW,
                            message=f"GEO_OPT MAX_ITER {max_iter} is very low. Geometry optimization may not converge.",
                            line=i,
                        ))
                except (ValueError, IndexError):
                    pass

    return diagnostics


def lint(text: str) -> List[Diagnostic]:
    """Run all lint checks on a CP2K input text and return diagnostics."""
    all_diagnostics = []

    # Get schema data
    valid_keywords = _get_all_schema_keywords()

    # Run lint rules
    all_diagnostics.extend(lint_keywords_misspelled(text, valid_keywords))
    all_diagnostics.extend(lint_invalid_nesting(text, set()))
    all_diagnostics.extend(lint_duplicates(text))
    all_diagnostics.extend(lint_config_smells(text))

    return all_diagnostics
