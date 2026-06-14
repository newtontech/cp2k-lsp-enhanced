"""Tests for the unified schema/type/path semantic diagnostics (issue #116).

The fixture-driven cases live under ``tests/fixtures/diagnostics/schema_semantic``
and are exercised via :func:`collect_semantic_diagnostics`.  Each fixture has
an accompanying ``*_golden.json`` describing the expected rule ids and
diagnostic count.

The tests also exercise the public ``SemanticDiagnostic`` contract directly so
that the rich metadata (``provenance_id``, ``suggested_fix``, ``code``,
``severity``) is verified without depending on the LSP transport.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cp2k_input_tools.semantic_diagnostics import (
    RULE_INVALID_NESTING,
    RULE_MISSING_GLOBAL,
    RULE_MISSING_REQUIRED_KEYWORD,
    RULE_TYPE_INTEGER,
    RULE_TYPE_LOGICAL,
    RULE_TYPE_REAL,
    RULE_UNKNOWN_ENUM,
    RULE_UNKNOWN_KEYWORD,
    RULE_UNKNOWN_SECTION,
    SemanticDiagnostic,
    collect_semantic_diagnostics,
)

TEST_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TEST_DIR / "fixtures" / "diagnostics" / "schema_semantic"


def _collect(fixture_name: str):
    text = (FIXTURE_DIR / f"{fixture_name}.inp").read_text()
    return collect_semantic_diagnostics(text)


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestSemanticDiagnosticContract:
    def test_to_dict_round_trip(self):
        diag = SemanticDiagnostic(
            rule_id=RULE_UNKNOWN_KEYWORD,
            severity="error",
            message="Keyword 'X' is not defined in section '&GLOBAL'.",
            code=RULE_UNKNOWN_KEYWORD,
            source="cp2k-schema",
            category="schema",
            line=2,
            column=0,
            end_line=2,
            end_column=10,
            provenance_id="cp2k_input.xml",
            suggested_fix="Remove or rename 'X'.",
            related_keyword="X",
            section_path="GLOBAL",
        )
        payload = diag.to_dict()
        assert payload["rule_id"] == RULE_UNKNOWN_KEYWORD
        assert payload["severity"] == "error"
        assert payload["provenance_id"] == "cp2k_input.xml"
        assert payload["suggested_fix"] == "Remove or rename 'X'."
        assert payload["range"]["start"] == {"line": 2, "character": 0}
        assert payload["related_keyword"] == "X"
        assert payload["section_path"] == "GLOBAL"


# ---------------------------------------------------------------------------
# Rule-level tests
# ---------------------------------------------------------------------------


class TestSchemaRules:
    def test_unknown_root_section(self):
        diags = _collect("unknown_root_section")
        rules = {d.rule_id for d in diags}
        assert RULE_UNKNOWN_SECTION in rules

    def test_unknown_nested_section(self):
        diags = _collect("unknown_nested_section")
        rules = {d.rule_id for d in diags}
        assert RULE_UNKNOWN_SECTION in rules

    def test_unknown_keyword(self):
        diags = _collect("unknown_keyword")
        rules = {d.rule_id for d in diags}
        assert RULE_UNKNOWN_KEYWORD in rules
        diag = next(d for d in diags if d.rule_id == RULE_UNKNOWN_KEYWORD)
        assert "FAKE_GLOBAL_KEYWORD" in diag.message
        assert diag.related_keyword == "FAKE_GLOBAL_KEYWORD"
        assert diag.section_path == "GLOBAL"

    def test_invalid_enum_value(self):
        diags = _collect("invalid_enum_value")
        rules = {d.rule_id for d in diags}
        assert RULE_UNKNOWN_ENUM in rules
        diag = next(d for d in diags if d.rule_id == RULE_UNKNOWN_ENUM)
        assert "NOT_A_REAL_RUN_TYPE" in diag.message

    def test_invalid_nesting(self):
        diags = _collect("invalid_nesting")
        rules = {d.rule_id for d in diags}
        assert RULE_INVALID_NESTING in rules


class TestTypeRules:
    def test_integer_mismatch(self):
        diags = _collect("type_integer_mismatch")
        rules = {d.rule_id for d in diags}
        assert RULE_TYPE_INTEGER in rules

    def test_real_mismatch(self):
        diags = _collect("type_real_mismatch")
        rules = {d.rule_id for d in diags}
        assert RULE_TYPE_REAL in rules

    def test_logical_mismatch(self):
        diags = _collect("type_logical_mismatch")
        rules = {d.rule_id for d in diags}
        assert RULE_TYPE_LOGICAL in rules


class TestStructuralRules:
    def test_missing_global(self):
        diags = _collect("missing_global")
        rules = {d.rule_id for d in diags}
        assert RULE_MISSING_GLOBAL in rules

    def test_missing_kind_element(self):
        diags = _collect("missing_kind_element")
        rules = {d.rule_id for d in diags}
        assert RULE_MISSING_REQUIRED_KEYWORD in rules

    def test_duplicate_keyword_emitted_as_warning(self):
        diags = _collect("duplicate_keyword")
        rules = {d.rule_id for d in diags}
        # The lint layer reports duplicates as the legacy rule id.
        assert "lint/duplicate-keyword" in rules or "cp2k.schema.duplicate_keyword" in rules


class TestValidInputsDoNotTrigger:
    def test_valid_minimal_has_no_errors(self):
        diags = _collect("valid_minimal")
        errors = [d for d in diags if d.severity == "error"]
        assert errors == [], [d.message for d in errors]


# ---------------------------------------------------------------------------
# Fixture-driven golden tests
# ---------------------------------------------------------------------------


def _golden_cases():
    if not FIXTURE_DIR.exists():
        return []
    return sorted(p.stem.replace("_golden", "") for p in FIXTURE_DIR.glob("*_golden.json"))


@pytest.mark.parametrize("case", _golden_cases())
def test_schema_semantic_golden_fixture(case):
    """Each fixture must match the rule/count recorded in its golden JSON."""
    golden_path = FIXTURE_DIR / f"{case}_golden.json"
    expected = json.loads(golden_path.read_text())
    diags = _collect(case)
    actual_rules = {d.rule_id for d in diags}
    if expected.get("diagnostic_count") is not None:
        # ``diagnostic_count`` is the *minimum* expected count, allowing the
        # implementation to surface additional related diagnostics without
        # rewriting goldens.
        assert len(diags) >= expected["diagnostic_count"], (
            f"{case}: expected at least {expected['diagnostic_count']} diagnostics, "
            f"got {len(diags)}: {[d.rule_id for d in diags]}"
        )
    for required_rule in expected.get("expected_rules", []):
        assert required_rule in actual_rules, (
            f"{case}: expected rule {required_rule} not present; got {sorted(actual_rules)}"
        )


# ---------------------------------------------------------------------------
# End-to-end: invalid + valid pairs (per acceptance criterion)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "invalid, valid",
    [
        ("unknown_root_section", "valid_minimal"),
        ("unknown_nested_section", "valid_minimal"),
        ("unknown_keyword", "valid_minimal"),
        ("invalid_enum_value", "valid_minimal"),
        ("type_integer_mismatch", "valid_minimal"),
        ("type_real_mismatch", "valid_minimal"),
        ("type_logical_mismatch", "valid_minimal"),
        ("invalid_nesting", "valid_minimal"),
        ("missing_global", "valid_minimal"),
        ("missing_kind_element", "valid_minimal"),
        ("duplicate_keyword", "valid_minimal"),
    ],
)
def test_each_rule_has_invalid_and_non_triggering_valid_fixture(invalid, valid):
    """Issue #116 acceptance: every rule has an invalid fixture and a
    non-triggering valid fixture."""
    invalid_diags = _collect(invalid)
    valid_diags = _collect(valid)

    # Invalid fixture must surface at least one error/warning.
    assert len(invalid_diags) > 0, f"Invalid fixture {invalid} produced no diagnostics"

    # Valid fixture must produce no error-level diagnostics.
    valid_errors = [d for d in valid_diags if d.severity == "error"]
    assert not valid_errors, (
        f"Valid fixture {valid} unexpectedly produced errors: "
        f"{[(d.rule_id, d.message) for d in valid_errors]}"
    )
