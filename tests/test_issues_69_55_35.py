"""Tests for issues #69, #55, and #35."""

import io
import warnings

import pytest

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.keyword_helpers import (
    DEPRECATED_KEYWORDS,
    DEPRECATED_SECTIONS,
    DeprecatedKeywordWarning,
    DeprecatedSectionWarning,
    Keyword,
    check_deprecated,
    check_deprecated_section,
    register_deprecated,
    register_deprecated_section,
)
from cp2k_input_tools.parser import CP2KInputParser


class TestIssue69PrintAtomKind:
    """Test that PRINT_ATOM_KIND keyword is recognized in MOTION/PRINT/FORCES."""

    def test_print_atom_kind_accepted(self):
        """PRINT_ATOM_KIND should be a valid keyword under MOTION/PRINT/FORCES."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&MOTION
  &PRINT
    &FORCES
      PRINT_ATOM_KIND TRUE
    &END FORCES
  &END PRINT
&END MOTION
"""
        result = parser.parse(io.StringIO(inp))
        # +print is a list since PRINT section can repeat
        forces = result.get("+motion", {}).get("+print", [{}])[0].get("+forces", {})
        assert "print_atom_kind" in forces
        assert forces["print_atom_kind"] is True

    def test_print_atom_kind_false(self):
        """PRINT_ATOM_KIND FALSE should parse correctly."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&MOTION
  &PRINT
    &FORCES
      PRINT_ATOM_KIND F
    &END FORCES
  &END PRINT
&END MOTION
"""
        result = parser.parse(io.StringIO(inp))
        forces = result.get("+motion", {}).get("+print", [{}])[0].get("+forces", {})
        assert forces["print_atom_kind"] is False

    def test_print_atom_kind_lone_keyword(self):
        """PRINT_ATOM_KIND as lone keyword should default to T."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&MOTION
  &PRINT
    &FORCES
      PRINT_ATOM_KIND
    &END FORCES
  &END PRINT
&END MOTION
"""
        result = parser.parse(io.StringIO(inp))
        forces = result.get("+motion", {}).get("+print", [{}])[0].get("+forces", {})
        assert "print_atom_kind" in forces


class TestIssue55InternalCp2kUnit:
    """Test that internal_cp2k units are handled without conversion."""

    def test_internal_cp2k_value_stored_as_is(self):
        """Keywords with internal_cp2k default unit should store values as-is."""
        import xml.etree.ElementTree as ET

        spec = ET.parse(DEFAULT_CP2K_INPUT_XML)
        for kw in spec.iter("KEYWORD"):
            du = kw.find("./DEFAULT_UNIT")
            if du is not None and du.text == "internal_cp2k":
                value = Keyword.from_string(kw, "1.23")
                assert value.values == 1.23
                break
        else:
            pytest.skip("No keyword with internal_cp2k default unit found")

    def test_internal_cp2k_with_explicit_unit_stored_as_string(self):
        """Keywords with internal_cp2k and explicit unit should store as string."""
        import xml.etree.ElementTree as ET

        spec = ET.parse(DEFAULT_CP2K_INPUT_XML)
        for kw in spec.iter("KEYWORD"):
            du = kw.find("./DEFAULT_UNIT")
            if du is not None and du.text == "internal_cp2k":
                value = Keyword.from_string(kw, "[angstrom] 1.23")
                assert "[angstrom] 1.23" in value.values or value.values == "[angstrom] 1.23"
                break
        else:
            pytest.skip("No keyword with internal_cp2k default unit found")


class TestIssue35DeprecatedKeywords:
    """Test deprecated keyword warning system."""

    def setup_method(self):
        """Clear registries before each test."""
        DEPRECATED_KEYWORDS.clear()
        DEPRECATED_SECTIONS.clear()

    def test_register_and_check_deprecated_keyword(self):
        """Registering and checking deprecated keyword should warn."""
        register_deprecated("OLD_KEYWORD", "MOTION/PRINT", "NEW_KEYWORD")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated("OLD_KEYWORD", "MOTION/PRINT")
            assert result is True
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedKeywordWarning)
            assert "NEW_KEYWORD" in str(w[0].message)

    def test_check_non_deprecated_keyword(self):
        """Non-deprecated keyword should not warn."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated("NORMAL_KEYWORD", "MOTION/PRINT")
            assert result is False
            our_warnings = [x for x in w if issubclass(x.category, (DeprecatedKeywordWarning, DeprecatedSectionWarning))]
            assert len(our_warnings) == 0

    def test_register_and_check_deprecated_section(self):
        """Registering and checking deprecated section should warn."""
        register_deprecated_section("OLD_SECTION", "MOTION", "NEW_SECTION")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated_section("OLD_SECTION", "MOTION")
            assert result is True
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedSectionWarning)

    def test_deprecated_keyword_warning_message(self):
        """Warning message should include keyword, section, and replacement."""
        register_deprecated("SOME_KW", "SECTION", "REPLACEMENT")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_deprecated("SOME_KW", "SECTION")
            msg = str(w[0].message)
            assert "SOME_KW" in msg
            assert "SECTION" in msg
            assert "REPLACEMENT" in msg

    def test_deprecated_keyword_without_replacement(self):
        """Deprecated keyword without replacement should still warn."""
        DEPRECATED_KEYWORDS["TEST::NOREPL"] = None

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated("NOREPL", "TEST")
            assert result is True
            assert "will be removed" in str(w[0].message)
