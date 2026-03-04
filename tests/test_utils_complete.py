"""
Comprehensive unit tests for cp2k_input_tools/utils.py
Target: 100% code coverage
"""

import io
import warnings
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from cp2k_input_tools import utils


class TestChainedException:
    """Test chained_exception function"""
    
    def test_chained_exception_basic(self):
        """Test basic chained exception creation"""
        original_exc = ValueError("original error")
        new_exc = utils.chained_exception(RuntimeError, "new error", original_exc)
        
        assert isinstance(new_exc, RuntimeError)
        assert str(new_exc) == "new error"
        assert new_exc.__cause__ is original_exc
    
    def test_chained_exception_with_different_types(self):
        """Test chained exception with different exception types"""
        original_exc = TypeError("type error")
        new_exc = utils.chained_exception(IOError, "io error", original_exc)
        
        assert isinstance(new_exc, IOError)
        assert new_exc.__cause__ is original_exc


class TestMultipleValueErrorsException:
    """Test MulitpleValueErrorsException class"""
    
    def test_exception_inheritance(self):
        """Test that it inherits from ValueError"""
        assert issubclass(utils.MulitpleValueErrorsException, ValueError)
    
    def test_exception_can_be_raised(self):
        """Test that the exception can be raised and caught"""
        with pytest.raises(utils.MulitpleValueErrorsException):
            raise utils.MulitpleValueErrorsException("test error")


class TestDatafileIterMixin:
    """Test DatafileIterMixin class"""
    
    def test_is_block_start(self):
        """Test is_block_start static method"""
        # Valid block start lines
        assert utils.DatafileIterMixin.is_block_start("H DZVP-MOLOPT-GTH") is True
        assert utils.DatafileIterMixin.is_block_start("He DZVP-MOLOPT-GTH") is True
        assert utils.DatafileIterMixin.is_block_start("Li BASIS") is True
        
        # Invalid block start lines
        assert utils.DatafileIterMixin.is_block_start("  ") is False
        assert utils.DatafileIterMixin.is_block_start("# comment") is False
        assert utils.DatafileIterMixin.is_block_start("H") is False  # Missing family
        assert utils.DatafileIterMixin.is_block_start("") is False
    
    def test_datafile_iter_with_string(self):
        """Test datafile_iter with string input"""
        
        class TestParser(utils.DatafileIterMixin):
            def __init__(self, data):
                self.data = data
            
            @classmethod
            def from_lines(cls, lines):
                return cls(lines)
            
            @staticmethod
            def is_block_start(line):
                return line.startswith("ELEMENT")
        
        content = """ELEMENT H
  data1
  data2
ELEMENT He
  data3
"""
        
        results = list(TestParser.datafile_iter(content))
        assert len(results) == 2
        assert results[0].data == ["ELEMENT H", "data1", "data2"]
        assert results[1].data == ["ELEMENT He", "data3"]
    
    def test_datafile_iter_with_list(self):
        """Test datafile_iter with list input"""
        
        class TestParser(utils.DatafileIterMixin):
            def __init__(self, data):
                self.data = data
            
            @classmethod
            def from_lines(cls, lines):
                return cls(lines)
        
        lines = [
            "ELEMENT H",
            "  data1",
            "ELEMENT He",
            "  data2",
        ]
        
        results = list(TestParser.datafile_iter(lines))
        assert len(results) == 2
    
    def test_datafile_iter_with_file_handle(self):
        """Test datafile_iter with file handle input"""
        
        class TestParser(utils.DatafileIterMixin):
            def __init__(self, data):
                self.data = data
            
            @classmethod
            def from_lines(cls, lines):
                return cls(lines)
        
        content = "ELEMENT H\n  data1\nELEMENT He\n  data2\n"
        fhandle = io.StringIO(content)
        
        results = list(TestParser.datafile_iter(fhandle))
        assert len(results) == 2
    
    def test_datafile_iter_emit_comments(self):
        """Test datafile_iter with emit_comments=True"""
        
        class TestParser(utils.DatafileIterMixin):
            def __init__(self, data):
                self.data = data
            
            @classmethod
            def from_lines(cls, lines):
                return cls(lines)
        
        content = """# comment line
ELEMENT H
  data1
# another comment
ELEMENT He
  data2
"""
        
        results = list(TestParser.datafile_iter(content, emit_comments=True))
        # Should include comments as strings
        assert any(isinstance(r, str) and "#" in r for r in results)
    
    def test_datafile_iter_keep_going_false(self):
        """Test datafile_iter with keep_going=False"""
        
        class TestParser(utils.DatafileIterMixin):
            @classmethod
            def from_lines(cls, lines):
                raise ValueError("Parse error")
        
        content = "ELEMENT H\n  data1\n"
        
        with pytest.raises(ValueError, match="failed to parse block"):
            list(TestParser.datafile_iter(content, keep_going=False))
    
    def test_datafile_iter_keep_going_true(self):
        """Test datafile_iter with keep_going=True (default)"""
        
        class TestParser(utils.DatafileIterMixin):
            call_count = 0
            
            @classmethod
            def from_lines(cls, lines):
                cls.call_count += 1
                if cls.call_count == 1:
                    raise ValueError("Parse error")
                return cls(lines)
            
            def __init__(self, data):
                self.data = data
        
        content = "ELEMENT H\n  data1\nELEMENT He\n  data2\n"
        
        # Should not raise, should continue after error
        results = list(TestParser.datafile_iter(content, keep_going=True))
        # Second element should be parsed successfully
        assert len(results) == 1
        assert results[0].data == ["ELEMENT He", "data2"]
    
    def test_datafile_iter_multiple_errors(self):
        """Test datafile_iter with multiple errors"""
        
        class TestParser(utils.DatafileIterMixin):
            @classmethod
            def from_lines(cls, lines):
                raise ValueError(f"Error for {lines[0]}")
        
        content = "ELEMENT H\n  data1\nELEMENT He\n  data2\n"
        
        with pytest.raises(utils.MulitpleValueErrorsException):
            list(TestParser.datafile_iter(content, keep_going=True))
    
    def test_datafile_iter_single_error(self):
        """Test datafile_iter with single error raises that error"""
        
        class TestParser(utils.DatafileIterMixin):
            call_count = 0
            
            @classmethod
            def from_lines(cls, lines):
                cls.call_count += 1
                if cls.call_count == 1:
                    raise ValueError("Single error")
                return cls(lines)
        
        content = "ELEMENT H\n  data1\n"
        
        # With only one error, should raise that error wrapped
        with pytest.raises(ValueError, match="failed to parse block"):
            list(TestParser.datafile_iter(content, keep_going=True))


class TestFromDictMixin:
    """Test FromDictMixin class"""
    
    def test_from_dict_with_deprecation_warning(self):
        """Test that from_dict raises deprecation warning"""
        
        class TestClass(utils.FromDictMixin):
            @classmethod
            def parse_obj(cls, data):
                return cls(**data)
            
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = TestClass.from_dict({"key": "value"})
            
            # Check deprecation warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, PendingDeprecationWarning)
            assert "parse_obj" in str(w[0].message)
    
    def test_from_dict_with_type_hooks(self):
        """Test that from_dict handles type_hooks with deprecation warning"""
        
        class TestClass(utils.FromDictMixin):
            @classmethod
            def parse_obj(cls, data):
                return cls(**data)
            
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = TestClass.from_dict({"key": "value"}, type_hooks={str: lambda x: x.upper()})
            
            # Should have two warnings (PendingDeprecationWarning and DeprecationWarning)
            assert len(w) == 2
            assert any("type_hooks" in str(warning.message) for warning in w)
    
    def test_from_dict_calls_parse_obj(self):
        """Test that from_dict correctly calls parse_obj"""
        
        class TestClass(utils.FromDictMixin):
            @classmethod
            def parse_obj(cls, data):
                instance = cls()
                instance.data = data
                return instance
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = TestClass.from_dict({"test": "data"})
            assert result.data == {"test": "data"}


class TestDformat:
    """Test dformat function"""
    
    def test_dformat_basic(self):
        """Test basic dformat functionality"""
        d = Decimal("1.23")
        result = utils.dformat(d, ndigits=5, slen=10)
        assert len(result) == 10
        assert "1.23" in result
    
    def test_dformat_negative(self):
        """Test dformat with negative number"""
        d = Decimal("-.1")
        result = utils.dformat(d, ndigits=10, slen=16)
        assert len(result) == 16
        assert "-0.1" in result
    
    def test_dformat_integer(self):
        """Test dformat with integer"""
        d = Decimal("1")
        result = utils.dformat(d, ndigits=10, slen=16)
        assert len(result) == 16
        assert "1" in result
    
    def test_dformat_zero_with_exponent(self):
        """Test dformat with zero that has exponent"""
        d = Decimal("0E-10")
        result = utils.dformat(d, ndigits=10, slen=16)
        assert len(result) == 16
        assert "0.0000000000" in result
    
    def test_dformat_scientific(self):
        """Test dformat with scientific notation"""
        d = Decimal("1E-10")
        result = utils.dformat(d, ndigits=10, slen=16)
        assert len(result) == 16
        assert "0.0000000001" in result
    
    def test_dformat_right_padding(self):
        """Test that dformat right-pads correctly"""
        d = Decimal("1.5")
        result = utils.dformat(d, ndigits=2, slen=10)
        assert result.startswith(" ")  # Right-aligned
        assert "1.5" in result


class TestElementTables:
    """Test NUM2SYM and SYM2NUM lookup tables"""
    
    def test_num2sym_length(self):
        """Test NUM2SYM has correct length"""
        assert len(utils.NUM2SYM) == 119  # 0 + 118 elements
    
    def test_num2sym_first_element(self):
        """Test first element is empty string"""
        assert utils.NUM2SYM[0] == ""
    
    def test_num2sym_hydrogen(self):
        """Test hydrogen is at correct index"""
        assert utils.NUM2SYM[1] == "H"
        assert utils.NUM2SYM[2] == "He"
    
    def test_num2sym_last_element(self):
        """Test last element is Oganesson"""
        assert utils.NUM2SYM[118] == "Og"
    
    def test_sym2num_hydrogen(self):
        """Test SYM2NUM lookup for hydrogen"""
        assert utils.SYM2NUM["H"] == 1
    
    def test_sym2num_oganesson(self):
        """Test SYM2NUM lookup for oganesson"""
        assert utils.SYM2NUM["Og"] == 118
    
    def test_sym2num_all_elements(self):
        """Test that all elements in NUM2SYM are in SYM2NUM"""
        for Z, sym in enumerate(utils.NUM2SYM[1:], start=1):
            assert utils.SYM2NUM[sym] == Z
    
    def test_sym2num_case_sensitive(self):
        """Test SYM2NUM is case-sensitive (only uppercase)"""
        assert "H" in utils.SYM2NUM
        assert "h" not in utils.SYM2NUM


class TestConstants:
    """Test module constants"""
    
    def test_eof_marker(self):
        """Test EOF_MARKER_LINE constant"""
        assert utils.EOF_MARKER_LINE == "Eof marker"
    
    def test_empty_line_match(self):
        """Test EMPTY_LINE_MATCH regex"""
        # Should match empty lines
        assert utils.EMPTY_LINE_MATCH.match("") is not None
        assert utils.EMPTY_LINE_MATCH.match("   ") is not None
        assert utils.EMPTY_LINE_MATCH.match("\t\t") is not None
        
        # Should match comment-only lines
        assert utils.EMPTY_LINE_MATCH.match("# comment") is not None
        assert utils.EMPTY_LINE_MATCH.match("  ! comment") is not None
        
        # Should not match content lines
        assert utils.EMPTY_LINE_MATCH.match("H BASIS") is None
        assert utils.EMPTY_LINE_MATCH.match("  data  ") is None
    
    def test_block_match(self):
        """Test BLOCK_MATCH regex"""
        # Valid block starts
        match = utils.BLOCK_MATCH.match("H DZVP-MOLOPT-GTH")
        assert match is not None
        assert match.group("element") == "H"
        assert match.group("family") == "DZVP-MOLOPT-GTH"
        
        # Two-letter element
        match = utils.BLOCK_MATCH.match("He BASIS")
        assert match is not None
        assert match.group("element") == "He"
        
        # Three-letter element
        match = utils.BLOCK_MATCH.match("Uue BASIS")
        assert match is not None
        assert match.group("element") == "Uue"
        
        # Invalid matches
        assert utils.BLOCK_MATCH.match("H") is None
        assert utils.BLOCK_MATCH.match("# comment") is None


class TestSupportsFromLinesProtocol:
    """Test SupportsFromLines protocol"""
    
    def test_protocol_structure(self):
        """Test that SupportsFromLines is a Protocol"""
        assert hasattr(utils.SupportsFromLines, 'from_lines')
        assert hasattr(utils.SupportsFromLines, 'is_block_start')
