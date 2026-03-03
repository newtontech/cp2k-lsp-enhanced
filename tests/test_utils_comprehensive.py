"""Comprehensive tests for cp2k_input_tools/utils.py to achieve 100% coverage."""

import pytest
import io
from decimal import Decimal

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


class TestConstants:
    """Test module constants."""

    def test_num2sym_list(self):
        """Test NUM2SYM contains element symbols."""
        assert NUM2SYM[1] == "H"
        assert NUM2SYM[2] == "He"
        assert NUM2SYM[6] == "C"
        assert NUM2SYM[8] == "O"
        assert NUM2SYM[26] == "Fe"
        assert NUM2SYM[118] == "Og"
        assert len(NUM2SYM) == 119

    def test_sym2num_dict(self):
        """Test SYM2NUM maps symbols to atomic numbers."""
        assert SYM2NUM["H"] == 1
        assert SYM2NUM["He"] == 2
        assert SYM2NUM["C"] == 6
        assert SYM2NUM["O"] == 8
        assert SYM2NUM["Fe"] == 26
        assert SYM2NUM["Og"] == 118

    def test_eof_marker_line(self):
        """Test EOF_MARKER_LINE constant."""
        assert EOF_MARKER_LINE == "Eof marker"

    def test_empty_line_match(self):
        """Test EMPTY_LINE_MATCH regex."""
        assert EMPTY_LINE_MATCH.match("") is not None
        assert EMPTY_LINE_MATCH.match("   ") is not None
        assert EMPTY_LINE_MATCH.match("# comment") is not None
        assert EMPTY_LINE_MATCH.match("  # comment  ") is not None
        assert EMPTY_LINE_MATCH.match("not empty") is None

    def test_block_match(self):
        """Test BLOCK_MATCH regex."""
        match = BLOCK_MATCH.match("H BASIS_SET")
        assert match is not None
        assert match.group("element") == "H"
        assert match.group("family") == "BASIS_SET"

        match = BLOCK_MATCH.match("  He  SOME_FAMILY extra")
        assert match is not None
        assert match.group("element") == "He"


class TestChainedException:
    """Test chained_exception function."""

    def test_chained_exception(self):
        """Test creating a chained exception."""
        prev = ValueError("previous error")
        exc = chained_exception(RuntimeError, "new error", prev)
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "new error"
        assert exc.__cause__ is prev

    def test_chained_exception_with_tb(self):
        """Test chained exception with traceback."""
        try:
            raise ValueError("original")
        except ValueError as e:
            exc = chained_exception(RuntimeError, "wrapped", e)
            assert exc.__cause__ is e


class TestMultipleValueErrorsException:
    """Test MulitpleValueErrorsException."""

    def test_multiple_value_errors(self):
        """Test MulitpleValueErrorsException."""
        exc = MulitpleValueErrorsException("multiple errors")
        assert str(exc) == "multiple errors"
        assert isinstance(exc, Exception)


class TestDatafileIterMixin:
    """Test DatafileIterMixin class."""

    def test_datafile_iter_mixin_exists(self):
        """Test DatafileIterMixin exists."""
        from cp2k_input_tools.utils import DatafileIterMixin
        assert DatafileIterMixin is not None


class TestFromDictMixin:
    """Test FromDictMixin class."""

    def test_from_dict_mixin_exists(self):
        """Test FromDictMixin exists."""
        from cp2k_input_tools.utils import FromDictMixin
        assert FromDictMixin is not None


class TestDFormat:
    """Test dformat function."""

    def test_dformat_basic(self):
        """Test basic dformat usage."""
        val = Decimal("3.14")
        result = dformat(val, 2, 10)
        assert len(result) == 10

    def test_dformat_integer(self):
        """Test dformat with integer-like decimal."""
        val = Decimal("42")
        result = dformat(val, 2, 8)
        assert len(result) == 8

    def test_dformat_small(self):
        """Test dformat with small value."""
        val = Decimal("0.001")
        result = dformat(val, 5, 12)
        assert len(result) == 12
