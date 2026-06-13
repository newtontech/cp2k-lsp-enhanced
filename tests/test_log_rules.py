"""Tests for the extended CP2K runtime-log rule registry (issue #117).

Each rule is exercised through:

* a one-line smoke test that triggers exactly the rule;
* an invalid fixture under ``tests/fixtures/logs/`` that should fire it;
* a valid fixture under ``tests/fixtures/logs/`` that should *not* fire it.

The rule registry metadata (severity, likely_section, provenance_id, ...) is
also asserted so the rich envelope contract stays stable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cp2k_input_tools.log_parser import (
    LOG_RULES,
    LogDiagnostic,
    RULE_LOG_ABORT,
    RULE_LOG_GEO_OPT_NOT_CONVERGED,
    RULE_LOG_INCONSISTENT_CELL,
    RULE_LOG_MD_INSTABILITY,
    RULE_LOG_MISSING_BASIS_FILE,
    RULE_LOG_MISSING_POTENTIAL_FILE,
    RULE_LOG_OUTER_SCF_NOT_CONVERGED,
    RULE_LOG_SEGFAULT,
    RULE_LOG_SCF_NOT_CONVERGED,
    RULE_LOG_UNKNOWN_BASIS,
    RULE_LOG_UNKNOWN_POTENTIAL,
    RULE_LOG_WALLTIME_EXCEEDED,
    list_log_rules,
    parse_log_content,
    parse_log_file,
)

TEST_DIR = Path(__file__).resolve().parent
LOG_FIXTURES = TEST_DIR / "fixtures" / "logs"
RULE_FIXTURES = TEST_DIR / "fixtures" / "rules"


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


class TestLogRuleRegistry:
    def test_registry_covers_required_failure_modes(self):
        """Issue #117: required failure modes must each have a rule."""
        required = {
            RULE_LOG_SCF_NOT_CONVERGED,
            RULE_LOG_OUTER_SCF_NOT_CONVERGED,
            RULE_LOG_GEO_OPT_NOT_CONVERGED,
            RULE_LOG_MD_INSTABILITY,
            RULE_LOG_MISSING_BASIS_FILE,
            RULE_LOG_MISSING_POTENTIAL_FILE,
            RULE_LOG_UNKNOWN_BASIS,
            RULE_LOG_UNKNOWN_POTENTIAL,
            RULE_LOG_INCONSISTENT_CELL,
            RULE_LOG_WALLTIME_EXCEEDED,
            RULE_LOG_ABORT,
            RULE_LOG_SEGFAULT,
        }
        present = {rule.rule_id for rule in LOG_RULES}
        missing = required - present
        assert not missing, f"Missing rule ids in LOG_RULES: {sorted(missing)}"

    def test_every_rule_carries_rich_metadata(self):
        """Each rule must carry section/explanation/suggested_action/provenance."""
        for rule in LOG_RULES:
            assert rule.likely_section, f"{rule.rule_id} missing likely_section"
            assert rule.explanation, f"{rule.rule_id} missing explanation"
            assert rule.suggested_action, f"{rule.rule_id} missing suggested_action"
            assert rule.provenance_id, f"{rule.rule_id} missing provenance_id"
            assert rule.severity in {"error", "warning", "information", "hint"}

    def test_list_log_rules_is_jsonable(self):
        manifest = list_log_rules()
        # Round-trip through JSON to guarantee serialisability.
        encoded = json.dumps(manifest)
        decoded = json.loads(encoded)
        assert len(decoded) == len(LOG_RULES)
        first = decoded[0]
        for field in (
            "rule_id",
            "severity",
            "likely_section",
            "explanation",
            "suggested_action",
            "provenance_id",
        ):
            assert field in first


# ---------------------------------------------------------------------------
# Per-rule smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rule_id, sample",
    [
        (RULE_LOG_SCF_NOT_CONVERGED, "SCF| WARNING: SCF run NOT converged"),
        (RULE_LOG_OUTER_SCF_NOT_CONVERGED, "OUTER SCF| outer SCF loop not converged after 50"),
        (RULE_LOG_GEO_OPT_NOT_CONVERGED, "Reaching maximum number of geometry optimizations"),
        (RULE_LOG_MD_INSTABILITY, "MD step 50, kinetic = NaN"),
        (RULE_LOG_MISSING_BASIS_FILE, "could not read basis set file BASIS_SET"),
        (RULE_LOG_MISSING_POTENTIAL_FILE, "could not find the potential file POTENTIAL"),
        (RULE_LOG_UNKNOWN_BASIS, "No basis set could be found for kind O"),
        (RULE_LOG_UNKNOWN_POTENTIAL, "A potential for kind H could not be found"),
        (RULE_LOG_INCONSISTENT_CELL, "POISSON solver ANALYTIC requires XYZ periodicity"),
        (RULE_LOG_WALLTIME_EXCEEDED, "exceeded the requested wall time of 3600 seconds"),
        (RULE_LOG_ABORT, "ABORT in routine pre_build_basisset from CP2K"),
        (RULE_LOG_SEGFAULT, "terminated by signal 11 (SIGSEGV)"),
    ],
)
def test_each_rule_fires_on_canonical_pattern(rule_id, sample):
    diagnostics = parse_log_content(sample)
    matched = [d for d in diagnostics if d.rule_id == rule_id]
    assert matched, f"rule {rule_id} did not fire on: {sample!r}"
    diag = matched[0]
    assert isinstance(diag, LogDiagnostic)
    # The metadata must be attached (issue #117 contract).
    assert diag.likely_section
    assert diag.explanation
    assert diag.suggested_action
    assert diag.provenance_id


def test_valid_log_lines_produce_no_diagnostics():
    content = (
        " SCF| SCF run converged in 10 iterations\n"
        " GEO OPT - CONVERGED at step 12\n"
        " MD step 50, kinetic = 50.0, total = -100.0\n"
        " PROGRAM ENDED AT 2024-01-15\n"
    )
    assert parse_log_content(content) == []


def test_log_diagnostic_to_dict_serialises_optional_fields():
    diag = LogDiagnostic(
        rule_id=RULE_LOG_SEGFAULT,
        message="CP2K crashed with a segmentation fault.",
        line_number=42,
        severity="error",
        hint="Re-run with a debug build.",
        likely_section="GLOBAL",
        explanation="The CP2K process died with SIGSEGV.",
        suggested_action="Reduce system size or report the backtrace.",
        provenance_id="cp2k wiki:troubleshooting",
    )
    payload = diag.to_dict()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["rule_id"] == RULE_LOG_SEGFAULT
    assert decoded["line_number"] == 42
    assert decoded["likely_section"] == "GLOBAL"
    assert decoded["severity"] == "error"


# ---------------------------------------------------------------------------
# Fixture-driven tests (invalid + valid pairs)
# ---------------------------------------------------------------------------


FIXTURE_PAIRS = [
    (RULE_LOG_SCF_NOT_CONVERGED, "scf_not_converged.out", "scf_converged.out", "log_scf_not_converged.json"),
    (RULE_LOG_OUTER_SCF_NOT_CONVERGED, "outer_scf_not_converged.out", "clean_run.out", "log_outer_scf_not_converged.json"),
    (RULE_LOG_GEO_OPT_NOT_CONVERGED, "geo_opt_not_converged.out", "geo_opt_converged.out", "log_geo_opt_not_converged.json"),
    (RULE_LOG_MD_INSTABILITY, "md_instability.out", "md_stable.out", "log_md_instability.json"),
    (RULE_LOG_MISSING_BASIS_FILE, "missing_basis_file.out", "clean_run.out", "log_missing_basis_file.json"),
    (RULE_LOG_MISSING_POTENTIAL_FILE, "missing_potential_file.out", "clean_run.out", "log_missing_potential_file.json"),
    (RULE_LOG_UNKNOWN_BASIS, "unknown_basis.out", "clean_run.out", "log_unknown_basis.json"),
    (RULE_LOG_UNKNOWN_POTENTIAL, "unknown_potential.out", "clean_run.out", "log_unknown_potential.json"),
    (RULE_LOG_INCONSISTENT_CELL, "inconsistent_cell.out", "clean_run.out", "log_inconsistent_cell.json"),
    (RULE_LOG_WALLTIME_EXCEEDED, "walltime_exceeded.out", "clean_run.out", "log_walltime_exceeded.json"),
    (RULE_LOG_ABORT, "abort.out", "clean_run.out", "log_abort.json"),
    (RULE_LOG_SEGFAULT, "segfault.out", "clean_run.out", "log_segfault.json"),
]


@pytest.mark.parametrize(
    "rule_id, invalid_fixture, valid_fixture, rule_golden",
    FIXTURE_PAIRS,
    ids=[p[0] for p in FIXTURE_PAIRS],
)
def test_log_rule_invalid_and_valid_fixtures(rule_id, invalid_fixture, valid_fixture, rule_golden):
    """Issue #117 acceptance: each rule fires on invalid fixture, stays quiet on valid one."""
    invalid_path = LOG_FIXTURES / invalid_fixture
    valid_path = LOG_FIXTURES / valid_fixture

    assert invalid_path.exists(), f"Missing invalid fixture: {invalid_path}"
    assert valid_path.exists(), f"Missing valid fixture: {valid_path}"

    invalid_diags = parse_log_file(str(invalid_path))
    valid_diags = parse_log_file(str(valid_path))

    invalid_match = [d for d in invalid_diags if d.rule_id == rule_id]
    assert invalid_match, (
        f"rule {rule_id} did not fire on invalid fixture {invalid_fixture}; "
        f"got {[d.rule_id for d in invalid_diags]}"
    )

    valid_match = [d for d in valid_diags if d.rule_id == rule_id]
    assert not valid_match, (
        f"rule {rule_id} unexpectedly fired on valid fixture {valid_fixture}"
    )


@pytest.mark.parametrize(
    "rule_id, invalid_fixture, valid_fixture, rule_golden",
    FIXTURE_PAIRS,
    ids=[p[0] for p in FIXTURE_PAIRS],
)
def test_log_rule_golden_manifest_matches_runtime(rule_id, invalid_fixture, valid_fixture, rule_golden):
    """The rule JSON manifest under tests/fixtures/rules/ matches the runtime registry."""
    manifest_path = RULE_FIXTURES / rule_golden
    assert manifest_path.exists(), f"Missing rule manifest: {manifest_path}"
    manifest = json.loads(manifest_path.read_text())

    assert manifest["rule_id"] == rule_id
    # The manifest's diagnostic block mirrors the diagnostic that fires on
    # the invalid fixture.  We compare against the produced diagnostic
    # (rather than the first rule definition) because some rule_ids have
    # multiple rule variants (e.g. MAX_SCF vs generic SCF).
    fired = [d for d in parse_log_file(str(LOG_FIXTURES / invalid_fixture)) if d.rule_id == rule_id]
    assert fired, f"rule {rule_id} did not fire on {invalid_fixture}"
    diag = fired[0]
    manifest_diag = manifest["diagnostics"][0]
    assert manifest_diag["rule_id"] == diag.rule_id
    assert manifest_diag["severity"] == diag.severity
    assert manifest_diag["likely_section"] == diag.likely_section
    assert manifest_diag["message"] == diag.message


def test_clean_run_fixture_emits_no_diagnostics():
    path = LOG_FIXTURES / "clean_run.out"
    assert path.exists()
    assert parse_log_file(str(path)) == []
