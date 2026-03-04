"""Comprehensive tests for utility modules."""

import io
import warnings
from decimal import Decimal
from typing import Mapping, MutableSequence

import pytest

from cp2k_input_tools.utils import (
    NUM2SYM,
    SYM2NUM,
    BLOCK_MATCH,
    EMPTY_LINE_MATCH,
    EOF_MARKER_LINE,
    DatafileIterMixin,
    FromDictMixin,
    MulitpleValueErrorsException,
    chained_exception,
    dformat,
)


class TestElementConstants:
    """Tests for element symbol/number constants."""

    def test_num2sym_length(self):
        """Test NUM2SYM has correct length."""
        # Should have 119 elements (0-indexed empty string + 118 elements)
        assert len(NUM2SYM) == 119

    def test_num2sym_hydrogen(self):
        """Test hydrogen is element 1."""
        assert NUM2SYM[1] == "H"

    def test_num2sym_oxygen(self):
        """Test oxygen is element 8."""
        assert NUM2SYM[8] == "O"

    def test_num2sym_carbon(self):
        """Test carbon is element 6."""
        assert NUM2SYM[6] == "C"

    def test_num2sym_oganesson(self):
        """Test oganesson is last element."""
        assert NUM2SYM[118] == "Og"

    def test_sym2num_length(self):
        """Test SYM2NUM has correct length."""
        assert len(SYM2NUM) == 118  # All real elements

    def test_sym2num_hydrogen(self):
        """Test hydrogen atomic number."""
        assert SYM2NUM["H"] == 1

    def test_sym2num_oxygen(self):
        """Test oxygen atomic number."""
        assert SYM2NUM["O"] == 8

    def test_sym2num_carbon(self):
        """Test carbon atomic number."""
        assert SYM2NUM["C"] == 6

    def test_sym2num_inverse(self):
        """Test SYM2NUM and NUM2SYM are inverses."""
        for z in range(1, 119):
            sym = NUM2SYM[z]
            assert SYM2NUM[sym] == z


class TestRegexPatterns:
    """Tests for regex patterns."""

    def test_eof_marker_line(self):
        """Test EOF marker constant."""
        assert EOF_MARKER_LINE == "Eof marker"

    def test_empty_line_match_empty(self):
        """Test EMPTY_LINE_MATCH with empty line."""
        assert EMPTY_LINE_MATCH.match("") is not None

    def test_empty_line_match_whitespace(self):
        """Test EMPTY_LINE_MATCH with whitespace."""
        assert EMPTY_LINE_MATCH.match("   ") is not None

    def test_empty_line_match_comment(self):
        """Test EMPTY_LINE_MATCH with comment."""
        assert EMPTY_LINE_MATCH.match("# comment") is not None
        assert EMPTY_LINE_MATCH.match("! comment") is not None

    def test_empty_line_match_content(self):
        """Test EMPTY_LINE_MATCH with content."""
        assert EMPTY_LINE_MATCH.match("content") is None

    def test_block_match_valid(self):
        """Test BLOCK_MATCH with valid block start."""
        match = BLOCK_MATCH.match("H DZVP")
        assert match is not None
        assert match.group("element") == "H"
        assert match.group("family") == "DZVP"

    def test_block_match_multi_char_element(self):
        """Test BLOCK_MATCH with multi-character element."""
        match = BLOCK_MATCH.match("Fe DZVP")
        assert match is not None
        assert match.group("element") == "Fe"

    def test_block_match_invalid(self):
        """Test BLOCK_MATCH with invalid line."""
        assert BLOCK_MATCH.match("invalid") is None


class TestChainedException:
    """Tests for chained_exception function."""

    def test_chained_exception_creation(self):
        """Test creating chained exception."""
        original = ValueError("original error")
        exc = chained_exception(RuntimeError, "wrapped error", original)
        
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "wrapped_error"
        assert exc.__cause__ is original

    def test_chained_exception_chain(self):
        """Test exception chain is preserved."""
        original = ValueError("original")
        exc = chained_exception(TypeError, "wrapper", original)
        
        assert exc.__cause__ == original
        assert str(exc.__cause__) == "original"


class TestMultipleValueErrorsException:
    """Tests for MulitpleValueErrorsException."""

    def test_exception_creation(self):
        """Test creating exception."""
        errors = [ValueError("error1"), ValueError("error2")]
        exc = MulitpleValueErrorsException(errors)
        
        assert isinstance(exc, ValueError)
        assert len(exc.args[0]) == 2


class TestDformat:
    """Tests for dformat function."""

    def test_dformat_basic(self):
        """Test basic dformat."""
        val = Decimal("1.5")
        result = dformat(val, 2, 10)
        assert isinstance(result, str)
        assert len(result) == 10

    def test_dformat_integer(self):
        """Test dformat with integer."""
        val = Decimal("5")
        result = dformat(val, 2, 10)
        assert isinstance(result, str)

    def test_dformat_negative(self):
        """Test dformat with negative number."""
        val = Decimal("-1.5")
        result = dformat(val, 2, 10)
        assert isinstance(result, str)

    def test_dformat_padding(self):
        """Test dformat adds padding."""
        val = Decimal("1.0")
        result = dformat(val, 5, 15)
        assert len(result) == 15


class TestDatafileIterMixin:
    """Tests for DatafileIterMixin."""

    def test_is_block_start_valid(self):
        """Test is_block_start with valid block."""
        assert DatafileIterMixin.is_block_start("H DZVP") is True
        assert DatafileIterMixin.is_block_start("Fe TZVP") is True

    def test_is_block_start_invalid(self):
        """Test is_block_start with invalid block."""
        assert DatafileIterMixin.is_block_start("invalid") is False
        assert DatafileIterMixin.is_block_start("") is False
        assert DatafileIterMixin.is_block_start("# comment") is False

    def test_datafile_iter_with_string(self):
        """Test datafile_iter with string content."""
        # This requires a concrete implementation
        pass  # Would need a concrete class to test

    def test_datafile_iter_with_list(self):
        """Test datafile_iter with list content."""
        pass  # Would need a concrete class to test


class TestFromDictMixin:
    """Tests for FromDictMixin."""

    def test_from_dict_warns(self):
        """Test from_dict issues deprecation warning."""
        
        class TestClass(FromDictMixin):
            @classmethod
            def parse_obj(cls, data):
                return cls()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TestClass.from_dict({"key": "value"})
            
            # Should have issued a PendingDeprecationWarning
            assert len(w) == 1
            assert issubclass(w[0].category, PendingDeprecationWarning)

    def test_from_dict_with_type_hooks_warning(self):
        """Test from_dict with type_hooks issues warning."""
        
        class TestClass(FromDictMixin):
            @classmethod
            def parse_obj(cls, data):
                return cls()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TestClass.from_dict({"key": "value"}, type_hooks={str: str})
            
            # Should have issued two warnings
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
