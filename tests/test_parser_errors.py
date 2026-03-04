"""Unit tests for parser_errors module."""

import pytest
from cp2k_input_tools.parser_errors import (
    ErrorContext,
    InvalidNameError,
    InvalidParameterError,
    InvalidSectionError,
    NameRepetitionError,
    NestedSectionError,
    ParserError,
    SectionMismatchError,
)


class TestErrorContext:
    """Tests for ErrorContext dataclass."""

    def test_error_context_default(self):
        """Test ErrorContext with default values."""
        ctx = ErrorContext()
        assert ctx.line is None
        assert ctx.linenr is None
        assert ctx.colnrs == []
        assert ctx.filename is None
        assert ctx.section is None
        assert ctx.section_stack == []
        assert ctx.suggestion is None

    def test_error_context_with_values(self):
        """Test ErrorContext with all values."""
        ctx = ErrorContext(
            line="TEST_LINE",
            linenr=42,
            colnrs=[1, 2, 3],
            filename="test.inp",
            section="GLOBAL",
            section_stack=["FORCE_EVAL", "DFT"],
            suggestion="Did you mean...?"
        )
        assert ctx.line == "TEST_LINE"
        assert ctx.linenr == 42
        assert ctx.colnrs == [1, 2, 3]
        assert ctx.filename == "test.inp"
        assert ctx.section == "GLOBAL"
        assert ctx.section_stack == ["FORCE_EVAL", "DFT"]
        assert ctx.suggestion == "Did you mean...?"


class TestParserError:
    """Tests for ParserError base class."""

    def test_parser_error_basic(self):
        """Test basic ParserError creation."""
        error = ParserError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_parser_error_with_context(self):
        """Test ParserError with context."""
        ctx = ErrorContext(line="TEST", linenr=10)
        error = ParserError("Test error", ctx)
        assert error.context == ctx
        assert error.message == "Test error"


class TestInvalidNameError:
    """Tests for InvalidNameError."""

    def test_invalid_name_error_basic(self):
        """Test InvalidNameError creation."""
        error = InvalidNameError("Invalid name 'FOO'")
        assert error.message == "Invalid name 'FOO'"
        assert str(error) == "Invalid name 'FOO'"

    def test_invalid_name_error_with_context(self):
        """Test InvalidNameError with context."""
        ctx = ErrorContext(
            line="FOO_BAR = 1",
            linenr=5,
            suggestion="Did you mean: FOO?"
        )
        error = InvalidNameError("Invalid name 'FOO_BAR'", ctx)
        assert error.context.suggestion == "Did you mean: FOO?"


class TestInvalidSectionError:
    """Tests for InvalidSectionError."""

    def test_invalid_section_error_basic(self):
        """Test InvalidSectionError creation."""
        error = InvalidSectionError("Invalid section '&FOO'")
        assert error.message == "Invalid section '&FOO'"
        assert str(error) == "Invalid section '&FOO'"

    def test_invalid_section_error_with_suggestion(self):
        """Test InvalidSectionError with suggestion."""
        ctx = ErrorContext(
            line="&FOO",
            linenr=1,
            section_stack=["GLOBAL"],
            suggestion="Did you mean: FORCE_EVAL?"
        )
        error = InvalidSectionError("Invalid section '&FOO'", ctx)
        assert error.context.suggestion is not None


class TestInvalidParameterError:
    """Tests for InvalidParameterError."""

    def test_invalid_parameter_error_basic(self):
        """Test InvalidParameterError creation."""
        error = InvalidParameterError("Invalid parameter value")
        assert error.message == "Invalid parameter value"

    def test_invalid_parameter_error_with_context(self):
        """Test InvalidParameterError with context."""
        ctx = ErrorContext(
            line="PROJECT_NAME",
            linenr=3,
            section="GLOBAL"
        )
        error = InvalidParameterError("Expected string value", ctx)
        assert error.context.section == "GLOBAL"


class TestSectionMismatchError:
    """Tests for SectionMismatchError."""

    def test_section_mismatch_error_basic(self):
        """Test SectionMismatchError creation."""
        error = SectionMismatchError("Section mismatch")
        assert error.message == "Section mismatch"

    def test_section_mismatch_error_unclosed(self):
        """Test SectionMismatchError for unclosed section."""
        ctx = ErrorContext(
            line="&GLOBAL",
            linenr=1,
            suggestion="Add '&END GLOBAL' to close the section"
        )
        error = SectionMismatchError("section 'GLOBAL' not closed", ctx)
        assert "not closed" in error.message
        assert error.context.suggestion is not None


class TestNameRepetitionError:
    """Tests for NameRepetitionError."""

    def test_name_repetition_error_basic(self):
        """Test NameRepetitionError creation."""
        error = NameRepetitionError("Keyword 'FOO' mentioned twice")
        assert error.message == "Keyword 'FOO' mentioned twice"

    def test_name_repetition_error_duplicate_keyword(self):
        """Test NameRepetitionError for duplicate keyword."""
        ctx = ErrorContext(
            line="PROJECT_NAME test1",
            linenr=5,
            section="GLOBAL",
            section_stack=["GLOBAL"]
        )
        error = NameRepetitionError(
            "the keyword 'PROJECT_NAME' can only be mentioned once",
            ctx
        )
        assert "PROJECT_NAME" in error.message
        assert error.context.section == "GLOBAL"


class TestNestedSectionError:
    """Tests for NestedSectionError."""

    def test_nested_section_error_basic(self):
        """Test NestedSectionError creation."""
        error = NestedSectionError("Nested section error")
        assert error.message == "Nested section error"


class TestErrorChaining:
    """Tests for error chaining and exception behavior."""

    def test_error_is_exception(self):
        """Test that all errors are proper exceptions."""
        errors = [
            ParserError("test"),
            InvalidNameError("test"),
            InvalidSectionError("test"),
            InvalidParameterError("test"),
            SectionMismatchError("test"),
            NameRepetitionError("test"),
            NestedSectionError("test"),
        ]
        for error in errors:
            assert isinstance(error, Exception)

    def test_error_can_be_caught(self):
        """Test that errors can be caught as ParserError."""
        try:
            raise InvalidNameError("test")
        except ParserError as e:
            assert "test" in str(e)

    def test_error_attributes(self):
        """Test that all errors have required attributes."""
        error = InvalidNameError("message", ErrorContext())
        assert hasattr(error, 'message')
        assert hasattr(error, 'context')
