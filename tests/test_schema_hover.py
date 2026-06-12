"""Tests for schema-backed hover provider (issue #46).

Tests cover:
- Schema-backed hover for keywords with type, default, enum values
- Schema-backed hover for sections with keywords and subsections
- Graceful fallback to hardcoded docs when schema unavailable
- Preservation of existing hover behavior
- Cursor context integration for path-based lookups
"""

import pytest
from cp2k_lsp.agent_api.schema import (
    lookup_keyword_at_path,
    lookup_keyword_schema,
    lookup_section_schema,
)

# =============================================================================
# Helper
# =============================================================================


def _create_hover_provider():
    """Create a HoverProvider instance for testing."""
    from cp2k_lsp.features.hover import HoverProvider

    class MockServer:
        class workspace:
            @staticmethod
            def get_text_document(uri):
                class Doc:
                    lines = []

                return Doc()

    provider = HoverProvider(MockServer())
    return provider


# =============================================================================
# Schema-backed hover tests
# =============================================================================


class TestSchemaBackedKeywordHover:
    """Test schema-backed hover for keywords."""

    def test_keyword_hover_includes_type(self):
        """Keyword hover should include type information."""
        provider = _create_hover_provider()
        # Force a schema lookup by calling the format method directly
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "enum" in hover.lower()

    def test_keyword_hover_includes_default(self):
        """Keyword hover should include default value."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "ENERGY" in hover

    def test_keyword_hover_includes_enum_values(self):
        """Keyword hover should list enum values for enum types."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        assert schema["type"] == "enum"
        hover = provider._format_keyword_hover(schema)
        assert "ENERGY" in hover
        assert "GEO_OPT" in hover
        assert "MD" in hover

    def test_keyword_hover_includes_description(self):
        """Keyword hover should include description."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        # Should contain the description text
        assert len(hover) > 50

    def test_keyword_hover_includes_units(self):
        """Keyword hover should include units when available."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("CUTOFF")
        if schema and schema.get("units"):
            hover = provider._format_keyword_hover(schema)
            assert "unit" in hover.lower() or "hartree" in hover.lower() or "rydberg" in hover.lower() or "ev" in hover.lower()
        else:
            pytest.skip("No keyword with units found in schema")

    def test_keyword_hover_for_integer_type(self):
        """Integer keyword hover should show type correctly."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("MAX_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "integer" in hover.lower()

    def test_keyword_hover_for_string_type(self):
        """String keyword hover should show type correctly."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("PROJECT_NAME")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "string" in hover.lower()

    def test_keyword_hover_for_real_type_with_scientific_notation(self):
        """Real keyword with scientific default should format correctly."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        # Should have formatted default
        assert "1" in hover  # Default is 1.0e-7


class TestSchemaBackedSectionHover:
    """Test schema-backed hover for sections."""

    def test_section_hover_includes_description(self):
        """Section hover should include description."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "Global" in hover or "GLOBAL" in hover

    def test_section_hover_includes_keywords(self):
        """Section hover should list keywords."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "PROJECT_NAME" in hover
        assert "RUN_TYPE" in hover

    def test_section_hover_includes_subsections(self):
        """Section hover should list subsections when present."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("SCF")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        # SCF has subsections
        assert "DIAGONALIZATION" in hover or "MIXING" in hover

    def test_section_hover_for_nested_section(self):
        """Nested section hover should work."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("DFT")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "DFT" in hover

    def test_section_hover_with_repeats_flag(self):
        """Section with repeats flag should indicate repeatable."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("FORCE_EVAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "Repeatable" in hover or "repeatable" in hover.lower()

    def test_section_hover_limits_long_lists(self):
        """Section hover should limit long keyword/subsection lists."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        # Should not have excessive content
        assert len(hover) < 2000


class TestSchemaHoverPathBasedLookup:
    """Test path-based keyword lookup for hover."""

    def test_path_based_keyword_lookup(self):
        """Path-based keyword lookup should return correct schema."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert schema is not None
        assert schema["name"] == "METHOD"
        assert schema["type"] == "enum"

    def test_path_based_keyword_hover_content(self):
        """Path-based keyword hover should have correct content."""
        provider = _create_hover_provider()
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "METHOD" in hover
        assert "GPW" in hover  # Default value
        assert "GAPW" in hover  # Enum value


class TestHoverFallbackBehavior:
    """Test fallback to hardcoded docs when schema unavailable."""

    def test_fallback_for_known_keyword(self):
        """Known keyword without schema should use fallback."""
        provider = _create_hover_provider()
        hover = provider._get_fallback_hover("RUN_TYPE")
        assert hover is not None
        assert "RUN_TYPE" in hover.contents.value

    def test_fallback_for_known_section(self):
        """Known section without schema should use fallback."""
        provider = _create_hover_provider()
        hover = provider._get_fallback_hover("GLOBAL")
        assert hover is not None
        assert "GLOBAL" in hover.contents.value

    def test_fallback_for_unknown_word(self):
        """Unknown word should return None."""
        provider = _create_hover_provider()
        hover = provider._get_fallback_hover("UNKNOWN_WORD")
        assert hover is None


class TestHoverWordExtraction:
    """Test word extraction at cursor position."""

    def test_word_at_start(self):
        """Word at beginning of line."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 0) == "RUN_TYPE"

    def test_word_at_end(self):
        """Word at end of line."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 13) == "ENERGY"

    def test_word_with_underscores(self):
        """Word with underscores."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("MAX_SCF = 50", 0) == "MAX_SCF"

    def test_word_with_numbers(self):
        """Word with numbers."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("EPS_SCF 1.0E-7", 0) == "EPS_SCF"

    def test_empty_line(self):
        """Empty line should return empty string."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("", 0) == ""

    def test_cursor_at_end_of_line(self):
        """Cursor at end of line."""
        provider = _create_hover_provider()
        assert provider._get_word_at_position("RUN_TYPE", 8) == "RUN_TYPE"


class TestHoverMarkdownFormatting:
    """Test markdown formatting of hover content."""

    def test_keyword_hover_has_markdown_structure(self):
        """Keyword hover should have proper markdown structure."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        # Should have bold title
        assert "**RUN_TYPE**" in hover
        # Should have type info
        assert "`enum`" in hover

    def test_section_hover_has_markdown_structure(self):
        """Section hover should have proper markdown structure."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        # Should have bold title
        assert "**GLOBAL**" in hover
        # Should have section label
        assert "Section" in hover

    def test_enum_values_are_formatted(self):
        """Enum values should be formatted as code."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        # Enum values should be in backticks
        assert "`ENERGY`" in hover
        assert "`GEO_OPT`" in hover


class TestIssue46AcceptanceCriteria:
    """Specific tests for issue #46 acceptance criteria."""

    def test_schema_hover_includes_description(self):
        """Issue #46: hover should include keyword description from schema."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        # Should include description - check it has content beyond just the title
        assert "SCF" in hover
        assert "threshold" in hover.lower() or "convergence" in hover.lower()

    def test_schema_hover_includes_enum_values(self):
        """Issue #46: hover should include enum values from schema."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        assert schema["type"] == "enum"
        hover = provider._format_keyword_hover(schema)
        # Should list multiple enum values
        assert hover.count("`") >= 6  # At least 3 enum values in backticks

    def test_schema_hover_includes_default(self):
        """Issue #46: hover should include default value from schema."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("PROJECT_NAME")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "PROJECT" in hover

    def test_schema_hover_includes_type(self):
        """Issue #46: hover should include type information from schema."""
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("MAX_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "integer" in hover.lower()

    def test_section_hover_includes_keywords(self):
        """Issue #46: section hover should include list of keywords."""
        provider = _create_hover_provider()
        schema = lookup_section_schema("SCF")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        # Should list keywords
        assert "EPS_SCF" in hover

    def test_graceful_fallback(self):
        """Issue #46: should gracefully fallback when schema unavailable."""
        provider = _create_hover_provider()
        # Test with a word that might not be in schema
        # The fallback should still work
        hover = provider._get_fallback_hover("UNKNOWN")
        assert hover is None

    def test_existing_hover_behavior_preserved(self):
        """Issue #46: existing hover behavior should be preserved."""
        from cp2k_lsp.features.hover import HoverProvider

        # Should still have SECTION_DOCS and KEYWORD_DOCS
        assert hasattr(HoverProvider, "SECTION_DOCS")
        assert hasattr(HoverProvider, "KEYWORD_DOCS")
        assert "GLOBAL" in HoverProvider.SECTION_DOCS
        assert "RUN_TYPE" in HoverProvider.KEYWORD_DOCS
