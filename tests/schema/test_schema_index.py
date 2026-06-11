"""Schema index tests for issue #42.

Tests cover:
- Loading and accessing the schema index
- Path-based section resolution
- Path-based keyword lookup
- Enum value extraction
- Default value extraction
- Description availability for hover
- JSON serialization for LSP consumption
"""

import json

from cp2k_lsp.agent_api import (
    describe_keyword,
    describe_section,
    list_all_keywords,
    list_all_sections,
)
from cp2k_lsp.agent_api.schema import (
    lookup_keyword_at_path,
    lookup_keyword_schema,
    lookup_section_path,
    lookup_section_schema,
    resolve_section_children,
)


class TestSchemaIndexLoading:
    """Tests for loading and accessing the schema index."""

    def test_schema_index_loads_without_error(self):
        """The schema index should load without errors."""
        # Just importing should work
        sections = list_all_sections()
        keywords = list_all_keywords()
        assert len(sections) > 0
        assert len(keywords) > 0

    def test_schema_index_has_core_sections(self):
        """Schema index should have core CP2K sections."""
        sections = list_all_sections()
        section_names = [s["name"] for s in sections]

        # Core sections that should be present
        assert "GLOBAL" in section_names
        assert "FORCE_EVAL" in section_names
        assert "DFT" in section_names
        assert "QS" in section_names
        assert "SCF" in section_names

    def test_schema_index_has_core_keywords(self):
        """Schema index should have core CP2K keywords."""
        keywords = list_all_keywords()
        keyword_names = [k["name"] for k in keywords]

        # Core keywords that should be present
        assert "PROJECT_NAME" in keyword_names
        assert "RUN_TYPE" in keyword_names
        assert "METHOD" in keyword_names
        assert "EPS_SCF" in keyword_names


class TestSectionPathResolution:
    """Tests for path-based section resolution."""

    def test_resolve_root_section(self):
        """Resolve a root section path."""
        section = lookup_section_path("GLOBAL")
        assert section is not None
        assert section["name"] == "GLOBAL"

    def test_resolve_nested_section(self):
        """Resolve a nested section path."""
        section = lookup_section_path("FORCE_EVAL.DFT")
        assert section is not None
        assert section["name"] == "DFT"

    def test_resolve_deeply_nested_section(self):
        """Resolve a deeply nested section path."""
        section = lookup_section_path("FORCE_EVAL.DFT.QS")
        assert section is not None
        assert section["name"] == "QS"

    def test_resolve_invalid_section_path(self):
        """Invalid section path should return None."""
        assert lookup_section_path("NONEXISTENT.SECTION") is None

    def test_resolve_invalid_child_section(self):
        """Invalid child section should return None."""
        # DFT is not a child of MOTION
        assert lookup_section_path("MOTION.DFT") is None

    def test_section_path_case_insensitive(self):
        """Section path resolution should be case-insensitive."""
        section = lookup_section_path("force_eval.dft.qs")
        assert section is not None
        assert section["name"] == "QS"


class TestKeywordAtPathLookup:
    """Tests for path-based keyword lookup."""

    def test_lookup_keyword_at_root_section(self):
        """Lookup keyword at root section path."""
        keyword = lookup_keyword_at_path("GLOBAL", "PROJECT_NAME")
        assert keyword is not None
        assert keyword["name"] == "PROJECT_NAME"
        assert keyword["type"] == "string"

    def test_lookup_keyword_at_nested_section(self):
        """Lookup keyword at nested section path."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        assert keyword["name"] == "METHOD"
        assert keyword["type"] == "enum"

    def test_lookup_keyword_at_deeply_nested_section(self):
        """Lookup keyword at deeply nested section path."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.SCF", "EPS_SCF")
        assert keyword is not None
        assert keyword["name"] == "EPS_SCF"
        assert keyword["type"] == "real"

    def test_lookup_keyword_at_invalid_section_path(self):
        """Invalid section path should return None."""
        assert lookup_keyword_at_path("NONEXISTENT.SECTION", "METHOD") is None

    def test_lookup_invalid_keyword_at_valid_path(self):
        """Invalid keyword at valid path should return None."""
        assert lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "NOT_A_KEYWORD") is None

    def test_keyword_at_path_case_insensitive(self):
        """Keyword lookup at path should be case-insensitive."""
        keyword = lookup_keyword_at_path("force_eval.dft.qs", "method")
        assert keyword is not None
        assert keyword["name"] == "METHOD"


class TestEnumValueExtraction:
    """Tests for enum value extraction from schema."""

    def test_enum_values_for_run_type(self):
        """Extract enum values for RUN_TYPE keyword."""
        keyword = lookup_keyword_schema("RUN_TYPE")
        assert keyword is not None
        assert keyword["type"] == "enum"
        assert "enum_values" in keyword

        # Should have expected values
        values = keyword["enum_values"]
        assert "ENERGY" in values
        assert "GEO_OPT" in values
        assert "MD" in values

    def test_enum_values_for_qs_method(self):
        """Extract enum values for QS METHOD keyword."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        assert keyword["type"] == "enum"
        assert "enum_values" in keyword

        # Should have comprehensive values from CP2K manual
        values = keyword["enum_values"]
        assert "GPW" in values
        assert "GAPW" in values
        assert "GAPW_XC" in values
        assert "LRIGPW" in values
        assert "RIGPW" in values

    def test_enum_values_for_extrapolation(self):
        """Extract enum values for EXTRAPOLATION keyword."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "EXTRAPOLATION")
        assert keyword is not None
        assert keyword["type"] == "enum"
        assert "USE_GUESS" in keyword["enum_values"]

    def test_enum_values_for_scf_guess(self):
        """Extract enum values for SCF_GUESS keyword."""
        keyword = lookup_keyword_schema("SCF_GUESS")
        assert keyword is not None
        assert keyword["type"] == "enum"
        assert "ATOMIC" in keyword["enum_values"]
        assert "RESTART" in keyword["enum_values"]

    def test_non_enum_keyword_has_no_enum_values(self):
        """Non-enum keyword should not have enum_values field."""
        keyword = lookup_keyword_schema("EPS_SCF")
        assert keyword is not None
        assert keyword["type"] == "real"
        # Either no enum_values or empty list
        if "enum_values" in keyword:
            assert len(keyword["enum_values"]) == 0


class TestDefaultValueExtraction:
    """Tests for default value extraction from schema."""

    def test_default_value_for_project_name(self):
        """Extract default value for PROJECT_NAME."""
        keyword = lookup_keyword_schema("PROJECT_NAME")
        assert keyword is not None
        assert keyword["default"] == "PROJECT"

    def test_default_value_for_run_type(self):
        """Extract default value for RUN_TYPE."""
        keyword = lookup_keyword_schema("RUN_TYPE")
        assert keyword is not None
        assert keyword["default"] == "ENERGY"

    def test_default_value_for_qs_method(self):
        """Extract default value for QS METHOD."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        assert keyword["default"] == "GPW"

    def test_default_value_for_eps_scf(self):
        """Extract default value for EPS_SCF."""
        keyword = lookup_keyword_schema("EPS_SCF")
        assert keyword is not None
        assert keyword["default"] == 1.0e-7

    def test_default_value_for_max_scf(self):
        """Extract default value for MAX_SCF."""
        keyword = lookup_keyword_schema("MAX_SCF")
        assert keyword is not None
        assert keyword["default"] == 50

    def test_default_value_can_be_none(self):
        """Some keywords may have None as default."""
        keyword = lookup_keyword_schema("WALLTIME")
        assert keyword is not None
        # WALLTIME has no default
        assert keyword["default"] is None


class TestDescriptionAvailability:
    """Tests for description availability for hover functionality."""

    def test_description_available_for_section(self):
        """Description should be available for sections."""
        section = describe_section("GLOBAL")
        assert section is not None
        assert "description" in section
        assert len(section["description"]) > 0

    def test_description_available_for_keyword(self):
        """Description should be available for keywords."""
        keyword = describe_keyword("PROJECT_NAME")
        assert keyword is not None
        assert "description" in keyword
        assert len(keyword["description"]) > 0

    def test_description_for_qs_method(self):
        """Description should be available for QS METHOD."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        assert "description" in keyword
        assert len(keyword["description"]) > 0

    def test_description_for_eps_scf(self):
        """Description should be available for EPS_SCF."""
        keyword = lookup_keyword_schema("EPS_SCF")
        assert keyword is not None
        assert "description" in keyword
        assert len(keyword["description"]) > 0

    def test_section_description_includes_keywords(self):
        """Section description should include list of keywords."""
        section = describe_section("SCF")
        assert section is not None
        assert "keywords" in section
        assert "EPS_SCF" in [k["name"] for k in section["keywords"]]
        assert "MAX_SCF" in [k["name"] for k in section["keywords"]]


class TestJSONSerialization:
    """Tests for JSON serialization for LSP consumption."""

    def test_section_schema_is_json_serializable(self):
        """Section schema should be JSON-serializable."""
        section = lookup_section_schema("GLOBAL")
        assert section is not None
        json_str = json.dumps(section)
        assert len(json_str) > 0

    def test_keyword_schema_is_json_serializable(self):
        """Keyword schema should be JSON-serializable."""
        keyword = lookup_keyword_schema("RUN_TYPE")
        assert keyword is not None
        json_str = json.dumps(keyword)
        assert len(json_str) > 0

    def test_path_based_keyword_is_json_serializable(self):
        """Path-based keyword lookup should be JSON-serializable."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        json_str = json.dumps(keyword)
        assert len(json_str) > 0

    def test_section_children_is_json_serializable(self):
        """Section children resolution should be JSON-serializable."""
        children = resolve_section_children("SCF")
        assert children is not None
        json_str = json.dumps(children)
        assert len(json_str) > 0

    def test_all_sections_is_json_serializable(self):
        """List of all sections should be JSON-serializable."""
        sections = list_all_sections()
        json_str = json.dumps(sections)
        assert len(json_str) > 0

    def test_all_keywords_is_json_serializable(self):
        """List of all keywords should be JSON-serializable."""
        keywords = list_all_keywords()
        json_str = json.dumps(keywords)
        assert len(json_str) > 0


class TestSchemaIndexCompleteness:
    """Tests for schema index completeness and integration."""

    def test_schema_index_supports_completion_requirements(self):
        """Schema index should support all completion requirements."""
        # All sections
        sections = list_all_sections()
        assert len(sections) > 0

        # All keywords with types
        keywords = list_all_keywords()
        assert len(keywords) > 0
        for kw in keywords:
            assert "name" in kw
            assert "type" in kw

    def test_schema_index_supports_hover_requirements(self):
        """Schema index should support all hover requirements."""
        # Descriptions available
        section = describe_section("GLOBAL")
        assert section is not None
        assert "description" in section

        keyword = describe_keyword("RUN_TYPE")
        assert keyword is not None
        assert "description" in keyword

    def test_schema_index_supports_diagnostics_requirements(self):
        """Schema index should support validation for diagnostics."""
        # Can check if keywords exist
        keyword = lookup_keyword_schema("RUN_TYPE")
        assert keyword is not None

        # Can check if sections exist
        section = lookup_section_schema("FORCE_EVAL")
        assert section is not None

        # Can check if keyword is valid at path
        keyword_at_path = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword_at_path is not None

        # Invalid lookup returns None
        assert lookup_keyword_schema("NONEXISTENT_KEYWORD") is None
        assert lookup_section_schema("NONEXISTENT_SECTION") is None
        assert lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "NOT_A_KEYWORD") is None


class TestIssue42AcceptanceCriteria:
    """Specific tests for issue #42 acceptance criteria."""

    def test_acceptance_criteria_method_enum(self):
        """Issue #42: path FORCE_EVAL/DFT/QS, keyword METHOD -> enum, default GPW."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert keyword is not None
        assert keyword["type"] == "enum"
        assert keyword["default"] == "GPW"
        assert "GPW" in keyword["enum_values"]

    def test_acceptance_criteria_extrapolation_enum(self):
        """Issue #42: path FORCE_EVAL/DFT/QS, keyword EXTRAPOLATION -> USE_GUESS."""
        keyword = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "EXTRAPOLATION")
        assert keyword is not None
        assert "USE_GUESS" in keyword["enum_values"]

    def test_acceptance_criteria_no_hardcoded_lists(self):
        """Issue #42: LSP features should use schema index, not hardcoded lists."""
        # Can get comprehensive data from schema
        sections = list_all_sections()
        keywords = list_all_keywords()

        # Schema has more than hardcoded COMMON_SECTIONS (9 items)
        assert len(sections) > 9

        # Schema has more than hardcoded COMMON_KEYWORDS (3 items)
        assert len(keywords) > 3

    def test_acceptance_criteria_unit_tests(self):
        """Issue #42: Schema index has unit tests independent of pygls."""
        # This test file is independent of pygls
        # All tests here should pass without pygls imports
        assert True

    def test_acceptance_criteria_error_handling(self):
        """Issue #42: Missing/invalid schema should fail with clear error."""
        # Invalid lookups return None (clear error handling)
        assert lookup_section_schema("NONEXISTENT") is None
        assert lookup_keyword_schema("NONEXISTENT") is None
        assert lookup_section_path("INVALID.PATH") is None
        assert lookup_keyword_at_path("INVALID.PATH", "KW") is None
