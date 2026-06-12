"""Tests for issue #72: parsing of X..Y ranges for LIST keyword."""

import io

import pytest

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.keyword_helpers import kw_converter_integer
from cp2k_input_tools.parser import CP2KInputParser, CP2KInputParserSimplified


class TestIntegerRangeConverter:
    """Unit tests for kw_converter_integer with range support."""

    def test_plain_integer(self):
        assert kw_converter_integer("42") == 42

    def test_negative_integer(self):
        assert kw_converter_integer("-3") == -3

    def test_simple_range(self):
        assert kw_converter_integer("1..5") == [1, 2, 3, 4, 5]

    def test_single_element_range(self):
        assert kw_converter_integer("3..3") == [3]

    def test_range_with_larger_numbers(self):
        assert kw_converter_integer("10..15") == [10, 11, 12, 13, 14, 15]

    def test_reversed_range_raises(self):
        from cp2k_input_tools.parser_errors import InvalidParameterError

        with pytest.raises(InvalidParameterError, match="start.*>.*end"):
            kw_converter_integer("5..1")


class TestListKeywordRangeParsing:
    """Integration tests parsing full CP2K input with LIST ranges."""

    def test_simple_range(self):
        """LIST 1..5 should expand to [1, 2, 3, 4, 5]."""
        parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 1..5
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        # Navigate to the LIST keyword value
        isolated_atoms = result["force_eval"]["subsys"]["topology"]["generate"]["isolated_atoms"]
        assert isolated_atoms["list"] == (1, 2, 3, 4, 5)

    def test_mixed_values_and_ranges(self):
        """LIST 1 3..7 10 should expand to (1, 3, 4, 5, 6, 7, 10)."""
        parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 1 3..7 10
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        isolated_atoms = result["force_eval"]["subsys"]["topology"]["generate"]["isolated_atoms"]
        assert isolated_atoms["list"] == (1, 3, 4, 5, 6, 7, 10)

    def test_single_integer_still_works(self):
        """LIST 42 should parse as a single integer (not a tuple)."""
        parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 42
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        isolated_atoms = result["force_eval"]["subsys"]["topology"]["generate"]["isolated_atoms"]
        assert isolated_atoms["list"] == 42

    def test_multiple_individual_integers(self):
        """LIST 1 2 3 should parse as a tuple of integers."""
        parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 1 2 3
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        isolated_atoms = result["force_eval"]["subsys"]["topology"]["generate"]["isolated_atoms"]
        assert isolated_atoms["list"] == (1, 2, 3)

    def test_canonical_parser_range(self):
        """Canonical parser should also handle ranges correctly."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 1..3
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        # Canonical parser wraps repeating sections/keywords in lists
        generate = result["+force_eval"][0]["+subsys"]["+topology"]["+generate"]
        isolated_atoms = generate[0]["+isolated_atoms"]
        # LIST repeats="yes", so values are wrapped in a list
        assert isolated_atoms["list"] == [(1, 2, 3)]

    def test_range_in_thermostat_define_region(self):
        """LIST keyword under DEFINE_REGION (thermostat) should also support ranges."""
        parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
        inp = """&MOTION
  &MD
    &THERMOSTAT
      &DEFINE_REGION
        LIST 1..4
      &END DEFINE_REGION
    &END THERMOSTAT
  &END MD
&END MOTION
"""
        result = parser.parse(io.StringIO(inp))
        define_region = result["motion"]["md"]["thermostat"]["define_region"]
        assert define_region["list"] == (1, 2, 3, 4)
