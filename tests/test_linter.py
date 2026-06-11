"""Tests for CP2K linter module."""


import pytest

from . import TEST_DIR

linter = pytest.importorskip("cp2k_input_tools.linter")

_get_all_schema_keywords = linter._get_all_schema_keywords
_get_all_schema_sections = linter._get_all_schema_sections
lint = linter.lint
lint_config_smells = linter.lint_config_smells
lint_duplicates = linter.lint_duplicates
lint_invalid_nesting = linter.lint_invalid_nesting
lint_keywords_misspelled = linter.lint_keywords_misspelled


class TestSchemaExtraction:
    """Tests for schema data extraction."""

    def test_get_schema_keywords(self):
        """Should extract keywords from XML schema."""
        keywords = _get_all_schema_keywords()
        assert len(keywords) > 50
        assert "PROJECT" in keywords or "METHOD" in keywords
        assert "COORD_FILE" in keywords

    def test_get_schema_sections(self):
        """Should extract section names from XML schema."""
        sections = _get_all_schema_sections()
        assert len(sections) > 50
        assert "GLOBAL" in sections
        assert "FORCE_EVAL" in sections
        assert "DFT" in sections


class TestKeywordMisspelling:
    """Tests for keyword misspelling detection."""

    def test_no_misspellings(self):
        """Valid input should not trigger misspelling warnings."""
        text = """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL"""
        diagnostics = lint_keywords_misspelled(text, {"PROJECT", "RUN_TYPE", "ENERGY"})
        assert len(diagnostics) == 0

    def test_detect_misspelling(self):
        """Should detect misspelled keywords and suggest corrections."""
        text = """&GLOBAL
  PROJCT test
  RUN_TYPE ENERGY
&END GLOBAL"""
        diagnostics = lint_keywords_misspelled(text, {"PROJECT", "RUN_TYPE", "ENERGY"})
        assert len(diagnostics) == 1
        assert "PROJCT" in diagnostics[0].message
        assert "PROJECT" in diagnostics[0].message

    def test_multiple_misspellings(self):
        """Should detect multiple misspelled keywords."""
        text = """&GLOBAL
  PROJCT test
  RUN_TYP ENERGY
&END GLOBAL"""
        diagnostics = lint_keywords_misspelled(text, {"PROJECT", "RUN_TYPE", "ENERGY"})
        assert len(diagnostics) >= 2


class TestInvalidNesting:
    """Tests for invalid section nesting detection."""

    def test_valid_nesting(self):
        """Valid nesting should not trigger errors."""
        text = """&FORCE_EVAL
  &DFT
    &SCF
    &END SCF
  &END DFT
&END FORCE_EVAL"""
        diagnostics = lint_invalid_nesting(text, {"FORCE_EVAL", "DFT", "SCF"})
        assert len(diagnostics) == 0

    def test_invalid_nesting_dft_in_global(self):
        """DFT should not be nested under GLOBAL."""
        text = """&GLOBAL
  &DFT
  &END DFT
&END GLOBAL"""
        diagnostics = lint_invalid_nesting(text, {"GLOBAL", "DFT"})
        assert len(diagnostics) == 1
        assert "DFT" in diagnostics[0].message
        assert "GLOBAL" in diagnostics[0].message


class TestDuplicates:
    """Tests for duplicate keyword/section detection."""

    def test_no_duplicates(self):
        """Input without duplicates should not trigger warnings."""
        text = """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL"""
        diagnostics = lint_duplicates(text)
        assert len(diagnostics) == 0

    def test_duplicate_keyword(self):
        """Should detect duplicate keywords."""
        text = """&GLOBAL
  PROJECT test
  PROJECT test2
  RUN_TYPE ENERGY
&END GLOBAL"""
        diagnostics = lint_duplicates(text)
        assert len(diagnostics) >= 1
        assert "PROJECT" in diagnostics[0].message

    def test_duplicate_section(self):
        """Should detect duplicate sections."""
        text = """&FORCE_EVAL
  &SUBSYS
    &COORD
    &END COORD
    &COORD
    &END COORD
  &END SUBSYS
&END FORCE_EVAL"""
        diagnostics = lint_duplicates(text)
        assert len(diagnostics) >= 1
        assert "COORD" in diagnostics[0].message

    def test_repeated_kind_sections_are_allowed(self):
        """KIND sections can repeat under SUBSYS."""
        text = """&FORCE_EVAL
  &SUBSYS
    &KIND O
    &END KIND
    &KIND H
    &END KIND
  &END SUBSYS
&END FORCE_EVAL"""
        diagnostics = lint_duplicates(text)
        assert not any(d.code == "lint/duplicate-section" for d in diagnostics)

    def test_repeated_coord_labels_are_data_records(self):
        """Repeated atom labels in COORD are coordinate rows, not duplicate keywords."""
        text = """&FORCE_EVAL
  &SUBSYS
    &COORD
      H 0.0 0.0 0.0
      H 0.0 0.0 1.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL"""
        diagnostics = lint_duplicates(text)
        assert not any(d.code == "lint/duplicate-keyword" for d in diagnostics)


class TestConfigSmells:
    """Tests for configuration smell detection."""

    def test_low_cutoff(self):
        """Should warn about very low cutoff."""
        text = """&DFT
  &MGRID
    CUTOFF 50
  &END MGRID
&END DFT"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/low-cutoff" for d in diagnostics)

    def test_ok_cutoff(self):
        """Should not warn about reasonable cutoff."""
        text = """&DFT
  &MGRID
    CUTOFF 400
  &END MGRID
&END DFT"""
        diagnostics = lint_config_smells(text)
        assert not any(d.code == "lint/low-cutoff" for d in diagnostics)

    def test_low_rel_cutoff(self):
        """Should warn about very low rel_cutoff."""
        text = """&DFT
  &MGRID
    REL_CUTOFF 10
  &END MGRID
&END DFT"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/low-rel-cutoff" for d in diagnostics)

    def test_few_scf_iterations(self):
        """Should warn about very few SCF iterations."""
        text = """&DFT
  &SCF
    MAX_SCF 5
  &END SCF
&END DFT"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/max-scf-too-low" for d in diagnostics)

    def test_loose_scf_eps(self):
        """Should warn about loose SCF convergence."""
        text = """&DFT
  &SCF
    EPS_SCF 1.0E-3
  &END SCF
&END DFT"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/loose-scf-eps" for d in diagnostics)

    def test_short_timestep(self):
        """Should warn about suspiciously short timestep."""
        text = """&MOTION
  &MD
    TIMESTEP 0.001
  &END MD
&END MOTION"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/short-timestep" for d in diagnostics)

    def test_long_timestep(self):
        """Should warn about suspiciously long timestep."""
        text = """&MOTION
  &MD
    TIMESTEP 10.0
  &END MD
&END MOTION"""
        diagnostics = lint_config_smells(text)
        assert any(d.code == "lint/long-timestep" for d in diagnostics)


class TestFullLintPipeline:
    """Integration tests for the full lint pipeline."""

    def test_valid_input_no_warnings(self):
        """A well-formed input should produce no lint warnings."""
        testpath = TEST_DIR / "inputs" / "test01.inp"
        with open(testpath) as f:
            text = f.read()
        diagnostics = lint(text)
        assert not any(d.code == "lint/misspelled-keyword" for d in diagnostics)
        # May have some warnings but no errors from lint rules
        lint_errors = [d for d in diagnostics if d.source == "cp2k-lint" and d.severity == "error"]
        assert len(lint_errors) == 0

    def test_config_smells_file(self):
        """Should detect config smells in test fixture."""
        testpath = TEST_DIR / "inputs" / "lint_config_smells.inp"
        with open(testpath) as f:
            text = f.read()
        diagnostics = lint(text)
        lint_warnings = [d for d in diagnostics if d.source == "cp2k-lint" and d.severity == "warning"]
        assert len(lint_warnings) >= 3  # low cutoff, low rel_cutoff, few scf, loose eps

    def test_duplicates_file(self):
        """Should detect duplicates in test fixture."""
        testpath = TEST_DIR / "inputs" / "lint_duplicates.inp"
        with open(testpath) as f:
            text = f.read()
        diagnostics = lint(text)
        lint_warnings = [d for d in diagnostics if d.source == "cp2k-lint"]
        assert len(lint_warnings) >= 2  # METHOD duplicate, MAX_SCF duplicate

    def test_misspelled_file(self):
        """Should detect misspellings in test fixture."""
        testpath = TEST_DIR / "inputs" / "lint_misspelled.inp"
        with open(testpath) as f:
            text = f.read()
        diagnostics = lint(text)
        misspelling_warnings = [d for d in diagnostics if d.code == "lint/misspelled-keyword"]
        assert len(misspelling_warnings) >= 2

    def test_invalid_nesting_file(self):
        """Should detect invalid nesting in test fixture."""
        testpath = TEST_DIR / "inputs" / "lint_invalid_nesting.inp"
        with open(testpath) as f:
            text = f.read()
        diagnostics = lint(text)
        nesting_errors = [d for d in diagnostics if d.code == "lint/invalid-nesting"]
        assert len(nesting_errors) >= 1
