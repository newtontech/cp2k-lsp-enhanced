"""Log parser regression tests (issue #71).

Tests the CP2K log parser against fixture log files covering:
- Converged SCF (no diagnostics expected)
- Non-converged SCF (error diagnostics expected)
- Max SCF exceeded (error diagnostics expected)
- Mixed output (convergence + non-convergence)
- Empty file
- Nonexistent file

Run: pytest tests/regression/test_log_parser_regression.py -v
"""

from pathlib import Path

import pytest

from cp2k_input_tools.log_parser import (
    LogDiagnostic,
    SCFConvergenceParser,
    parse_log_content,
    parse_log_file,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
LOGS_DIR = FIXTURES_DIR / "logs"


class TestLogParserConverged:
    """Converged SCF logs should produce no diagnostics."""

    def test_converged_file_no_diagnostics(self):
        path = LOGS_DIR / "scf_converged.out"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        diags = parse_log_file(str(path))
        scf_errors = [d for d in diags if d.rule_id == "cp2k.log.scf_not_converged"]
        assert len(scf_errors) == 0, f"Converged SCF should have no SCF errors: {scf_errors}"

    def test_converged_content_inline(self):
        content = "SCF| SCF run converged in 12 iterations\n"
        diags = parse_log_content(content)
        assert len(diags) == 0


class TestLogParserNotConverged:
    """Non-converged SCF logs should produce error diagnostics."""

    def test_not_converged_file(self):
        path = LOGS_DIR / "scf_not_converged.out"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        diags = parse_log_file(str(path))
        scf_errors = [d for d in diags if d.rule_id == "cp2k.log.scf_not_converged"]
        assert len(scf_errors) >= 1, "Non-converged SCF should produce at least one error"

    def test_not_converged_inline(self):
        content = "SCF| WARNING: SCF run NOT converged\n"
        diags = parse_log_content(content)
        assert len(diags) == 1
        assert diags[0].severity == "error"
        assert diags[0].rule_id == "cp2k.log.scf_not_converged"
        assert diags[0].hint is not None

    def test_max_scf_exceeded_file(self):
        path = LOGS_DIR / "scf_max_exceeded.out"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        diags = parse_log_file(str(path))
        assert len(diags) >= 1, "Max SCF exceeded should produce error"
        assert diags[0].rule_id == "cp2k.log.scf_not_converged"
        assert "maximum" in diags[0].message.lower()

    def test_max_scf_exceeded_inline(self):
        content = "WARNING: SCF run not converged after maximum number of iterations\n"
        diags = parse_log_content(content)
        assert len(diags) == 1
        assert "maximum" in diags[0].message.lower()


class TestLogParserMixedOutput:
    """Logs with both converged and non-converged SCF runs."""

    def test_mixed_output_file(self):
        path = LOGS_DIR / "mixed_output.out"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        diags = parse_log_file(str(path))
        # Should detect the non-converged SCF
        scf_errors = [d for d in diags if d.rule_id == "cp2k.log.scf_not_converged"]
        assert len(scf_errors) >= 1, "Mixed output should flag non-converged SCF"

    def test_multiple_not_converged_inline(self):
        content = (
            "SCF| SCF run NOT converged\n"
            "SCF| SCF run NOT converged\n"
        )
        diags = parse_log_content(content)
        assert len(diags) == 2, "Multiple NOT-converged lines should produce multiple diagnostics"


class TestLogParserEdgeCases:
    """Edge cases for log parsing."""

    def test_empty_file(self):
        path = LOGS_DIR / "empty.out"
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        diags = parse_log_file(str(path))
        assert diags == []

    def test_empty_content(self):
        diags = parse_log_content("")
        assert diags == []

    def test_nonexistent_file(self):
        diags = parse_log_file("/nonexistent/path/file.out")
        assert diags == []

    def test_no_scf_info(self):
        content = "Some other log output\nWithout SCF information\n"
        diags = parse_log_content(content)
        assert diags == []

    def test_case_insensitive_scf(self):
        """SCF patterns should be case-insensitive."""
        content = "scf run not converged\n"
        diags = parse_log_content(content)
        assert len(diags) == 1

    def test_diagnostic_fields_present(self):
        """Each diagnostic should have all required fields."""
        content = "SCF run NOT converged\n"
        diags = parse_log_content(content)
        assert len(diags) == 1
        d = diags[0]
        assert isinstance(d, LogDiagnostic)
        assert d.rule_id is not None
        assert d.message is not None
        assert d.line_number > 0
        assert d.severity in ("error", "warning", "information", "hint")
        assert d.hint is not None

    def test_line_numbers_are_accurate(self):
        """Diagnostic line numbers should match the actual source line."""
        content = (
            "Line 1\n"
            "Line 2\n"
            "SCF run NOT converged\n"
            "Line 4\n"
        )
        diags = parse_log_content(content)
        assert len(diags) == 1
        assert diags[0].line_number == 3


class TestLogParserDeterminism:
    """Log parsing should be deterministic."""

    def test_parse_twice_same_result(self):
        content = "SCF run NOT converged\n"
        diags1 = parse_log_content(content)
        diags2 = parse_log_content(content)
        assert len(diags1) == len(diags2)
        for d1, d2 in zip(diags1, diags2, strict=True):
            assert d1.rule_id == d2.rule_id
            assert d1.message == d2.message
            assert d1.line_number == d2.line_number
            assert d1.severity == d2.severity

    def test_reuse_parser_instance(self):
        """A single parser instance should be reusable across parses."""
        parser = SCFConvergenceParser()
        content1 = "SCF run NOT converged\n"
        content2 = "SCF run converged in 5 iterations\n"
        diags1 = parser.parse(content1)
        assert len(diags1) == 1
        diags2 = parser.parse(content2)
        assert len(diags2) == 0
