"""
Tests for CP2K input schema index.

TDD: Tests written first, implementation to follow.
"""
import pytest
from dataclasses import asdict

from cp2k_input_tools.schema_index import (
    CP2KSchemaIndex,
    SectionSpec,
    KeywordSpec,
    get_schema_index,
)


@pytest.mark.unit
class TestCP2KSchemaIndex:
    """Test the CP2K schema index functionality."""

    def test_schema_index_loads_without_error(self) -> None:
        """Test that the schema index can be loaded without raising an error."""
        index = CP2KSchemaIndex()
        assert index is not None
        assert index.loaded

    def test_get_global_section(self) -> None:
        """Test that we can retrieve the GLOBAL section spec."""
        index = get_schema_index()
        section = index.get_section(("GLOBAL",))
        assert section is not None
        assert section.name == "GLOBAL"
        assert section.parent_path == ()

    def test_get_force_eval_section(self) -> None:
        """Test that we can retrieve FORCE_EVAL section."""
        index = get_schema_index()
        section = index.get_section(("FORCE_EVAL",))
        assert section is not None
        assert section.name == "FORCE_EVAL"

    def test_get_force_eval_dft_qs_section(self) -> None:
        """Test nested section path resolution."""
        index = get_schema_index()
        section = index.get_section(("FORCE_EVAL", "DFT", "QS"))
        assert section is not None
        assert section.name == "QS"
        assert section.parent_path == ("FORCE_EVAL", "DFT")

    def test_get_nonexistent_section_returns_none(self) -> None:
        """Test that asking for a nonexistent section returns None."""
        index = get_schema_index()
        section = index.get_section(("NONEXISTENT", "SECTION"))
        assert section is None

    def test_get_child_sections_of_global(self) -> None:
        """Test getting child sections of GLOBAL."""
        index = get_schema_index()
        children = index.get_child_sections(("GLOBAL",))
        assert len(children) > 0
        # Should have sections like PRINT, TIMINGS, etc.
        child_names = {c.name for c in children}
        assert "PRINT" in child_names or "TIMINGS" in child_names

    def test_get_child_sections_of_force_eval(self) -> None:
        """Test getting child sections of FORCE_EVAL."""
        index = get_schema_index()
        children = index.get_child_sections(("FORCE_EVAL",))
        assert len(children) > 0
        child_names = {c.name for c in children}
        assert "DFT" in child_names

    def test_get_child_sections_of_force_eval_dft(self) -> None:
        """Test getting child sections of FORCE_EVAL/DFT."""
        index = get_schema_index()
        children = index.get_child_sections(("FORCE_EVAL", "DFT"))
        assert len(children) > 0
        child_names = {c.name for c in children}
        # Should include QS, SCF, KPOINTS, etc.
        assert "QS" in child_names
        assert "SCF" in child_names

    def test_get_keywords_of_qs(self) -> None:
        """Test getting keywords of QS section."""
        index = get_schema_index()
        keywords = index.get_keywords(("FORCE_EVAL", "DFT", "QS"))
        assert len(keywords) > 0
        keyword_names = {k.name for k in keywords}
        assert "METHOD" in keyword_names
        assert "EXTRAPOLATION" in keyword_names

    def test_get_method_keyword_spec(self) -> None:
        """Test getting the METHOD keyword spec from QS section."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        assert keyword is not None
        assert keyword.name == "METHOD"
        assert keyword.section_path == ("FORCE_EVAL", "DFT", "QS")
        # METHOD is an enum keyword
        assert keyword.type_name == "keyword"  # enum type

    def test_method_keyword_has_gpw_enum_value(self) -> None:
        """Test that QS/METHOD has GPW as an enum value."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        assert keyword is not None
        assert keyword.enum_values is not None
        assert "GPW" in keyword.enum_values
        # Should also have other common values
        assert "GAPW" in keyword.enum_values
        assert "GAPW_XC" in keyword.enum_values

    def test_method_keyword_default_value(self) -> None:
        """Test that QS/METHOD has GPW as default value."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        assert keyword is not None
        # GPW should be the default
        if keyword.default_value:
            assert "GPW" in keyword.default_value or keyword.default_value == "GPW"

    def test_get_nonexistent_keyword_returns_none(self) -> None:
        """Test that asking for a nonexistent keyword returns None."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "BOGUS_KEYWORD")
        assert keyword is None

    def test_get_keyword_from_nonexistent_section_returns_none(self) -> None:
        """Test keyword lookup from nonexistent section returns None."""
        index = get_schema_index()
        keyword = index.get_keyword(("NONEXISTENT", "SECTION"), "METHOD")
        assert keyword is None

    def test_section_spec_has_description(self) -> None:
        """Test that SectionSpec includes description."""
        index = get_schema_index()
        section = index.get_section(("GLOBAL",))
        assert section is not None
        # Description may be empty string but should exist
        assert hasattr(section, "description")

    def test_keyword_spec_has_description(self) -> None:
        """Test that KeywordSpec includes description."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        assert keyword is not None
        assert hasattr(keyword, "description")

    def test_keyword_spec_has_usage_info(self) -> None:
        """Test that KeywordSpec includes usage information."""
        index = get_schema_index()
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        assert keyword is not None
        assert hasattr(keyword, "usage")

    def test_get_section_returns_cached_instance(self) -> None:
        """Test that get_section returns a cached spec (not creating new objects)."""
        index = get_schema_index()
        section1 = index.get_section(("GLOBAL",))
        section2 = index.get_section(("GLOBAL",))
        # Same object reference (cached)
        assert section1 is section2

    def test_get_keyword_returns_cached_instance(self) -> None:
        """Test that get_keyword returns a cached spec."""
        index = get_schema_index()
        keyword1 = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        keyword2 = index.get_keyword(("FORCE_EVAL", "DFT", "QS"), "METHOD")
        # Same object reference (cached)
        assert keyword1 is keyword2

    def test_logical_keyword_type(self) -> None:
        """Test that logical keywords have correct type."""
        index = get_schema_index()
        # UKS is a logical keyword in DFT
        keyword = index.get_keyword(("FORCE_EVAL", "DFT"), "UKS")
        assert keyword is not None
        assert keyword.type_name in ("logical", "_LOGICAL")

    def test_integer_keyword_type(self) -> None:
        """Test that integer keywords have correct type."""
        index = get_schema_index()
        # MAX_SCF is an integer keyword in SCF
        keyword = index.get_keyword(("FORCE_EVAL", "DFT", "SCF"), "MAX_SCF")
        assert keyword is not None
        assert keyword.type_name in ("integer", "_INTEGER")

    def test_section_has_repeats_info(self) -> None:
        """Test that SectionSpec includes repeats information."""
        index = get_schema_index()
        # KIND sections can repeat
        section = index.get_section(("FORCE_EVAL", "SUBSYS"))
        if section is not None:
            assert hasattr(section, "repeats")

    def test_keyword_has_repeats_info(self) -> None:
        """Test that KeywordSpec includes repeats information."""
        index = get_schema_index()
        # BASIS_SET_FILE_NAME can repeat
        keyword = index.get_keyword(("FORCE_EVAL", "DFT"), "BASIS_SET_FILE_NAME")
        assert keyword is not None
        assert hasattr(keyword, "repeats")

    def test_index_has_total_counts(self) -> None:
        """Test that the index reports total section/keyword counts."""
        index = get_schema_index()
        assert index.total_sections > 1000  # Should have thousands of sections
        assert index.total_keywords > 10000  # Should have tens of thousands of keywords

    def test_get_schema_index_returns_singleton(self) -> None:
        """Test that get_schema_index returns the same singleton instance."""
        index1 = get_schema_index()
        index2 = get_schema_index()
        assert index1 is index2

    def test_top_level_sections_count(self) -> None:
        """Test that we can get top-level section count."""
        index = get_schema_index()
        children = index.get_child_sections(())  # Empty path = root
        # Should have at least GLOBAL, FORCE_EVAL, MOTION
        assert len(children) >= 3
        names = {c.name for c in children}
        assert "GLOBAL" in names
        assert "FORCE_EVAL" in names
        assert "MOTION" in names
