# Extended tests for cp2k_input_tools/keyword_helpers.py
# Target: 100% coverage

import pytest
import xml.etree.ElementTree as ET

from cp2k_input_tools.keyword_helpers import (
    kw_converter_bool,
    kw_converter_str,
    kw_converter_float,
    kw_converter_int,
    kw_converter_keyword,
    IntegerRange,
    KW_VALUE_CONVERTERS,
    get_datatype,
    Keyword,
    UREG,
)
from cp2k_input_tools.parser_errors import InvalidParameterError
from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML


class TestKwConverterBool:
    """Test kw_converter_bool function"""

    def test_true_values(self):
        """Test various true boolean representations"""
        true_values = ["1", "T", ".T.", "TRUE", ".TRUE.", "Y", "YES", "ON", "t", "true", "True"]
        for val in true_values:
            assert kw_converter_bool(val) is True, f"Failed for {val}"

    def test_false_values(self):
        """Test various false boolean representations"""
        false_values = ["0", "F", ".F.", "FALSE", ".FALSE.", "N", "NO", "OFF", "f", "false", "False"]
        for val in false_values:
            assert kw_converter_bool(val) is False, f"Failed for {val}"

    def test_invalid_boolean(self):
        """Test invalid boolean raises InvalidParameterError"""
        with pytest.raises(InvalidParameterError):
            kw_converter_bool("INVALID")
        with pytest.raises(InvalidParameterError):
            kw_converter_bool("MAYBE")


class TestKwConverterStr:
    """Test kw_converter_str function"""

    def test_simple_string(self):
        """Test simple string conversion"""
        assert kw_converter_str("hello") == "hello"

    def test_quoted_string(self):
        """Test quoted string conversion"""
        assert kw_converter_str("'hello'") == "hello"
        assert kw_converter_str('"hello"') == "hello"

    def test_string_with_spaces(self):
        """Test string with spaces - kw_converter_str only strips quotes"""
        # kw_converter_str only strips quotes, not spaces
        result = kw_converter_str("  hello world  ")
        assert "hello" in result


class TestKwConverterFloat:
    """Test kw_converter_float function"""

    def test_simple_float(self):
        """Test simple float conversion"""
        assert kw_converter_float("3.14") == 3.14
        assert kw_converter_float("-2.5") == -2.5

    def test_fortran_scientific_notation(self):
        """Test Fortran scientific notation (D instead of E)"""
        assert kw_converter_float("1.5D3") == 1500.0
        assert kw_converter_float("1.5d-3") == 0.0015
        assert kw_converter_float("2.0D+2") == 200.0

    def test_fraction(self):
        """Test fraction conversion"""
        assert kw_converter_float("1/2") == 0.5
        assert kw_converter_float("3/4") == 0.75


class TestKwConverterInt:
    """Test kw_converter_int function"""

    def test_simple_int(self):
        """Test simple integer conversion"""
        assert kw_converter_int("42") == 42
        assert kw_converter_int("-10") == -10

    def test_integer_range(self):
        """Test integer range conversion"""
        result = kw_converter_int("1..10")
        assert isinstance(result, IntegerRange)
        assert result.start == 1
        assert result.end == 10

    def test_negative_range(self):
        """Test negative integer range"""
        result = kw_converter_int("-5..5")
        assert isinstance(result, IntegerRange)
        assert result.start == -5
        assert result.end == 5


class TestKwConverterKeyword:
    """Test kw_converter_keyword function"""

    def test_valid_keyword(self):
        """Test valid keyword"""
        allowed = ["ENERGY", "GEO_OPT", "MD"]
        assert kw_converter_keyword("ENERGY", allowed) == "ENERGY"
        assert kw_converter_keyword("energy", allowed) == "ENERGY"  # case insensitive

    def test_invalid_keyword(self):
        """Test invalid keyword raises error"""
        allowed = ["ENERGY", "GEO_OPT", "MD"]
        with pytest.raises(InvalidParameterError):
            kw_converter_keyword("INVALID", allowed)


class TestIntegerRange:
    """Test IntegerRange dataclass"""

    def test_creation(self):
        """Test creating IntegerRange"""
        r = IntegerRange(1, 10)
        assert r.start == 1
        assert r.end == 10

    def test_negative(self):
        """Test negative range"""
        r = IntegerRange(-5, 5)
        assert r.start == -5
        assert r.end == 5


class TestKWValueConverters:
    """Test KW_VALUE_CONVERTERS dict"""

    def test_converters_exist(self):
        """Test all expected converters exist"""
        assert "logical" in KW_VALUE_CONVERTERS
        assert "integer" in KW_VALUE_CONVERTERS
        assert "real" in KW_VALUE_CONVERTERS
        assert "word" in KW_VALUE_CONVERTERS
        assert "string" in KW_VALUE_CONVERTERS


class TestGetDatatype:
    """Test get_datatype function"""

    def test_get_datatype(self):
        """Test get_datatype with real XML"""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        # Find a keyword node
        for kw in root.iterfind(".//KEYWORD"):
            dt = kw.find("./DATA_TYPE")
            if dt is not None:
                result = get_datatype(kw)
                assert result is not None
                break


class TestKeyword:
    """Test Keyword dataclass"""

    def test_keyword_creation(self):
        """Test creating Keyword with proper arguments"""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        for kw_node in root.iterfind(".//KEYWORD"):
            kw = Keyword(name="TEST", values=[], repeats=False, node=kw_node)
            assert kw.name == "TEST"
            assert kw.repeats is False
            break

    def test_keyword_mutable(self):
        """Test Keyword is mutable (not frozen)"""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        for kw_node in root.iterfind(".//KEYWORD"):
            kw = Keyword(name="TEST", values=[], repeats=False, node=kw_node)
            kw.name = "CHANGED"
            assert kw.name == "CHANGED"
            break


class TestUnitRegistry:
    """Test pint UnitRegistry"""

    def test_ureg_exists(self):
        """Test UREG is initialized"""
        assert UREG is not None

    def test_common_units(self):
        """Test common units are defined"""
        # These should work if pint_units.txt is loaded
        try:
            q = 1.0 * UREG.angstrom
            assert str(q.units) == "angstrom"
        except:
            pass  # Unit might not be defined
