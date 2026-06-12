"""Tests for CP2K log parser module."""

from pathlib import Path

import pytest

from . import TEST_DIR
from cp2k_input_tools.log_parser import (
    parse_log_content,
    parse_log_file,
    SCFConvergenceParser,
    LogDiagnostic,
)


class TestSCFConvergenceParser:
    """Tests for SCF convergence detection."""

    def test_converged_scf_produces_no_diagnostics(self):
        """Converged SCF should not produce diagnostics."""
        content = """
 SCF| SCF run converged in 12 iterations
 SCF| Final energy: -76.250123 Hartree
"""
        parser = SCFConvergenceParser()
        diagnostics = parser.parse(content)
        assert len(diagnostics) == 0

    def test_not_converged_scf_produces_error(self):
        """Non-converged SCF should produce error diagnostic."""
        content = """
 SCF| WARNING: SCF run NOT converged
 SCF| Maximum number of SCF iterations reached without convergence.
"""
        parser = SCFConvergenceParser()
        diagnostics = parser.parse(content)
        assert len(diagnostics) == 1
        assert diagnostics[0].rule_id == "cp2k.log.scf_not_converged"
        assert diagnostics[0].severity == "error"

    def test_max_scf_exceeded_produces_error(self):
        """Maximum SCF exceeded message should produce error."""
        content = """
 SCF| WARNING: SCF run not converged after maximum number of iterations
"""
        parser = SCFConvergenceParser()
        diagnostics = parser.parse(content)
        assert len(diagnostics) == 1
        assert diagnostics[0].rule_id == "cp2k.log.scf_not_converged"
        assert "maximum" in diagnostics[0].message.lower()

    def test_diagnostic_has_hint(self):
        """Non-converged diagnostic should include hint."""
        content = """
 SCF| WARNING: SCF run NOT converged
"""
        parser = SCFConvergenceParser()
        diagnostics = parser.parse(content)
        assert len(diagnostics) == 1
        assert diagnostics[0].hint is not None
        assert "MAX_SCF" in diagnostics[0].hint or "EPS_SCF" in diagnostics[0].hint


class TestLogFileParsing:
    """Tests for parsing actual log files."""

    def test_parse_converged_log_file(self):
        """Should parse converged log file without errors."""
        testpath = TEST_DIR / "fixtures" / "logs" / "scf_converged.out"
        if not testpath.exists():
            pytest.skip(f"Fixture not found: {testpath}")

        diagnostics = parse_log_file(str(testpath))
        # Should not have SCF non-convergence error
        scf_errors = [d for d in diagnostics if d.rule_id == "cp2k.log.scf_not_converged"]
        assert len(scf_errors) == 0

    def test_parse_not_converged_log_file(self):
        """Should detect SCF non-convergence in log file."""
        testpath = TEST_DIR / "fixtures" / "logs" / "scf_not_converged.out"
        if not testpath.exists():
            pytest.skip(f"Fixture not found: {testpath}")

        diagnostics = parse_log_file(str(testpath))
        scf_errors = [d for d in diagnostics if d.rule_id == "cp2k.log.scf_not_converged"]
        assert len(scf_errors) >= 1

    def test_parse_nonexistent_file(self):
        """Should handle nonexistent file gracefully."""
        diagnostics = parse_log_file("nonexistent.log")
        assert diagnostics == []

    def test_parse_empty_content(self):
        """Should handle empty content without errors."""
        diagnostics = parse_log_content("")
        assert diagnostics == []

    def test_parse_content_without_scf(self):
        """Should handle content without SCF information."""
        content = """
 Some other log output
 Without SCF information
"""
        diagnostics = parse_log_content(content)
        assert diagnostics == []
