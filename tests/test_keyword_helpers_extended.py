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
        """Test string with spaces"""
        assert kw_converter_str("  hello world  ") == "hello world"


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

    def test_negative_fraction(self):
        """Test negative fraction"""
        assert kw_converter_float("-1/2") == -0.5


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
        assert result.start == -5
        assert result.end == 5


class TestKwConverterKeyword:
    """Test kw_converter_keyword function"""

    def test_valid_keyword(self):
        """Test valid keyword conversion"""
        allowed = ["OPTION_A", "OPTION_B", "OPTION_C"]
        assert kw_converter_keyword("option_a", allowed) == "OPTION_A"
        assert kw_converter_keyword("OPTION_B", allowed) == "OPTION_B"

    def test_invalid_keyword(self):
        """Test invalid keyword raises InvalidParameterError"""
        allowed = ["OPTION_A", "OPTION_B"]
        with pytest.raises(InvalidParameterError):
            kw_converter_keyword("INVALID", allowed)


class TestIntegerRange:
    """Test IntegerRange dataclass"""

    def test_integer_range_creation(self):
        """Test creating IntegerRange"""
        r = IntegerRange(1, 10)
        assert r.start == 1
        assert r.end == 10

    def test_integer_range_frozen(self):
        """Test IntegerRange is frozen (immutable)"""
        r = IntegerRange(0, 100)
        with pytest.raises(Exception):  # FrozenInstanceError
            r.start = 50


class TestKWValueConverters:
    """Test KW_VALUE_CONVERTERS mapping"""

    def test_converters_exist(self):
        """Test all expected converters exist"""
        assert "logical" in KW_VALUE_CONVERTERS
        assert "integer" in KW_VALUE_CONVERTERS
        assert "real" in KW_VALUE_CONVERTERS
        assert "word" in KW_VALUE_CONVERTERS
        assert "string" in KW_VALUE_CONVERTERS

    def test_logical_converter(self):
        """Test logical converter"""
        assert KW_VALUE_CONVERTERS["logical"]("TRUE") is True
        assert KW_VALUE_CONVERTERS["logical"]("FALSE") is False

    def test_integer_converter(self):
        """Test integer converter"""
        assert KW_VALUE_CONVERTERS["integer"]("42") == 42

    def test_real_converter(self):
        """Test real converter"""
        assert KW_VALUE_CONVERTERS["real"]("3.14") == 3.14

    def test_string_converters(self):
        """Test string and word converters"""
        assert KW_VALUE_CONVERTERS["string"]("hello") == "hello"
        assert KW_VALUE_CONVERTERS["word"]("hello") == "hello"


class TestGetDatatype:
    """Test get_datatype function"""

    def test_get_datatype_integer(self):
        """Test getting integer datatype"""
        # Create a mock keyword node
        xml_str = '''
        <KEYWORD>
            <NAME>TEST_INT</NAME>
            <DATA_TYPE kind="integer">
                <N_VAR>1</N_VAR>
            </DATA_TYPE>
        </KEYWORD>
        '''
        node = ET.fromstring(xml_str)
        dt = get_datatype(node)
        assert dt.type == "integer"
        assert dt.n_var == 1
        assert dt.parser("42") == 42

    def test_get_datatype_real(self):
        """Test getting real datatype"""
        xml_str = '''
        <KEYWORD>
            <NAME>TEST_REAL</NAME>
            <DATA_TYPE kind="real">
                <N_VAR>1</N_VAR>
            </DATA_TYPE>
        </KEYWORD>
        '''
        node = ET.fromstring(xml_str)
        dt = get_datatype(node)
        assert dt.type == "real"
        assert dt.n_var == 1

    def test_get_datatype_keyword(self):
        """Test getting keyword datatype"""
        xml_str = '''
        <KEYWORD>
            <NAME>TEST_KEYWORD</NAME>
            <DATA_TYPE kind="keyword">
                <N_VAR>1</N_VAR>
                <NAME>OPTION_A</NAME>
                <NAME>OPTION_B</NAME>
            </DATA_TYPE>
        </KEYWORD>
        '''
        node = ET.fromstring(xml_str)
        dt = get_datatype(node)
        assert dt.type == "keyword"
        assert dt.n_var == 1
        assert dt.parser("OPTION_A") == "OPTION_A"


class TestKeyword:
    """Test Keyword dataclass"""

    def test_keyword_creation(self):
        """Test creating Keyword instance"""
        kw = Keyword(name="TEST", values=[1, 2, 3])
        assert kw.name == "TEST"
        assert kw.values == [1, 2, 3]

    def test_keyword_frozen(self):
        """Test Keyword is frozen"""
        kw = Keyword(name="TEST", values=[])
        with pytest.raises(Exception):  # FrozenInstanceError
            kw.name = "OTHER"
