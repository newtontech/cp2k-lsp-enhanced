# Extended tests for cp2k_input_tools/utils.py
# Target: 100% coverage

import io
import pytest
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
    """Test module constants"""

    def test_num2sym_list(self):
        """Test NUM2SYM contains element symbols"""
        assert NUM2SYM[1] == "H"
        assert NUM2SYM[2] == "He"
        assert NUM2SYM[6] == "C"
        assert NUM2SYM[8] == "O"
        assert NUM2SYM[26] == "Fe"
        assert NUM2SYM[118] == "Og"
        assert len(NUM2SYM) == 119  # 0-118

    def test_sym2num_dict(self):
        """Test SYM2NUM maps symbols to atomic numbers"""
        assert SYM2NUM["H"] == 1
        assert SYM2NUM["He"] == 2
        assert SYM2NUM["C"] == 6
        assert SYM2NUM["O"] == 8
        assert SYM2NUM["Fe"] == 26
        assert SYM2NUM["Og"] == 118

    def test_empty_line_match(self):
        """Test EMPTY_LINE_MATCH regex"""
        assert EMPTY_LINE_MATCH.match("") is not None
        assert EMPTY_LINE_MATCH.match("   ") is not None
        assert EMPTY_LINE_MATCH.match("# comment") is not None
        assert EMPTY_LINE_MATCH.match("  # comment  ") is not None
        assert EMPTY_LINE_MATCH.match("not empty") is None

    def test_block_match(self):
        """Test BLOCK_MATCH regex"""
        match = BLOCK_MATCH.match("H BASIS_SET")
        assert match is not None
        assert match.group("element") == "H"
        assert match.group("family") == "BASIS_SET"

        match = BLOCK_MATCH.match("  He  SOME_FAMILY extra")
        assert match is not None
        assert match.group("element") == "He"


class TestChainedException:
    """Test chained_exception function"""

    def test_chained_exception(self):
        """Test creating a chained exception"""
        prev = ValueError("previous error")
        exc = chained_exception(RuntimeError, "new error", prev)
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "new error"
        assert exc.__cause__ is prev


class TestMultipleValueErrorsException:
    """Test MulitpleValueErrorsException"""

    def test_multiple_value_errors(self):
        """Test MulitpleValueErrorsException"""
        exc = MulitpleValueErrorsException("multiple errors")
        assert isinstance(exc, ValueError)
        assert str(exc) == "multiple errors"


class MockDataClass:
    """Mock class for testing DatafileIterMixin"""

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_lines(cls, lines):
        return cls("\n".join(lines))

    @staticmethod
    def is_block_start(line):
        return line.startswith("BLOCK:")


class TestDatafileIterMixin:
    """Test DatafileIterMixin class"""

    def test_datafile_iter_simple(self):
        """Test iterating over simple data"""
        content = "BLOCK: first\nline1\nline2\n\nBLOCK: second\nline3\n"
        results = list(DatafileIterMixin.datafile_iter(content.splitlines(), keep_going=True))
        assert len(results) == 2
        assert results[0].data == "BLOCK: first\nline1\nline2"
        assert results[1].data == "BLOCK: second\nline3"

    def test_datafile_iter_with_comments(self):
        """Test iterating with emit_comments=True"""
        content = "# header comment\n\nBLOCK: first\ndata\n"
        results = list(DatafileIterMixin.datafile_iter(content.splitlines(), keep_going=True, emit_comments=True))
        # Should include comments
        assert any("# header comment" in str(r) for r in results if isinstance(r, str))

    def test_datafile_iter_keep_going_false(self):
        """Test with keep_going=False raises on error"""

        class ErrorClass:
            @classmethod
            def from_lines(cls, lines):
                raise ValueError("parse error")

            @staticmethod
            def is_block_start(line):
                return line.startswith("BLOCK:")

        content = "BLOCK: first\ndata\n"
        with pytest.raises(ValueError):
            list(DatafileIterMixin.datafile_iter(content.splitlines(), keep_going=False))

    def test_datafile_iter_with_io(self):
        """Test with file-like object"""
        content = io.StringIO("BLOCK: first\ndata\n")
        results = list(DatafileIterMixin.datafile_iter(content, keep_going=True))
        assert len(results) == 1

    def test_datafile_iter_multiple_errors(self):
        """Test multiple errors raises MulitpleValueErrorsException"""

        class ErrorClass:
            @classmethod
            def from_lines(cls, lines):
                raise ValueError("parse error")

            @staticmethod
            def is_block_start(line):
                return line.startswith("BLOCK:")

        content = "BLOCK: first\ndata\n\nBLOCK: second\ndata2\n"
        with pytest.raises(MulitpleValueErrorsException):
            list(DatafileIterMixin.datafile_iter(content.splitlines(), keep_going=True))


class MockFromDictClass(FromDictMixin):
    """Mock class for testing FromDictMixin"""

    def __init__(self, value):
        self.value = value

    @classmethod
    def parse_obj(cls, data):
        return cls(data.get("value"))


class TestFromDictMixin:
    """Test FromDictMixin class"""

    def test_from_dict_simple(self):
        """Test from_dict creates instance from dict"""
        obj = MockFromDictClass.from_dict({"value": 42})
        assert obj.value == 42

    def test_from_dict_with_type_hooks_warning(self):
        """Test from_dict with type_hooks emits deprecation warning"""
        with pytest.warns(DeprecationWarning):
            obj = MockFromDictClass.from_dict({"value": 42}, type_hooks={})
        assert obj.value == 42

    def test_from_dict_pending_deprecation_warning(self):
        """Test from_dict emits pending deprecation warning"""
        with pytest.warns(PendingDeprecationWarning):
            obj = MockFromDictClass.from_dict({"value": 42})
        assert obj.value == 42


class TestDformat:
    """Test dformat function"""

    def test_dformat_positive(self):
        """Test formatting positive decimal"""
        result = dformat(Decimal("1.234"), 2, 10)
        assert len(result) == 10

    def test_dformat_negative(self):
        """Test formatting negative decimal"""
        result = dformat(Decimal("-1.234"), 2, 10)
        assert len(result) == 10

    def test_dformat_zero(self):
        """Test formatting zero"""
        result = dformat(Decimal("0.0"), 2, 8)
        assert len(result) == 8

    def test_dformat_large(self):
        """Test formatting large number"""
        result = dformat(Decimal("123.456"), 3, 12)
        assert len(result) == 12
