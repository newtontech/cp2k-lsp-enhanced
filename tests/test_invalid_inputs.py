"""Tests for common invalid CP2K input patterns and error handling."""

import pytest

from cp2k_lsp.parser import CP2KParser
from cp2k_lsp.parser.errors import SyntaxError as ParserSyntaxError
from cp2k_lsp.parser.lexer import Lexer, TokenType


def _parse(text: str):
    """Parse text and return (ast, errors)."""
    parser = CP2KParser.parse_text(text)
    return parser.ast, parser.errors


# =============================================================================
# Invalid section patterns
# =============================================================================


class TestInvalidSections:
    """Test handling of invalid section constructs."""

    def test_unclosed_section_at_eof(self):
        """Section without &END at EOF should report error."""
        inp = "&GLOBAL\n  RUN_TYPE ENERGY\n"
        ast, errors = _parse(inp)
        assert len(errors) > 0
        assert any("Unclosed" in str(e) for e in errors)

    def test_unclosed_nested_section(self):
        """Nested section without &END should report error."""
        inp = """\
&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        # Should report unclosed DFT section
        assert len(errors) > 0

    def test_section_end_without_start(self):
        """&END without matching section start should be handled."""
        inp = "&END GLOBAL\n"
        ast, errors = _parse(inp)
        # Should handle gracefully (either error or skip)
        assert ast is not None

    def test_empty_section_name(self):
        """Section with just & should be handled."""
        inp = "&\n&END\n"
        lexer = Lexer(inp)
        tokens = lexer.tokenize()
        # Should not crash
        assert tokens is not None

    def test_section_end_name_mismatch(self):
        """&END with wrong name should report error."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END WRONG
"""
        ast, errors = _parse(inp)
        assert len(errors) > 0
        assert any("mismatch" in str(e).lower() or "Mismatch" in str(e) for e in errors)

    def test_deeply_unclosed_sections(self):
        """Multiple levels of unclosed sections should all be reported."""
        inp = """\
&FORCE_EVAL
  &DFT
    &SCF
"""
        ast, errors = _parse(inp)
        assert len(errors) >= 1  # At least one unclosed section error

    def test_extra_end_after_section(self):
        """Extra &END after properly closed section should be handled."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
&END GLOBAL
"""
        ast, errors = _parse(inp)
        # Should handle gracefully
        assert ast is not None


# =============================================================================
# Invalid keyword patterns
# =============================================================================


class TestInvalidKeywords:
    """Test handling of invalid keyword constructs."""

    def test_keyword_without_section(self):
        """Keyword outside section should produce error."""
        inp = "RUN_TYPE ENERGY\n"
        ast, errors = _parse(inp)
        assert len(errors) > 0
        assert any("Unexpected" in str(e) for e in errors)

    def test_empty_input(self):
        """Empty input should produce empty AST without errors."""
        ast, errors = _parse("")
        assert ast is not None
        assert len(ast.sections) == 0
        assert ast.global_section is None

    def test_only_whitespace(self):
        """Only whitespace should produce empty AST."""
        ast, errors = _parse("   \n  \n  \n")
        assert ast is not None
        assert len(ast.sections) == 0


# =============================================================================
# Unterminated strings
# =============================================================================


class TestUnterminatedStrings:
    """Test handling of unterminated string literals."""

    def test_unterminated_double_quote(self):
        """Unterminated double-quoted string should raise error."""
        inp = """\
&GLOBAL
  PROJECT_NAME "unterminated
&END GLOBAL
"""
        with pytest.raises(ParserSyntaxError, match="Unterminated string"):
            _parse(inp)

    def test_unterminated_single_quote(self):
        """Unterminated single-quoted string should raise error."""
        inp = """\
&GLOBAL
  PROJECT_NAME 'unterminated
&END GLOBAL
"""
        with pytest.raises(ParserSyntaxError, match="Unterminated string"):
            _parse(inp)


# =============================================================================
# Malformed values
# =============================================================================


class TestMalformedValues:
    """Test handling of malformed value constructs."""

    def test_unexpected_char(self):
        """Unexpected characters should be handled gracefully."""
        inp = """\
&GLOBAL
  @@@
&END GLOBAL
"""
        # Should not crash - lexer skips unexpected chars
        lexer = Lexer(inp)
        tokens = lexer.tokenize()
        assert tokens is not None

    def test_special_chars_in_section(self):
        """Special characters in section body should not crash."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
  $variable value
&END GLOBAL
"""
        lexer = Lexer(inp)
        tokens = lexer.tokenize()
        # Should not crash, $ is skipped by lexer
        assert tokens is not None


# =============================================================================
# Parser recovery
# =============================================================================


class TestParserRecovery:
    """Test that parser can recover from errors and continue parsing."""

    def test_multiple_errors_in_sections(self):
        """Multiple errors should all be captured."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END WRONG1

&FORCE_EVAL
  METHOD QS
&END WRONG2
"""
        ast, errors = _parse(inp)
        assert len(errors) == 2
        mismatch_errors = [e for e in errors if "mismatch" in str(e).lower() or "Mismatch" in str(e)]
        assert len(mismatch_errors) == 2

    def test_valid_after_error(self):
        """Valid sections after errors should still be parsed."""
        inp = """\
&GLOBAL
&END WRONG

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert len(errors) > 0  # Error for wrong end name
        # FORCE_EVAL should still be parsed
        assert ast.get_section("FORCE_EVAL") is not None
