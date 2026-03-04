# Test for issue #72: X..Y range parsing fix
import pytest
from cp2k_input_tools.keyword_helpers import (
    kw_converter_int,
    IntegerRange,
    KEEP_RANGE_AS_STRING,
)


class TestXyRangeFix:
    """Test X..Y range parsing for issue #72"""

    def test_global_config_exists(self):
        """Test KEEP_RANGE_AS_STRING global config exists"""
        assert isinstance(KEEP_RANGE_AS_STRING, bool)

    def test_range_as_integer_range_default(self):
        """Test X..Y range returns IntegerRange by default (issue #72)"""
        result = kw_converter_int('1..10')
        assert isinstance(result, IntegerRange)
        assert result.start == 1
        assert result.end == 10

    def test_range_as_string_explicit(self):
        """Test X..Y range returns string when explicitly requested"""
        result = kw_converter_int('1..10', keep_range_as_string=True)
        assert isinstance(result, str)
        assert result == '1..10'

    def test_simple_int_unchanged(self):
        """Test simple integer parsing is unchanged"""
        result = kw_converter_int('42')
        assert isinstance(result, int)
        assert result == 42

    def test_negative_range_as_integer_range(self):
        """Test negative X..Y range as IntegerRange"""
        result = kw_converter_int('-5..5')
        assert isinstance(result, IntegerRange)
        assert result.start == -5
        assert result.end == 5

    def test_explicit_string_mode(self):
        """Test explicit keep_range_as_string=True"""
        result = kw_converter_int('1..100', keep_range_as_string=True)
        assert isinstance(result, str)
        assert result == '1..100'

    def test_explicit_range_mode(self):
        """Test explicit keep_range_as_string=False"""
        result = kw_converter_int('1..100', keep_range_as_string=False)
        assert isinstance(result, IntegerRange)
        assert result.start == 1
        assert result.end == 100