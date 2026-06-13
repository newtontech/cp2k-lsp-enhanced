"""Tests for hover provider with manual URLs, provenance, and examples.

Tests cover:
- Manual URL generation for keywords and sections
- Provenance display in hover output
- Example snippets in hover
- Deprecation banners
- Enum truncation
"""

import pytest
from cp2k_lsp.agent_api.schema import (
    lookup_keyword_schema,
    lookup_section_schema,
)


def _create_hover_provider():
    from cp2k_lsp.features.hover import HoverProvider

    class MockServer:
        class workspace:
            @staticmethod
            def get_text_document(uri):
                class Doc:
                    lines = []
                return Doc()
    return HoverProvider(MockServer())


class TestManualUrlInHover:
    def test_keyword_hover_includes_manual_url(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "**Manual**" in hover
        assert "manual.cp2k.org" in hover

    def test_section_hover_includes_manual_url(self):
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "**Manual**" in hover
        assert "manual.cp2k.org" in hover

    def test_nested_section_hover_includes_manual_url(self):
        provider = _create_hover_provider()
        schema = lookup_section_schema("SCF")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "**Manual**" in hover
        assert "SCF" in hover

    def test_dft_section_manual_url(self):
        provider = _create_hover_provider()
        schema = lookup_section_schema("DFT")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "FORCE_EVAL" in hover
        assert "DFT" in hover


class TestProvenanceInHover:
    def test_keyword_hover_includes_provenance(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "*Source: CP2K 2024.1*" in hover

    def test_section_hover_includes_provenance(self):
        provider = _create_hover_provider()
        schema = lookup_section_schema("FORCE_EVAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "*Source: CP2K 2024.1*" in hover


class TestExampleInHover:
    def test_keyword_hover_includes_example(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "**Example**" in hover
        assert "```cp2k" in hover
        assert "RUN_TYPE ENERGY" in hover

    def test_section_hover_includes_example(self):
        provider = _create_hover_provider()
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        hover = provider._format_section_hover(schema)
        assert "**Example**" in hover
        assert "&GLOBAL" in hover

    def test_method_keyword_example(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("METHOD")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "METHOD GPW" in hover

    def test_element_keyword_example(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("ELEMENT")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "ELEMENT O" in hover

    def test_basis_set_keyword_example(self):
        provider = _create_hover_provider()
        schema = lookup_keyword_schema("BASIS_SET")
        assert schema is not None
        hover = provider._format_keyword_hover(schema)
        assert "BASIS_SET" in hover


class TestEnumTruncation:
    def test_enum_truncated_when_many_values(self):
        provider = _create_hover_provider()
        schema = {
            "name": "BIG_ENUM",
            "type": "enum",
            "description": "A keyword with many enum values.",
            "enum_values": [f"VALUE_{i}" for i in range(20)],
        }
        hover = provider._format_keyword_hover(schema)
        assert "and" in hover
        assert "more" in hover
        assert "10 more" in hover

    def test_enum_not_truncated_when_few_values(self):
        provider = _create_hover_provider()
        schema = {
            "name": "SMALL_ENUM",
            "type": "enum",
            "description": "A small enum.",
            "enum_values": ["A", "B", "C"],
        }
        hover = provider._format_keyword_hover(schema)
        assert "... and" not in hover


class TestDeprecationBanner:
    def test_deprecated_keyword_shows_warning(self):
        provider = _create_hover_provider()
        schema = {
            "name": "OLD_KEYWORD",
            "type": "string",
            "description": "An old keyword.",
            "deprecated": True,
            "deprecation_warning": "Use NEW_KEYWORD instead.",
        }
        hover = provider._format_keyword_hover(schema)
        assert "⚠️" in hover
        assert "Use NEW_KEYWORD instead." in hover

    def test_deprecated_section_shows_warning(self):
        provider = _create_hover_provider()
        schema = {
            "name": "OLD_SECTION",
            "description": "An old section.",
            "deprecated": True,
            "deprecation_warning": "Use NEW_SECTION instead.",
        }
        hover = provider._format_section_hover(schema)
        assert "⚠️" in hover
        assert "Use NEW_SECTION instead." in hover


class TestSchemaLookupManualUrls:
    def test_keyword_schema_has_manual_url(self):
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        assert "manual_url" in schema
        assert schema["manual_url"].startswith("https://manual.cp2k.org/")

    def test_section_schema_has_manual_url(self):
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        assert "manual_url" in schema
        assert schema["manual_url"].startswith("https://manual.cp2k.org/")

    def test_keyword_schema_has_provenance(self):
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        assert "provenance" in schema
        assert schema["provenance"]["source"] == "schema"
        assert schema["provenance"]["cp2k_version"] == "2024.1"

    def test_section_schema_has_provenance(self):
        schema = lookup_section_schema("DFT")
        assert schema is not None
        assert "provenance" in schema
        assert schema["provenance"]["source"] == "schema"

    def test_keyword_schema_has_example(self):
        schema = lookup_keyword_schema("METHOD")
        assert schema is not None
        assert "example" in schema
        assert "GPW" in schema["example"]
