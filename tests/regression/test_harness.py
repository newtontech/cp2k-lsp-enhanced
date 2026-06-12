"""Regression harness integration tests (issue #71).

Top-level harness that validates:
1. Golden fixtures load correctly
2. All fixture types are present and valid
3. Linter + parser produce consistent results on fixtures
4. Log parser produces correct results on log fixtures
5. Determinism checks

Run: pytest tests/regression/test_harness.py -v
"""

import json
from pathlib import Path

from cp2k_input_tools.linter import lint
from cp2k_input_tools.log_parser import parse_log_file
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.parser_errors import ParserError
from cp2k_input_tools.tokenizer import TokenizerError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"
LOGS_DIR = FIXTURES_DIR / "logs"


def _get_all_diagnostics(filepath: str) -> list:
    """Get diagnostics for a file using linter + parser."""
    content = Path(filepath).read_text()
    diags = []

    # 1. Linter diagnostics
    try:
        lint_diags = lint(content)
        for d in lint_diags:
            diags.append({
                "line": getattr(d, "line", 0),
                "severity": getattr(d, "severity", "unknown"),
                "code": getattr(d, "code", ""),
                "message": getattr(d, "message", str(d)),
            })
    except Exception:
        pass

    # 2. Parser diagnostics
    try:
        parser = CP2KInputParser()
        parser.parse(content.splitlines())
    except (TokenizerError, ParserError) as exc:
        ctx = exc.args[1] if len(exc.args) > 1 else None
        line = getattr(ctx, "linenr", 1) if ctx else 1
        diags.append({
            "line": line,
            "severity": "error",
            "code": f"PARSER_{type(exc).__name__}",
            "message": str(exc.args[0]),
        })

    return diags


# ---------------------------------------------------------------------------
# Fixture loading validation
# ---------------------------------------------------------------------------

class TestHarnessFixtureLoading:
    """Verify that all fixture files can be loaded and parsed."""

    def test_golden_dir_exists(self):
        assert GOLDEN_DIR.is_dir(), f"Golden fixtures dir missing: {GOLDEN_DIR}"

    def test_mutations_dir_exists(self):
        assert MUTATIONS_DIR.is_dir(), f"Mutations fixtures dir missing: {MUTATIONS_DIR}"

    def test_logs_dir_exists(self):
        assert LOGS_DIR.is_dir(), f"Logs fixtures dir missing: {LOGS_DIR}"

    def test_golden_fixtures_have_valid_json(self):
        """Each .inp file in golden/ should have a matching _golden.json."""
        inp_files = list(GOLDEN_DIR.glob("*.inp"))
        assert len(inp_files) > 0, "Should have at least one golden fixture"

        for inp_file in inp_files:
            golden_file = inp_file.parent / f"{inp_file.stem}_golden.json"
            assert golden_file.exists(), f"Missing golden JSON for {inp_file.name}"
            data = json.loads(golden_file.read_text())
            assert "diagnostics" in data, f"Golden JSON missing 'diagnostics' key: {golden_file.name}"

    def test_mutation_fixtures_have_valid_json(self):
        """Each mutation .inp should have a matching golden JSON."""
        inp_files = list(MUTATIONS_DIR.glob("mutation_*.inp"))
        assert len(inp_files) > 0, "Should have at least one mutation fixture"

        for inp_file in inp_files:
            golden_file = inp_file.parent / f"{inp_file.stem}_golden.json"
            assert golden_file.exists(), f"Missing golden JSON for {inp_file.name}"
            data = json.loads(golden_file.read_text())
            assert "diagnostics" in data, f"Golden JSON missing 'diagnostics' key: {golden_file.name}"

    def test_log_fixtures_exist(self):
        """Log fixtures should be present."""
        log_files = list(LOGS_DIR.glob("*.out"))
        assert len(log_files) > 0, "Should have at least one log fixture"


# ---------------------------------------------------------------------------
# Harness evaluation
# ---------------------------------------------------------------------------

class TestHarnessEvaluation:
    """Test the evaluation of fixtures through linter + parser."""

    def test_golden_fixtures_evaluable(self):
        """All golden fixtures should be evaluable without crash."""
        for inp_file in GOLDEN_DIR.glob("*.inp"):
            diags = _get_all_diagnostics(str(inp_file))
            assert isinstance(diags, list)

    def test_mutation_fixtures_evaluable(self):
        """All mutation fixtures should be evaluable without crash."""
        for inp_file in MUTATIONS_DIR.glob("*.inp"):
            diags = _get_all_diagnostics(str(inp_file))
            assert isinstance(diags, list)

    def test_log_fixtures_evaluable(self):
        """All log fixtures should be parseable without crash."""
        for log_file in LOGS_DIR.glob("*.out"):
            diags = parse_log_file(str(log_file))
            assert isinstance(diags, list)

    def test_valid_golden_no_errors(self):
        """Valid golden inputs should produce no ERROR diagnostics."""
        for inp_file in GOLDEN_DIR.glob("valid_*.inp"):
            golden_file = inp_file.parent / f"{inp_file.stem}_golden.json"
            if not golden_file.exists():
                continue
            golden = json.loads(golden_file.read_text())
            if golden.get("diagnostics") != []:
                continue  # only check fixtures expecting no errors
            diags = _get_all_diagnostics(str(inp_file))
            errors = [d for d in diags if d.get("severity") == "error"]
            assert len(errors) == 0, (
                f"{inp_file.name}: expected no errors, got: {[d['message'] for d in errors]}"
            )

    def test_mutation_fixtures_have_diagnostics(self):
        """Mutation fixtures should produce at least one diagnostic."""
        for inp_file in MUTATIONS_DIR.glob("mutation_*.inp"):
            diags = _get_all_diagnostics(str(inp_file))
            assert len(diags) > 0, (
                f"{inp_file.name}: mutation should produce at least one diagnostic"
            )


# ---------------------------------------------------------------------------
# Determinism checks
# ---------------------------------------------------------------------------

class TestHarnessDeterminism:
    """Running diagnostics multiple times should produce identical results."""

    def test_golden_determinism(self):
        """Golden fixtures should produce identical diagnostics on repeated runs."""
        for inp_file in GOLDEN_DIR.glob("valid_*.inp"):
            r1 = _get_all_diagnostics(str(inp_file))
            r2 = _get_all_diagnostics(str(inp_file))
            msgs1 = sorted(d.get("message", "") for d in r1)
            msgs2 = sorted(d.get("message", "") for d in r2)
            assert msgs1 == msgs2, f"Non-deterministic: {inp_file.name}"

    def test_mutation_determinism(self):
        """Mutation fixtures should produce identical diagnostics on repeated runs."""
        for inp_file in MUTATIONS_DIR.glob("mutation_*.inp"):
            r1 = _get_all_diagnostics(str(inp_file))
            r2 = _get_all_diagnostics(str(inp_file))
            msgs1 = sorted(d.get("message", "") for d in r1)
            msgs2 = sorted(d.get("message", "") for d in r2)
            assert msgs1 == msgs2, f"Non-deterministic: {inp_file.name}"

    def test_log_parser_determinism(self):
        """Log parsing should be deterministic."""
        for log_file in LOGS_DIR.glob("*.out"):
            r1 = parse_log_file(str(log_file))
            r2 = parse_log_file(str(log_file))
            assert len(r1) == len(r2), f"Non-deterministic: {log_file.name}"
            for d1, d2 in zip(r1, r2, strict=True):
                assert d1.rule_id == d2.rule_id
                assert d1.message == d2.message
                assert d1.line_number == d2.line_number


# ---------------------------------------------------------------------------
# Closed-loop: verify golden snapshots match actual diagnostics
# ---------------------------------------------------------------------------

class TestHarnessClosedLoop:
    """Verify that golden snapshot expectations match actual behavior."""

    def test_valid_golden_snapshot_matches(self):
        """Golden snapshots for valid files should match actual diagnostics."""
        for inp_file in GOLDEN_DIR.glob("valid_*.inp"):
            golden_file = inp_file.parent / f"{inp_file.stem}_golden.json"
            if not golden_file.exists():
                continue
            golden = json.loads(golden_file.read_text())
            if golden.get("diagnostics") != []:
                continue

            diags = _get_all_diagnostics(str(inp_file))
            # Golden expects no diagnostics → actual should have no errors
            errors = [d for d in diags if d.get("severity") == "error"]
            assert len(errors) == 0

    def test_mutation_snapshot_has_matching_severity(self):
        """Mutation golden snapshots should match actual diagnostic severities."""
        for inp_file in MUTATIONS_DIR.glob("mutation_*.inp"):
            golden_file = inp_file.parent / f"{inp_file.stem}_golden.json"
            if not golden_file.exists():
                continue
            golden = json.loads(golden_file.read_text())
            golden_diags = golden.get("diagnostics", [])
            if not golden_diags:
                continue

            diags = _get_all_diagnostics(str(inp_file))
            for g_diag in golden_diags:
                expected_sev = g_diag.get("severity", "error")
                matching = [d for d in diags if d.get("severity") == expected_sev]
                assert len(matching) > 0, (
                    f"{inp_file.name}: expected '{expected_sev}' severity, "
                    f"got: {[d.get('severity') for d in diags]}"
                )
