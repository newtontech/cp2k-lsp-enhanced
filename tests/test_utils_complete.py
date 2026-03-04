"""Comprehensive unit tests for utils module."""

import pytest
from io import StringIO
from cp2k_input_tools.utils import (
    NUM2SYM,
    SYM2NUM,
    EOF_MARKER_LINE,
    EMPTY_LINE_MATCH,
    BLOCK_MATCH,
    chained_exception,
    MulitpleValueErrorsException,
    DatafileIterMixin,
    FromDictMixin,
    dformat,
)
from decimal import Decimal


class TestSymbols:
    """Tests for symbol/number conversion tables."""

    def test_num2sym_length(self):
        """Test NUM2SYM has correct length."""
        assert len(NUM2SYM) == 119  # 0-118, with 0 being empty

    def test_num2sym_first_element(self):
        """Test first element is Hydrogen."""
        assert NUM2SYM[1] == "H"

    def test_num2sym_common_elements(self):
        """Test common elements."""
        assert NUM2SYM[6] == "C"
        assert NUM2SYM[7] == "N"
        assert NUM2SYM[8] == "O"
        assert NUM2SYM[79] == "Au"

    def test_sym2num_inverse(self):
        """Test SYM2NUM is inverse of NUM2SYM."""
        for Z, sym in enumerate(NUM2SYM[1:], start=1):
            assert SYM2NUM[sym] == Z


class TestConstants:
    """Tests for module constants."""

    def test_eof_marker(self):
        """Test EOF_MARKER_LINE constant."""
        assert EOF_MARKER_LINE == "Eof marker"

    def test_empty_line_match(self):
        """Test EMPTY_LINE_MATCH regex."""
        assert EMPTY_LINE_MATCH.match("")
        assert EMPTY_LINE_MATCH.match("   ")
        assert EMPTY_LINE_MATCH.match("# comment")
        assert EMPTY_LINE_MATCH.match("  # comment")
        assert not EMPTY_LINE_MATCH.match("H basis")

    def test_block_match(self):
        """Test BLOCK_MATCH regex."""
        match = BLOCK_MATCH.match("H DZVP-MOLOPT-GTH")
        assert match is not None
        assert match.group("element") == "H"
        assert match.group("family") == "DZVP-MOLOPT-GTH"


class TestChainedException:
    """Tests for chained_exception function."""

    def test_chained_exception(self):
        """Test chained exception creation."""
        original = ValueError("original error")
        chained = chained_exception(RuntimeError, "new error", original)
        
        assert isinstance(chained, RuntimeError)
        assert str(chained) == "new error"
        assert chained.__cause__ is original


class TestMultipleValueErrorsException:
    """Tests for MulitpleValueErrorsException."""

    def test_exception_is_value_error(self):
        """Test that it's a ValueError subclass."""
        assert issubclass(MulitpleValueErrorsException, ValueError)

    def test_exception_with_errors(self):
        """Test exception with error list."""
        errors = [ValueError("error1"), ValueError("error2")]
        exc = MulitpleValueErrorsException(errors)
        assert isinstance(exc, ValueError)


class TestDatafileIterMixin:
    """Tests for DatafileIterMixin."""

    class DummyData(DatafileIterMixin):
        def __init__(self, element, family):
            self.element = element
            self.family = family

        @classmethod
        def from_lines(cls, lines):
            match = BLOCK_MATCH.match(lines[0])
            return cls(match.group("element"), match.group("family"))

        @staticmethod
        def is_block_start(line):
            return BLOCK_MATCH.match(line) is not None

    def test_datafile_iter_simple(self):
        """Test datafile_iter with simple input."""
        content = [
            "H DZVP-MOLOPT-GTH",
            "  1  2  3",
            "",
            "O DZVP-MOLOPT-GTH",
            "  4  5  6",
        ]
        
        results = list(self.DummyData.datafile_iter(content))
        assert len(results) == 2
        assert results[0].element == "H"
        assert results[1].element == "O"

    def test_datafile_iter_from_string(self):
        """Test datafile_iter with string input."""
        content = "H DZVP-MOLOPT-GTH\n  1  2  3\n\nO DZVP-MOLOPT-GTH\n  4  5  6"
        
        results = list(self.DummyData.datafile_iter(content))
        assert len(results) == 2

    def test_datafile_iter_emit_comments(self):
        """Test datafile_iter with emit_comments."""
        content = [
            "H DZVP-MOLOPT-GTH",
            "  1  2  3",
            "",
            "# comment",
            "O DZVP-MOLOPT-GTH",
            "  4  5  6",
        ]
        
        results = list(self.DummyData.datafile_iter(content, emit_comments=True))
        # Should include comments
        comment_results = [r for r in results if isinstance(r, str)]
        assert len(comment_results) >= 1

    def test_is_block_start(self):
        """Test is_block_start static method."""
        assert self.DummyData.is_block_start("H DZVP-MOLOPT-GTH")
        assert not self.DummyData.is_block_start("# comment")
        assert not self.DummyData.is_block_start("")


class TestDformat:
    """Tests for dformat function."""

    def test_dformat_integer(self):
        """Test dformat with integer."""
        val = Decimal("42")
        result = dformat(val, 5, 10)
        assert "42" in result

    def test_dformat_decimal(self):
        """Test dformat with decimal."""
        val = Decimal("3.14159")
        result = dformat(val, 3, 10)
        assert isinstance(result, str)
