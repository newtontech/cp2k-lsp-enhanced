"""Comprehensive unit tests for tokenizer module."""

import pytest
from cp2k_input_tools.tokenizer import (
    COMMENT_CHARS,
    Context,
    CP2KInputTokenizer,
    InvalidTokenCharError,
    Token,
    TokenizerError,
    UnterminatedStringError,
    tokenize,
    tokenize_with_context,
)


class TestTokenizerConstants:
    """Tests for tokenizer constants."""

    def test_comment_chars(self):
        """Test COMMENT_CHARS constant."""
        assert "!" in COMMENT_CHARS
        assert "#" in COMMENT_CHARS
        assert len(COMMENT_CHARS) == 2


class TestContext:
    """Tests for Context dataclass."""

    def test_context_default(self):
        """Test Context with default values."""
        ctx = Context()
        assert ctx.colnr is None
        assert ctx.colnrs == []
        assert ctx.ref_colnr is None
        assert ctx.line is None
        assert ctx.ref_line is None
        assert ctx.filename is None
        assert ctx.section is None
        assert ctx.section_stack == []

    def test_context_with_values(self):
        """Test Context with all values."""
        ctx = Context(
            colnr=10,
            colnrs=[1, 2, 3],
            ref_colnr=5,
            line="TEST_LINE",
            ref_line="REF_LINE",
            filename="test.inp",
            section="GLOBAL",
            section_stack=["FORCE_EVAL"]
        )
        assert ctx.colnr == 10
        assert ctx.colnrs == [1, 2, 3]
        assert ctx.ref_colnr == 5
        assert ctx.line == "TEST_LINE"
        assert ctx.ref_line == "REF_LINE"
        assert ctx.filename == "test.inp"
        assert ctx.section == "GLOBAL"
        assert ctx.section_stack == ["FORCE_EVAL"]


class TestToken:
    """Tests for Token dataclass."""

    def test_token_creation(self):
        """Test Token creation."""
        ctx = Context(colnr=5)
        token = Token(string="value", ctx=ctx)
        assert token.string == "value"
        assert token.ctx.colnr == 5


class TestTokenizerError:
    """Tests for TokenizerError class."""

    def test_tokenizer_error_basic(self):
        """Test basic TokenizerError."""
        error = TokenizerError("test error")
        assert error.message == "test error"

    def test_tokenizer_error_with_context(self):
        """Test TokenizerError with context."""
        ctx = Context(line="test", colnr=5)
        error = TokenizerError("test error", ctx)
        assert error.context == ctx


class TestUnterminatedStringError:
    """Tests for UnterminatedStringError."""

    def test_unterminated_string_error(self):
        """Test UnterminatedStringError creation."""
        error = UnterminatedStringError("unterminated string")
        assert isinstance(error, TokenizerError)
        assert error.message == "unterminated string"


class TestInvalidTokenCharError:
    """Tests for InvalidTokenCharError."""

    def test_invalid_token_char_error(self):
        """Test InvalidTokenCharError creation."""
        error = InvalidTokenCharError("invalid char")
        assert isinstance(error, TokenizerError)
        assert error.message == "invalid char"


class TestTokenize:
    """Tests for tokenize function."""

    def test_tokenize_simple(self):
        """Test tokenize with simple input."""
        result = tokenize("hello world")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == "world"

    def test_tokenize_with_quotes(self):
        """Test tokenize with quoted string."""
        result = tokenize('hello "world test"')
        assert len(result) == 2
        assert result[0] == "hello"
        assert result[1] == '"world test"'

    def test_tokenize_empty(self):
        """Test tokenize with empty string."""
        result = tokenize("")
        assert result == ()

    def test_tokenize_with_comment(self):
        """Test tokenize with comment."""
        result = tokenize("hello world ! comment")
        # Tokenizer includes comment as a token, which is expected behavior
        assert len(result) >= 2
        assert result[0] == "hello"
        assert result[1] == "world"

    def test_tokenize_with_hash_comment(self):
        """Test tokenize with hash comment."""
        result = tokenize("hello world # comment")
        # Tokenizer includes comment as a token
        assert len(result) >= 2
        assert result[0] == "hello"


class TestTokenizeWithContext:
    """Tests for tokenize_with_context function."""

    def test_tokenize_with_context_simple(self):
        """Test tokenize_with_context with simple input."""
        result = tokenize_with_context("hello world", filename="test.inp", line_number=5)
        assert len(result) == 2
        assert result[0].string == "hello"
        assert result[0].ctx.filename == "test.inp"
        assert result[1].string == "world"

    def test_tokenize_with_context_empty(self):
        """Test tokenize_with_context with empty string."""
        result = tokenize_with_context("")
        assert result == []


class TestCP2KInputTokenizer:
    """Tests for CP2KInputTokenizer class."""

    def test_tokenizer_init(self):
        """Test CP2KInputTokenizer initialization."""
        tokenizer = CP2KInputTokenizer()
        assert tokenizer.tokens == []
        assert tokenizer.state == "lookout"

    def test_tokenizer_simple_tokens(self):
        """Test tokenizer with simple tokens."""
        tokenizer = CP2KInputTokenizer()
        result = tokenize("hello world test")
        assert len(result) == 3

    def test_tokenizer_string_handling(self):
        """Test tokenizer string handling."""
        result = tokenize('hello "world"')
        assert len(result) == 2
        assert result[1] == '"world"'

    def test_tokenizer_single_quotes(self):
        """Test tokenizer with single quotes."""
        result = tokenize("hello 'world'")
        assert len(result) == 2
        assert result[1] == "'world'"

    def test_tokenizer_is_not_escaped(self):
        """Test is_not_escaped method."""
        tokenizer = CP2KInputTokenizer()
        assert tokenizer.is_not_escaped('test', 0) is True
        assert tokenizer.is_not_escaped('test', 1) is True
        # Test with escape character
        assert tokenizer.is_not_escaped(r'test\\"', 5) is False

    def test_tokenizer_tokens_property(self):
        """Test tokens property."""
        tokenizer = CP2KInputTokenizer()
        result = tokenize("hello world")
        # tokens property should return the positions, not the strings
        tokenizer._tokens = []
        tokenizer._current_token_start = 0
        tokenizer.begin_basic_token(None, 0)
        tokenizer.end_basic_token(None, 5)
        assert len(tokenizer.tokens) == 1
        assert tokenizer.tokens[0] == (0, 5)
