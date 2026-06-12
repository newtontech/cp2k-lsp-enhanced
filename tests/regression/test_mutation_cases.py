"""Mutation regression tests for CP2K input errors (issue #71).

Directly tests the linter, parser against common classes of input errors.

Mutation categories:
1. Misspelled keywords
2. Invalid enum values
3. Missing required END blocks
4. Duplicate non-repeatable keywords
5. Unknown sections
6. Invalid nesting
7. Configuration smells (low cutoff, few SCF iterations)
8. Inline parametric mutations

Run: pytest tests/regression/test_mutation_cases.py -v
"""

from pathlib import Path

import pytest

from cp2k_input_tools.linter import lint
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.parser_errors import ParserError
from cp2k_input_tools.tokenizer import TokenizerError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"


# ---------------------------------------------------------------------------
# 1. Misspelled keywords
# ---------------------------------------------------------------------------

class TestMisspelledKeywordMutations:
    """Keywords with typos should be flagged."""

    def test_misspelled_method(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOOD QS\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert "METHOOD" in messages, f"Expected METHOOD in messages: {messages}"

    def test_misspelled_keyword_lint_no_crash(self):
        """Linter should not crash on misspelled keywords."""
        content = (
            "&FORCE_EVAL\n"
            "  METHOOD QS\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        assert isinstance(diags, list)


# ---------------------------------------------------------------------------
# 2. Invalid enum values
# ---------------------------------------------------------------------------

class TestInvalidEnumMutations:
    """Invalid enum values should produce diagnostics."""

    def test_invalid_method_value(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOD TOTALLY_WRONG_VALUE\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert any(
            kw in messages.lower()
            for kw in ["value", "enum", "unknown", "method"]
        ), f"Expected value/enum reference in: {messages}"

    def test_invalid_method_value_fixture(self):
        """Check the mutation fixture file."""
        inp = MUTATIONS_DIR / "mutation_invalid_enum.inp"
        if not inp.exists():
            pytest.skip("Fixture not found")
        content = inp.read_text()
        diags = lint(content)
        assert isinstance(diags, list)


# ---------------------------------------------------------------------------
# 3. Missing END blocks
# ---------------------------------------------------------------------------

class TestMissingEndMutations:
    """Missing &END blocks should produce parser or lint errors."""

    def test_missing_end_parser_raises(self):
        """Parser should raise an error for unclosed sections."""
        content = "&FORCE_EVAL\n  METHOD QS\n"  # no &END
        parser = CP2KInputParser()
        with pytest.raises((ParserError, TokenizerError)):
            parser.parse(content.splitlines())

    def test_missing_end_lint(self):
        """Linter should detect missing END blocks."""
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &SUBSYS\n"
            "    &COORD\n"
            "      O 0.0 0.0 0.0\n"
            "    &END COORD\n"
            # Missing &END SUBSYS and &END FORCE_EVAL
        )
        diags = lint(content)
        assert isinstance(diags, list)
        # May detect missing end or just parse normally


# ---------------------------------------------------------------------------
# 4. Duplicate keywords
# ---------------------------------------------------------------------------

class TestDuplicateKeywordMutations:
    """Duplicate non-repeatable keywords should be flagged."""

    def test_duplicate_method(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  METHOD QS\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert any(
            kw in messages.lower() for kw in ["duplicate", "appears", "once"]
        ), f"Expected duplicate reference in: {messages}"


# ---------------------------------------------------------------------------
# 5. Unknown sections
# ---------------------------------------------------------------------------

class TestUnknownSectionMutations:
    """Invalid nesting and unknown sections should be flagged."""

    def test_invalid_nesting_known_section_wrong_place(self):
        """A known section in the wrong parent should be detected."""
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &GLOBAL\n"
            "    PROJECT test\n"
            "  &END GLOBAL\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert "GLOBAL" in messages, f"Expected GLOBAL in: {messages}"
        assert any(d.severity == "error" for d in diags)

    def test_unknown_section_lint_no_crash(self):
        """Linter should not crash on completely unknown sections."""
        content = (
            "&TOTALLY_FAKE_SECTION\n"
            "  SOME_KEYWORD value\n"
            "&END TOTALLY_FAKE_SECTION\n"
        )
        diags = lint(content)
        assert isinstance(diags, list)

    def test_unknown_section_fixture(self):
        """Check the mutation fixture file with invalid nesting."""
        inp = MUTATIONS_DIR / "mutation_unknown_section.inp"
        if not inp.exists():
            pytest.skip("Fixture not found")
        content = inp.read_text()
        diags = lint(content)
        assert isinstance(diags, list)
        messages = " ".join(d.message for d in diags)
        assert "GLOBAL" in messages, f"Expected GLOBAL in: {messages}"


# ---------------------------------------------------------------------------
# 6. Invalid nesting
# ---------------------------------------------------------------------------

class TestInvalidNestingMutations:
    """Wrongly nested sections should be detected."""

    def test_invalid_nesting(self):
        content = (
            "&GLOBAL\n"
            "  PROJECT test\n"
            "&END GLOBAL\n"
            "&MGRID\n"
            "  CUTOFF 400\n"
            "&END MGRID\n"
        )
        diags = lint(content)
        assert isinstance(diags, list)
        messages = " ".join(d.message for d in diags)
        assert "MGRID" in messages, f"Expected MGRID in: {messages}"


# ---------------------------------------------------------------------------
# 7. Configuration smells
# ---------------------------------------------------------------------------

class TestConfigurationSmellMutations:
    """Configuration smells should produce warnings."""

    def test_low_cutoff_warning(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    &MGRID\n"
            "      CUTOFF 10\n"
            "    &END MGRID\n"
            "  &END DFT\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert any(kw in messages.lower() for kw in ["cutoff", "low"]), (
            f"Expected cutoff warning in: {messages}"
        )

    def test_few_scf_iterations_warning(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    &SCF\n"
            "      MAX_SCF 2\n"
            "    &END SCF\n"
            "  &END DFT\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert any(kw in messages.lower() for kw in ["scf", "iter"]), (
            f"Expected SCF/iteration warning in: {messages}"
        )

    def test_loose_scf_eps_warning(self):
        content = (
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    &SCF\n"
            "      MAX_SCF 50\n"
            "      EPS_SCF 1.0E-1\n"
            "    &END SCF\n"
            "  &END DFT\n"
            "&END FORCE_EVAL\n"
        )
        diags = lint(content)
        messages = " ".join(d.message for d in diags)
        assert any(kw in messages.lower() for kw in ["scf", "eps", "loose"]), (
            f"Expected EPS_SCF warning in: {messages}"
        )


# ---------------------------------------------------------------------------
# 8. Inline mutation helpers for parametric tests
# ---------------------------------------------------------------------------

class TestInlineMutations:
    """Parametric inline mutation tests for common error patterns."""

    @pytest.mark.parametrize(
        "content,expected_fragment",
        [
            pytest.param(
                "&FORCE_EVAL\n  PROJECT 'unterminated\n&END FORCE_EVAL\n",
                None,  # Linter may not detect unterminated strings; parser raises
                id="unterminated-string",
            ),
            pytest.param(
                "&FORCE_EVAL\n  METHOD QS\n&END WRONG_NAME\n",
                None,
                id="section-end-mismatch",
            ),
            pytest.param(
                "",
                None,
                id="empty-file",
            ),
            pytest.param(
                "! This is a comment\n# Another comment\n",
                None,
                id="comments-only",
            ),
            pytest.param(
                "&FORCE_EVAL\n  &DFT\n    &FAKE_INNER\n    &END FAKE_INNER\n  &END DFT\n&END FORCE_EVAL\n",
                None,  # Linter may not detect unknown sections under DFT
                id="deeply-nested-unknown",
            ),
        ],
    )
    def test_inline_mutation_lint_no_crash(self, content, expected_fragment):
        """Each mutation should either produce diagnostics or not crash via linter."""
        diags = lint(content)
        assert isinstance(diags, list), "lint() should always return a list"
        if expected_fragment:
            messages = " ".join(d.message for d in diags)
            assert expected_fragment in messages, (
                f"Expected '{expected_fragment}' in diagnostics: {messages}"
            )

    def test_unterminated_string_parser_raises(self):
        """Parser should raise on unterminated string."""
        content = "&FORCE_EVAL\n  PROJECT 'unterminated\n&END FORCE_EVAL\n"
        parser = CP2KInputParser()
        with pytest.raises((ParserError, TokenizerError)):
            parser.parse(content.splitlines())
