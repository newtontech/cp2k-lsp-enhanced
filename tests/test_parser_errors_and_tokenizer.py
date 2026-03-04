"""Comprehensive tests for parser errors and related modules."""

import pytest

from cp2k_input_tools.parser_errors import (
    InvalidNameError,
    InvalidParameterError,
    InvalidSectionError,
    NameRepetitionError,
    ParserError,
    PreprocessorError,
    SectionMismatchError,
)
from cp2k_input_tools.tokenizer import (
    COMMENT_CHARS,
    Context,
    CP2KInputTokenizer,
    InvalidTokenCharError,
    Token,
    TokenizerError,
    UnterminatedStringError,
    tokenize,
)


class TestParserErrorClasses:
    """Tests for parser error classes."""

    def test_parser_error_base(self):
        """Test ParserError base class."""
        error = ParserError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_invalid_name_error(self):
        """Test InvalidNameError."""
        error = InvalidNameError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)

    def test_invalid_section_error(self):
        """Test InvalidSectionError."""
        error = InvalidSectionError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)

    def test_invalid_parameter_error(self):
        """Test InvalidParameterError."""
        error = InvalidParameterError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)

    def test_section_mismatch_error(self):
        """Test SectionMismatchError."""
        error = SectionMismatchError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)

    def test_name_repetition_error(self):
        """Test NameRepetitionError."""
        error = NameRepetitionError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)

    def test_preprocessor_error(self):
        """Test PreprocessorError."""
        error = PreprocessorError("test error")
        assert str(error) == "test error"
        assert isinstance(error, ParserError)


class TestContext:
    """Tests for Context dataclass."""

    def test_context_default_creation(self):
        """Test creating Context with defaults."""
        ctx = Context()
        assert ctx.colnr is None
        assert ctx.colnrs == []
        assert ctx.ref_colnr is None
        assert ctx.line is None
        assert ctx.ref_line is None
        assert ctx.filename is None
        assert ctx.section is None

    def test_context_with_values(self):
        """Test creating Context with values."""
        ctx = Context(
            colnr=5,
            colnrs=[1, 2, 3],
            ref_colnr=10,
            line="test line",
            ref_line="ref line",
            filename="test.inp",
            section="GLOBAL"
        )
        assert ctx.colnr == 5
        assert ctx.colnrs == [1, 2, 3]
        assert ctx.ref_colnr == 10
        assert ctx.line == "test line"
        assert ctx.ref_line == "ref line"
        assert ctx.filename == "test.inp"
        assert ctx.section == "GLOBAL"


class TestTokenizerErrorClasses:
    """Tests for tokenizer error classes."""

    def test_tokenizer_error_base(self):
        """Test TokenizerError base class."""
        ctx = Context()
        error = TokenizerError("test error", ctx)
        assert "test error" in str(error)
        assert isinstance(error, Exception)

    def test_unterminated_string_error(self):
        """Test UnterminatedStringError."""
        ctx = Context()
        error = UnterminatedStringError("unterminated", ctx)
        assert isinstance(error, TokenizerError)

    def test_invalid_token_char_error(self):
        """Test InvalidTokenCharError."""
        ctx = Context()
        error = InvalidTokenCharError("invalid char", ctx)
        assert isinstance(error, TokenizerError)


class TestCommentChars:
    """Tests for COMMENT_CHARS constant."""

    def test_comment_chars_content(self):
        """Test COMMENT_CHARS contains expected values."""
        assert "!" in COMMENT_CHARS
        assert "#" in COMMENT_CHARS
        assert len(COMMENT_CHARS) == 2


class TestToken:
    """Tests for Token dataclass."""

    def test_token_creation(self):
        """Test creating Token."""
        ctx = Context()
        token = Token(string="test", ctx=ctx)
        assert token.string == "test"
        assert token.ctx is ctx


class TestCP2KInputTokenizer:
    """Tests for CP2KInputTokenizer."""

    def test_tokenizer_init(self):
        """Test tokenizer initialization."""
        tokenizer = CP2KInputTokenizer()
        assert hasattr(tokenizer, '_tracking_quote_char')
        assert hasattr(tokenizer, '_current_token_start')
        assert hasattr(tokenizer, '_tokens')

    def test_tokenizer_tokens_property(self):
        """Test tokenizer tokens property."""
        tokenizer = CP2KInputTokenizer()
        # Initially empty
        assert tokenizer.tokens == []

    def test_begin_basic_token(self):
        """Test begin_basic_token method."""
        tokenizer = CP2KInputTokenizer()
        tokenizer.begin_basic_token(None, 5)
        assert tokenizer._current_token_start == 5

    def test_end_basic_token(self):
        """Test end_basic_token method."""
        tokenizer = CP2KInputTokenizer()
        tokenizer._current_token_start = 0
        tokenizer.end_basic_token("hello", 5)
        assert tokenizer.tokens == [(0, 5)]

    def test_begin_string_token(self):
        """Test begin_string_token method."""
        tokenizer = CP2KInputTokenizer()
        tokenizer.begin_string_token('"test"', 0)
        assert tokenizer._current_token_start == 0
        assert tokenizer._tracking_quote_char == '"'

    def test_is_not_escaped_no_escape(self):
        """Test is_not_escaped without escape character."""
        tokenizer = CP2KInputTokenizer()
        result = tokenizer.is_not_escaped("test", 0)
        assert result is True

    def test_is_not_escaped_with_escape(self):
        """Test is_not_escaped with escape character."""
        tokenizer = CP2KInputTokenizer()
        result = tokenizer.is_not_escaped('\\"', 1)
        assert result is False

    def test_is_matching_quote_matching(self):
        """Test is_matching_quote with matching quote."""
        tokenizer = CP2KInputTokenizer()
        tokenizer._tracking_quote_char = '"'
        result = tokenizer.is_matching_quote('"test"', 5)
        assert result is True

    def test_is_matching_quote_not_matching(self):
        """Test is_matching_quote with non-matching quote."""
        tokenizer = CP2KInputTokenizer()
        tokenizer._tracking_quote_char = '"'
        result = tokenizer.is_matching_quote("'test'", 5)
        assert result is False


class TestTokenizeFunction:
    """Tests for tokenize function."""

    def test_tokenize_empty(self):
        """Test tokenizing empty string."""
        result = tokenize("")
        assert result == ()

    def test_tokenize_simple(self):
        """Test tokenizing simple string."""
        result = tokenize("hello world")
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == "world"

    def test_tokenize_with_quotes(self):
        """Test tokenizing string with quotes."""
        result = tokenize('hello "world"')
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == '"world"'

    def test_tokenize_with_comment(self):
        """Test tokenizing string with comment."""
        result = tokenize("hello world ! comment")
        assert len(result) == 3
        assert result[0] == "hello"
        assert result[1] == "world"
        assert result[2].startswith("!")

    def test_tokenize_with_hash_comment(self):
        """Test tokenizing string with hash comment."""
        result = tokenize("hello world # comment")
        assert len(result) == 3
        assert result[2].startswith("#")

    def test_tokenize_multiple_spaces(self):
        """Test tokenizing with multiple spaces."""
        result = tokenize("hello    world")
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == "world"

    def test_tokenize_with_tabs(self):
        """Test tokenizing with tabs."""
        result = tokenize("hello\tworld")
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == "world"

    def test_tokenize_single_quotes(self):
        """Test tokenizing with single quotes."""
        result = tokenize("'single quoted'")
        assert len(result) == 1
        assert result[0] == "'single quoted'"

    def test_tokenize_mixed_quotes(self):
        """Test tokenizing with mixed quotes."""
        result = tokenize('"double" \'single\'')
        assert len(result) == 2

    def test_tokenize_just_comment(self):
        """Test tokenizing just a comment."""
        result = tokenize("! just a comment")
        assert len(result) == 1
        assert result[0].startswith("!")

    def test_tokenize_only_whitespace(self):
        """Test tokenizing only whitespace."""
        result = tokenize("   \t   ")
        assert result == ()
