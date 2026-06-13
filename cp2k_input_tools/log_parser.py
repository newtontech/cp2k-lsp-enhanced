"""CP2K runtime log file parser (issue #117).

Parses CP2K ``.out`` / ``.log`` files and converts runtime failures into
structured :class:`LogDiagnostic` records that map back to likely input
causes.

The module ships a stable set of pattern-based rules, each tagged with:

* ``rule_id`` -- canonical OpenQC identifier (``cp2k.log.*``);
* ``severity`` -- ``error`` / ``warning`` / ``information``;
* ``likely_section`` -- the input section most likely responsible for the
  failure (e.g. ``FORCE_EVAL > DFT > SCF``);
* ``explanation`` -- one-sentence explanation of the failure;
* ``suggested_action`` -- concrete next action;
* ``provenance_id`` -- manual / wiki reference for the rule.

Backward compatibility: ``SCFConvergenceParser``, ``parse_log_file`` and
``parse_log_content`` keep their existing behaviour, while
``LogDiagnostic`` gains new optional metadata fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Canonical rule IDs (single source of truth for #117)
# ---------------------------------------------------------------------------

RULE_LOG_SCF_NOT_CONVERGED = "cp2k.log.scf_not_converged"
RULE_LOG_OUTER_SCF_NOT_CONVERGED = "cp2k.log.outer_scf_not_converged"
RULE_LOG_GEO_OPT_NOT_CONVERGED = "cp2k.log.geo_opt_not_converged"
RULE_LOG_MD_INSTABILITY = "cp2k.log.md_instability"
RULE_LOG_MISSING_BASIS_FILE = "cp2k.log.missing_basis_file"
RULE_LOG_MISSING_POTENTIAL_FILE = "cp2k.log.missing_potential_file"
RULE_LOG_UNKNOWN_BASIS = "cp2k.log.unknown_basis"
RULE_LOG_UNKNOWN_POTENTIAL = "cp2k.log.unknown_potential"
RULE_LOG_INCONSISTENT_CELL = "cp2k.log.inconsistent_cell"
RULE_LOG_WALLTIME_EXCEEDED = "cp2k.log.walltime_exceeded"
RULE_LOG_ABORT = "cp2k.log.abort"
RULE_LOG_SEGFAULT = "cp2k.log.segfault"


@dataclass
class LogDiagnostic:
    """A diagnostic from CP2K log output.

    The first five fields (``rule_id``, ``message``, ``line_number``,
    ``severity``, ``hint``) are preserved verbatim from the original
    module so existing consumers keep working.  The new optional fields
    carry the richer metadata required by issue #117.
    """

    rule_id: str
    message: str
    line_number: int
    severity: str = "error"
    hint: Optional[str] = None
    likely_section: Optional[str] = None
    explanation: Optional[str] = None
    suggested_action: Optional[str] = None
    provenance_id: Optional[str] = None
    related_keyword: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Serialize to a JSON-friendly dictionary."""
        payload: Dict[str, object] = {
            "rule_id": self.rule_id,
            "message": self.message,
            "line_number": self.line_number,
            "severity": self.severity,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.likely_section:
            payload["likely_section"] = self.likely_section
        if self.explanation:
            payload["explanation"] = self.explanation
        if self.suggested_action:
            payload["suggested_action"] = self.suggested_action
        if self.provenance_id:
            payload["provenance_id"] = self.provenance_id
        if self.related_keyword:
            payload["related_keyword"] = self.related_keyword
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload


@dataclass
class LogRule:
    """Declarative runtime-log pattern rule."""

    rule_id: str
    pattern: re.Pattern[str]
    message: str
    severity: str = "error"
    hint: Optional[str] = None
    likely_section: Optional[str] = None
    explanation: Optional[str] = None
    suggested_action: Optional[str] = None
    provenance_id: Optional[str] = None
    related_keyword: Optional[str] = None
    # If True, the rule fires once per file (using the first match); otherwise
    # it fires once per matching line.
    once_per_file: bool = False


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------


def _compile(rules: List[LogRule]) -> List[LogRule]:
    """Helper to declare the rule registry in a single expression."""
    return rules


LOG_RULES: List[LogRule] = _compile(
    [
        # ------------------------------------------------------------------
        # SCF non-convergence (two variants for backward-compat messages).
        # Both rules share the same rule_id and use ``once_per_file=True`` so
        # that a single SCF failure yields exactly one diagnostic regardless
        # of how many lines in the log repeat the warning.
        # ------------------------------------------------------------------
        LogRule(
            rule_id=RULE_LOG_SCF_NOT_CONVERGED,
            pattern=re.compile(
                r"SCF\s+run\s+not\s+converged\s+after\s+maximum\s+number\s+of\s+iterations",
                re.IGNORECASE,
            ),
            message="SCF reached maximum iterations without convergence.",
            severity="error",
            hint="Increase MAX_SCF or tighten convergence criteria (EPS_SCF).",
            likely_section="FORCE_EVAL > DFT > SCF",
            explanation=(
                "The self-consistent field cycle hit the MAX_SCF iteration cap "
                "without reaching the requested EPS_SCF threshold."
            ),
            suggested_action=(
                "Raise MAX_SCF, tighten EPS_SCF, switch to OT, or improve the "
                "initial guess (SCF_GUESS RESTART)."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/SCF/MAX_SCF",
            related_keyword="MAX_SCF",
            once_per_file=True,
        ),
        LogRule(
            rule_id=RULE_LOG_SCF_NOT_CONVERGED,
            pattern=re.compile(
                r"SCF\s+run\s+NOT\s+converged",
                re.IGNORECASE,
            ),
            message="SCF calculation did not converge.",
            severity="error",
            hint="Increase MAX_SCF or tighten EPS_SCF; consider a better initial guess.",
            likely_section="FORCE_EVAL > DFT > SCF",
            explanation=(
                "The self-consistent field cycle did not reach the requested "
                "convergence threshold."
            ),
            suggested_action=(
                "Raise MAX_SCF, tighten EPS_SCF, switch to OT, or improve the "
                "initial guess (SCF_GUESS RESTART)."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/SCF",
            related_keyword="MAX_SCF",
            once_per_file=True,
        ),
        LogRule(
            rule_id=RULE_LOG_OUTER_SCF_NOT_CONVERGED,
            pattern=re.compile(
                r"Outer\s+SCF\s+(?:loop\s+)?not\s+converged",
                re.IGNORECASE,
            ),
            message="Outer SCF loop did not converge.",
            severity="error",
            hint="Increase OUTER_SCF MAX_SCF or check the inner-SCF threshold.",
            likely_section="FORCE_EVAL > DFT > SCF > OUTER_SCF",
            explanation=(
                "The outer SCF iteration (e.g. CDFT or Krylov) exceeded its "
                "iteration budget."
            ),
            suggested_action=(
                "Raise OUTER_SCF%MAX_SCF, check the inner-SCF convergence, and "
                "verify the constraint setup."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/SCF/OUTER_SCF",
            related_keyword="MAX_SCF",
        ),
        LogRule(
            rule_id=RULE_LOG_GEO_OPT_NOT_CONVERGED,
            pattern=re.compile(
                r"(?:Reaching\s+maximum\s+number\s+of\s+(?:geometry\s+)?optimizations"
                r"|Geometry\s+optimization\s+not\s+converged"
                r"|GEOMETRY\s+OPTIMIZATION\s+NOT\s+CONVERGED)",
                re.IGNORECASE,
            ),
            message="Geometry optimization did not converge.",
            severity="error",
            hint="Increase MAX_ITER or switch to a more robust optimizer.",
            likely_section="MOTION > GEO_OPT",
            explanation=(
                "The geometry optimizer exhausted its iteration budget without "
                "satisfying the RMS/MAX force and displacement criteria."
            ),
            suggested_action=(
                "Raise MAX_ITER under &GEO_OPT, switch OPTIMIZER to BFGS/LBFGS, "
                "or relax the convergence thresholds."
            ),
            provenance_id="cp2k manual:MOTION/GEO_OPT",
            related_keyword="MAX_ITER",
        ),
        LogRule(
            rule_id=RULE_LOG_MD_INSTABILITY,
            pattern=re.compile(
                r"(?:\bNaN\b"
                r"|Inf\s+in\s+energy"
                r"|temperature\s+is\s+(?:NaN|Inf)"
                r"|MD\s+run\s+(?:became|is)\s+unstable"
                r"|velocity\s+explosion)",
                re.IGNORECASE,
            ),
            message="MD simulation became unstable (NaN/temperature blow-up).",
            severity="error",
            hint="Reduce TIMESTEP, equilibrate at lower temperature, or check the potential.",
            likely_section="MOTION > MD",
            explanation=(
                "Energy/temperature show NaN or unphysical blow-up, typically "
                "from too large a timestep or overlapping atoms."
            ),
            suggested_action=(
                "Decrease TIMESTEP to 0.25-0.5 fs, run a short NVT "
                "equilibration, and verify the initial coordinates."
            ),
            provenance_id="cp2k manual:MOTION/MD/TIMESTEP",
            related_keyword="TIMESTEP",
        ),
        LogRule(
            rule_id=RULE_LOG_MISSING_BASIS_FILE,
            pattern=re.compile(
                r"(?:could\s+not\s+read\s+basis\s+set\s+file"
                r"|basis\s+set\s+file\s+(?:could\s+not\s+be\s+)?(?:read|found|opened)"
                r"|BASIS_SET_FILE_NAME\s+.*?not\s+found"
                r"|could\s+not\s+find\s+(?:the\s+)?basis\s+set\s+(?:data\s+)?file)",
                re.IGNORECASE,
            ),
            message="CP2K could not read the basis set file.",
            severity="error",
            hint="Verify BASIS_SET_FILE_NAME points to an existing readable file.",
            likely_section="FORCE_EVAL > DFT",
            explanation=(
                "CP2K was unable to open the basis set library referenced from "
                "BASIS_SET_FILE_NAME."
            ),
            suggested_action=(
                "Set BASIS_SET_FILE_NAME to a readable file (typically "
                "BASIS_SET) and check the working directory."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/BASIS_SET_FILE_NAME",
            related_keyword="BASIS_SET_FILE_NAME",
        ),
        LogRule(
            rule_id=RULE_LOG_MISSING_POTENTIAL_FILE,
            pattern=re.compile(
                r"(?:could\s+not\s+read\s+(?:the\s+)?potential\s+file"
                r"|potential\s+file\s+(?:could\s+not\s+be\s+)?(?:read|found|opened)"
                r"|POTENTIAL_FILE_NAME\s+.*?not\s+found"
                r"|could\s+not\s+find\s+(?:the\s+)?(?:GTH-)?potential\s+(?:data\s+)?file)",
                re.IGNORECASE,
            ),
            message="CP2K could not read the pseudopotential file.",
            severity="error",
            hint="Verify POTENTIAL_FILE_NAME points to an existing readable file.",
            likely_section="FORCE_EVAL > DFT",
            explanation=(
                "CP2K was unable to open the pseudopotential library referenced "
                "from POTENTIAL_FILE_NAME."
            ),
            suggested_action=(
                "Set POTENTIAL_FILE_NAME to a readable file (typically "
                "POTENTIAL or GTH_POTENTIALS)."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/POTENTIAL_FILE_NAME",
            related_keyword="POTENTIAL_FILE_NAME",
        ),
        LogRule(
            rule_id=RULE_LOG_UNKNOWN_BASIS,
            pattern=re.compile(
                r"(?:No\s+basis\s+set\s+could\s+be\s+found"
                r"|basis\s+set\s+(?:\S+)\s+(?:is\s+)?(?:not|currently\s+not)\s+(?:available|defined)"
                r"|could\s+not\s+find\s+requested\s+basis\s+set"
                r"|A\s+basis\s+set\s+for\s+(?:kind\s+)?\w+\s+(?:could\s+)?not\s+be\s+found)",
                re.IGNORECASE,
            ),
            message="Requested basis set is unknown for the kind.",
            severity="error",
            hint="Use a basis set present in BASIS_SET_FILE_NAME for every KIND.",
            likely_section="FORCE_EVAL > SUBSYS > KIND",
            explanation=(
                "CP2K could not match the BASIS_SET label on a KIND to any "
                "entry in the loaded basis set file."
            ),
            suggested_action=(
                "Open BASIS_SET_FILE_NAME, check the spelling, or pick a "
                "well-known basis (DZVP-MOLOPT-SR-GTH, TZVP-GTH, ...)."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/SUBSYS/KIND/BASIS_SET",
            related_keyword="BASIS_SET",
        ),
        LogRule(
            rule_id=RULE_LOG_UNKNOWN_POTENTIAL,
            pattern=re.compile(
                r"(?:No\s+(?:GTH-)?potential\s+could\s+be\s+found"
                r"|potential\s+(?:\S+)\s+(?:is\s+)?(?:not|currently\s+not)\s+(?:available|defined)"
                r"|could\s+not\s+find\s+requested\s+(?:GTH-)?potential"
                r"|A\s+(?:GTH-)?potential\s+for\s+(?:kind\s+)?\w+\s+(?:could\s+)?not\s+be\s+found)",
                re.IGNORECASE,
            ),
            message="Requested pseudopotential is unknown for the kind.",
            severity="error",
            hint="Use a GTH potential present in POTENTIAL_FILE_NAME for every KIND.",
            likely_section="FORCE_EVAL > SUBSYS > KIND",
            explanation=(
                "CP2K could not match the POTENTIAL label on a KIND to any "
                "entry in the loaded potential file."
            ),
            suggested_action=(
                "Open POTENTIAL_FILE_NAME and verify the spelling (e.g. "
                "GTH-PBE-qN) for every KIND."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/SUBSYS/KIND/POTENTIAL",
            related_keyword="POTENTIAL",
        ),
        LogRule(
            rule_id=RULE_LOG_INCONSISTENT_CELL,
            pattern=re.compile(
                r"(?:Inconsistent\s+CELL/PERIODIC/POISSON/KPOINTS"
                r"|POISSON\s+solver\s+(?:\S+)\s+(?:requires|needs)\s+(?:XYZ|NONE)\s+periodicity"
                r"|periodicity\s+mismatch"
                r"|KPOINTS\s+requires\s+an?\s+(?:aperiodic|orthorhombic)\s+cell)",
                re.IGNORECASE,
            ),
            message="CELL / PERIODIC / POISSON / KPOINTS settings are inconsistent.",
            severity="error",
            hint="Reconcile CELL%PERIODIC with the chosen POISSON solver and KPOINTS block.",
            likely_section="FORCE_EVAL > DFT > POISSON / FORCE_EVAL > SUBSYS > CELL",
            explanation=(
                "CP2K detected that the cell periodicity, Poisson solver and "
                "(optional) k-point setup do not agree."
            ),
            suggested_action=(
                "Set CELL%PERIODIC to match the POISSON%POISSON_SOLVER and "
                "drop &KPOINTS for periodic runs."
            ),
            provenance_id="cp2k manual:FORCE_EVAL/DFT/POISSON",
            related_keyword="PERIODIC",
        ),
        LogRule(
            rule_id=RULE_LOG_WALLTIME_EXCEEDED,
            pattern=re.compile(
                r"(?:exceeded\s+the\s+(?:requested\s+)?wall[\s_-]?time"
                r"|walltime\s+(?:reached|exceeded)"
                r"|GLOBAL/WALLTIME\s+(?:reached|exceeded))",
                re.IGNORECASE,
            ),
            message="CP2K stopped because the GLOBAL WALLTIME was reached.",
            severity="warning",
            hint="Increase WALLTIME or write a restart file and resume.",
            likely_section="GLOBAL",
            explanation=(
                "CP2K cleanly stopped the run after the wall-time budget was "
                "consumed."
            ),
            suggested_action=(
                "Raise the WALLTIME keyword under &GLOBAL, or enable "
                "RESTART handling to resume the calculation."
            ),
            provenance_id="cp2k manual:GLOBAL/WALLTIME",
            related_keyword="WALLTIME",
        ),
        LogRule(
            rule_id=RULE_LOG_ABORT,
            pattern=re.compile(
                r"(?:\bABORT\b(?:ed)?\s+(?:in|from)"
                r"|called\s+via\s+mp_abort"
                r"|terminated\s+by\s+signal\s+(?:6|SIGABRT)"
                r"|CP2K\s+aborted)",
                re.IGNORECASE,
            ),
            message="CP2K aborted mid-run.",
            severity="error",
            hint="Inspect the surrounding log context for the CP2K source file/line.",
            likely_section="GLOBAL",
            explanation=(
                "CP2K raised an explicit abort (typically from a "
                "precondition violation in a CP2K source file)."
            ),
            suggested_action=(
                "Read the lines preceding the abort for the source file/line "
                "and reconcile the input that triggered the precondition."
            ),
            provenance_id="cp2k wiki:troubleshooting",
        ),
        LogRule(
            rule_id=RULE_LOG_SEGFAULT,
            pattern=re.compile(
                r"(?:Segmentation\s+fault"
                r"|\bSIGSEGV\b"
                r"|terminated\s+by\s+signal\s+11"
                r"|signal\s+11\s*\(\s*SIGSEGV\s*\))",
                re.IGNORECASE,
            ),
            message="CP2K crashed with a segmentation fault.",
            severity="error",
            hint="Re-run with a debug build or smaller system to isolate the trigger.",
            likely_section="GLOBAL",
            explanation=(
                "The CP2K process died with SIGSEGV, indicating a memory "
                "access violation inside CP2K or a library it depends on."
            ),
            suggested_action=(
                "Reduce the system size, verify the CP2K build, and report "
                "the backtrace if the input is otherwise valid."
            ),
            provenance_id="cp2k wiki:troubleshooting",
        ),
    ]
)


# ---------------------------------------------------------------------------
# Backward-compatible SCF parser (delegates to LOG_RULES)
# ---------------------------------------------------------------------------


class SCFConvergenceParser:
    """Parser for SCF convergence information in CP2K logs.

    Retained for backward compatibility with the original module.  The
    parser now delegates to :data:`LOG_RULES` so callers see the same
    metadata-rich diagnostics.
    """

    SCF_CONVERGED = re.compile(
        r"SCF run converged\s+in\s+\d+\s+iterations",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.diagnostics: List[LogDiagnostic] = []
        self.max_scf_iterations: Optional[int] = None
        self.converged = False

    def parse(self, content: str) -> List[LogDiagnostic]:
        """Parse log content and return SCF-related diagnostics."""
        self.diagnostics = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            self._check_scf_convergence(line, line_num)

        return self.diagnostics

    def _check_scf_convergence(self, line: str, line_num: int) -> None:
        """Check a single line for SCF convergence issues.

        Mirrors the original ``if/elif`` behaviour by emitting at most one
        diagnostic per line.  The more specific "after maximum number of
        iterations" rule wins over the generic "SCF run NOT converged" rule
        when both match.
        """
        for rule in LOG_RULES:
            if rule.rule_id not in (
                RULE_LOG_SCF_NOT_CONVERGED,
                RULE_LOG_OUTER_SCF_NOT_CONVERGED,
            ):
                continue
            if rule.pattern.search(line):
                self.diagnostics.append(_diagnostic_from_rule(rule, line_num, line))
                return


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _diagnostic_from_rule(rule: LogRule, line_num: int, line: str) -> LogDiagnostic:
    """Build a :class:`LogDiagnostic` from a matched rule."""
    return LogDiagnostic(
        rule_id=rule.rule_id,
        message=rule.message,
        line_number=line_num,
        severity=rule.severity,
        hint=rule.hint,
        likely_section=rule.likely_section,
        explanation=rule.explanation,
        suggested_action=rule.suggested_action,
        provenance_id=rule.provenance_id,
        related_keyword=rule.related_keyword,
        extra={"matched_line": line.strip()[:200]},
    )


def parse_log_content(content: str, *, rules: Optional[Sequence[LogRule]] = None) -> List[LogDiagnostic]:
    """Parse CP2K log content and return all matched diagnostics.

    Args:
        content: CP2K log file content as a string.
        rules: Optional override sequence of :class:`LogRule` objects.  When
            omitted, the default :data:`LOG_RULES` registry is used.

    Returns:
        List of :class:`LogDiagnostic` records sorted by line number then
        rule id.
    """
    active_rules = list(rules) if rules is not None else list(LOG_RULES)
    diagnostics: List[LogDiagnostic] = []
    if not content:
        return diagnostics

    lines = content.split("\n")
    seen_once: set[str] = set()

    for offset, raw in enumerate(lines, start=1):
        for rule in active_rules:
            if not rule.pattern.search(raw):
                continue
            if rule.once_per_file:
                if rule.rule_id in seen_once:
                    continue
                seen_once.add(rule.rule_id)
            diagnostics.append(_diagnostic_from_rule(rule, offset, raw))

    diagnostics.sort(key=lambda d: (d.line_number, d.rule_id))
    return diagnostics


def parse_log_file(log_path: str, *, rules: Optional[Sequence[LogRule]] = None) -> List[LogDiagnostic]:
    """Parse a CP2K log file and return all matched diagnostics.

    Args:
        log_path: Path to the CP2K output log file.
        rules: Optional override sequence of :class:`LogRule` objects.

    Returns:
        List of :class:`LogDiagnostic` records (empty if the file does
        not exist or cannot be read).
    """
    log_file = Path(log_path)
    if not log_file.exists():
        return []
    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return parse_log_content(content, rules=rules)


def list_log_rules() -> List[Dict[str, object]]:
    """Return a JSON-friendly manifest of the built-in log rules."""
    return [
        {
            "rule_id": rule.rule_id,
            "severity": rule.severity,
            "message": rule.message,
            "hint": rule.hint,
            "likely_section": rule.likely_section,
            "explanation": rule.explanation,
            "suggested_action": rule.suggested_action,
            "provenance_id": rule.provenance_id,
            "related_keyword": rule.related_keyword,
            "once_per_file": rule.once_per_file,
        }
        for rule in LOG_RULES
    ]


__all__ = [
    "LogDiagnostic",
    "LogRule",
    "SCFConvergenceParser",
    "LOG_RULES",
    "RULE_LOG_SCF_NOT_CONVERGED",
    "RULE_LOG_OUTER_SCF_NOT_CONVERGED",
    "RULE_LOG_GEO_OPT_NOT_CONVERGED",
    "RULE_LOG_MD_INSTABILITY",
    "RULE_LOG_MISSING_BASIS_FILE",
    "RULE_LOG_MISSING_POTENTIAL_FILE",
    "RULE_LOG_UNKNOWN_BASIS",
    "RULE_LOG_UNKNOWN_POTENTIAL",
    "RULE_LOG_INCONSISTENT_CELL",
    "RULE_LOG_WALLTIME_EXCEEDED",
    "RULE_LOG_ABORT",
    "RULE_LOG_SEGFAULT",
    "list_log_rules",
    "parse_log_content",
    "parse_log_file",
]
