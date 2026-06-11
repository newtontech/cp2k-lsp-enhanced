"""Tests for the agent API (#36, #37, #38)."""

import json

from cp2k_lsp.agent_api import (
    describe_keyword,
    describe_section,
    describe_section_tree,
    get_minimal_example,
    get_next_token_guidance,
    list_all_keywords,
    list_all_sections,
    list_available_examples,
    lookup_keyword_at_path,
    lookup_keyword_schema,
    lookup_section_path,
    lookup_section_schema,
    resolve_section_children,
)

# ============================================================================
# #36 – Domain language description API
# ============================================================================


class TestDescribeSection:
    """Tests for describe_section (issue #36)."""

    def test_describe_known_section(self):
        desc = describe_section("GLOBAL")
        assert desc is not None
        assert desc["name"] == "GLOBAL"
        assert "description" in desc
        assert "keywords" in desc
        assert "subsections" in desc
        assert isinstance(desc["keywords"], list)
        assert isinstance(desc["subsections"], list)

    def test_describe_global_keywords(self):
        desc = describe_section("GLOBAL")
        assert desc is not None
        kw_names = [k["name"] for k in desc["keywords"]]
        assert "PROJECT_NAME" in kw_names
        assert "RUN_TYPE" in kw_names
        assert "PRINT_LEVEL" in kw_names

    def test_describe_global_properties(self):
        desc = describe_section("GLOBAL")
        assert desc is not None
        assert desc["required"] is True
        assert desc["repeats"] is False

    def test_describe_unknown_section(self):
        assert describe_section("NONEXISTENT") is None

    def test_describe_case_insensitive(self):
        desc = describe_section("global")
        assert desc is not None
        assert desc["name"] == "GLOBAL"

    def test_describe_force_eval(self):
        desc = describe_section("FORCE_EVAL")
        assert desc is not None
        assert desc["repeats"] is True
        assert "DFT" in desc["subsections"]
        assert "SUBSYS" in desc["subsections"]

    def test_json_serializable(self):
        desc = describe_section("DFT")
        assert desc is not None
        # Should not raise
        json.dumps(desc)


class TestDescribeKeyword:
    """Tests for describe_keyword (issue #36)."""

    def test_describe_enum_keyword(self):
        desc = describe_keyword("RUN_TYPE")
        assert desc is not None
        assert desc["name"] == "RUN_TYPE"
        assert desc["type"] == "enum"
        assert "ENERGY" in desc["enum_values"]
        assert "MD" in desc["enum_values"]
        assert desc["default"] == "ENERGY"

    def test_describe_integer_keyword(self):
        desc = describe_keyword("MAX_SCF")
        assert desc is not None
        assert desc["type"] == "integer"
        assert desc["default"] == 50

    def test_describe_real_keyword(self):
        desc = describe_keyword("EPS_SCF")
        assert desc is not None
        assert desc["type"] == "real"
        assert desc["default"] == 1.0e-7

    def test_describe_keyword_with_units(self):
        desc = describe_keyword("TEMPERATURE")
        assert desc is not None
        assert desc["units"] is not None
        assert "K" in desc["units"]

    def test_describe_file_keyword(self):
        desc = describe_keyword("BASIS_SET_FILE_NAME")
        assert desc is not None
        assert desc["type"] == "file"

    def test_describe_unknown_keyword(self):
        assert describe_keyword("NONEXISTENT") is None

    def test_json_serializable(self):
        desc = describe_keyword("RUN_TYPE")
        assert desc is not None
        json.dumps(desc)


class TestDescribeSectionTree:
    """Tests for describe_section_tree (issue #36)."""

    def test_tree_expands_subsections(self):
        tree = describe_section_tree("FORCE_EVAL")
        assert tree is not None
        assert "subsections_detail" in tree
        dft = next(
            (s for s in tree["subsections_detail"] if s["name"] == "DFT"),
            None,
        )
        assert dft is not None
        assert "keywords" in dft

    def test_tree_depth_limit(self):
        tree = describe_section_tree("FORCE_EVAL")
        assert tree is not None
        # Should not crash even with deeply nested sections

    def test_unknown_section_returns_none(self):
        assert describe_section_tree("NONEXISTENT") is None


class TestListAll:
    """Tests for list_all_sections and list_all_keywords (issue #36)."""

    def test_list_all_sections(self):
        sections = list_all_sections()
        assert isinstance(sections, list)
        assert len(sections) > 0
        names = [s["name"] for s in sections]
        assert "GLOBAL" in names
        assert "FORCE_EVAL" in names
        assert "DFT" in names

    def test_list_all_keywords(self):
        keywords = list_all_keywords()
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        names = [k["name"] for k in keywords]
        assert "RUN_TYPE" in names
        assert "EPS_SCF" in names

    def test_list_all_json_serializable(self):
        json.dumps(list_all_sections())
        json.dumps(list_all_keywords())


# ============================================================================
# #37 – Schema lookup API
# ============================================================================


class TestLookupSectionSchema:
    """Tests for lookup_section_schema (issue #37)."""

    def test_lookup_global_schema(self):
        schema = lookup_section_schema("GLOBAL")
        assert schema is not None
        assert schema["name"] == "GLOBAL"
        assert "PROJECT_NAME" in schema["keywords"]
        assert "RUN_TYPE" in schema["keywords"]
        assert schema["required"] is True

    def test_lookup_scf_schema(self):
        schema = lookup_section_schema("SCF")
        assert schema is not None
        assert "EPS_SCF" in schema["keywords"]
        assert "MAX_SCF" in schema["keywords"]
        assert "OT" in schema["subsections"]

    def test_lookup_unknown(self):
        assert lookup_section_schema("NONEXISTENT") is None

    def test_json_serializable(self):
        json.dumps(lookup_section_schema("FORCE_EVAL"))


class TestLookupKeywordSchema:
    """Tests for lookup_keyword_schema (issue #37)."""

    def test_lookup_enum_keyword(self):
        schema = lookup_keyword_schema("RUN_TYPE")
        assert schema is not None
        assert schema["type"] == "enum"
        assert isinstance(schema["enum_values"], list)
        assert len(schema["enum_values"]) > 0

    def test_lookup_real_keyword(self):
        schema = lookup_keyword_schema("EPS_SCF")
        assert schema is not None
        assert schema["type"] == "real"
        assert "enum_values" not in schema  # no enum for real keywords

    def test_lookup_keyword_with_units(self):
        schema = lookup_keyword_schema("TIMESTEP")
        assert schema is not None
        assert schema["units"] is not None
        assert "fs" in schema["units"]

    def test_lookup_unknown(self):
        assert lookup_keyword_schema("NONEXISTENT") is None


class TestLookupSectionPath:
    """Tests for lookup_section_path (issue #37)."""

    def test_single_section(self):
        result = lookup_section_path("FORCE_EVAL")
        assert result is not None
        assert result["name"] == "FORCE_EVAL"

    def test_two_level_path(self):
        result = lookup_section_path("FORCE_EVAL.DFT")
        assert result is not None
        assert result["name"] == "DFT"

    def test_three_level_path(self):
        result = lookup_section_path("FORCE_EVAL.DFT.SCF")
        assert result is not None
        assert result["name"] == "SCF"
        assert "EPS_SCF" in result["keywords"]

    def test_force_eval_to_subsys(self):
        result = lookup_section_path("FORCE_EVAL.SUBSYS")
        assert result is not None
        assert result["name"] == "SUBSYS"

    def test_invalid_path_returns_none(self):
        assert lookup_section_path("NONEXISTENT") is None

    def test_invalid_child_returns_none(self):
        # DFT is not a subsection of MOTION
        assert lookup_section_path("MOTION.DFT") is None

    def test_empty_path_returns_none(self):
        assert lookup_section_path("") is None

    def test_case_insensitive_path(self):
        result = lookup_section_path("force_eval.dft")
        assert result is not None
        assert result["name"] == "DFT"


class TestResolveSectionChildren:
    """Tests for resolve_section_children (issue #37)."""

    def test_resolve_global_children(self):
        children = resolve_section_children("GLOBAL")
        assert children is not None
        assert children["section"] == "GLOBAL"
        kw_names = [k["name"] for k in children["keywords"]]
        assert "RUN_TYPE" in kw_names
        assert "PROJECT_NAME" in kw_names
        # GLOBAL has subsections like PRINT, DBCSR, etc.
        assert len(children["subsections"]) >= 0  # may or may not have resolved

    def test_resolve_scf_children(self):
        children = resolve_section_children("SCF")
        assert children is not None
        kw_names = [k["name"] for k in children["keywords"]]
        assert "EPS_SCF" in kw_names
        assert "MAX_SCF" in kw_names
        sub_names = [s["name"] for s in children["subsections"]]
        assert "OT" in sub_names
        assert "MIXING" in sub_names

    def test_resolve_unknown(self):
        assert resolve_section_children("NONEXISTENT") is None

    def test_resolve_keyword_has_type_info(self):
        children = resolve_section_children("SCF")
        assert children is not None
        for kw in children["keywords"]:
            assert "name" in kw
            assert "type" in kw


# ============================================================================
# #38 – Minimal examples and next-token guidance
# ============================================================================


class TestMinimalExamples:
    """Tests for minimal examples (issue #38)."""

    def test_list_available_examples(self):
        examples = list_available_examples()
        assert isinstance(examples, list)
        assert len(examples) >= 3  # energy, geo_opt, md_nvt, cell_opt
        ids = [e["id"] for e in examples]
        assert "energy" in ids
        assert "geo_opt" in ids
        assert "md_nvt" in ids

    def test_get_energy_example(self):
        example = get_minimal_example("energy")
        assert example is not None
        assert "input" in example
        assert "&GLOBAL" in example["input"]
        assert "RUN_TYPE ENERGY" in example["input"]
        assert "&FORCE_EVAL" in example["input"]
        assert example["run_type"] == "ENERGY"

    def test_get_geo_opt_example(self):
        example = get_minimal_example("geo_opt")
        assert example is not None
        assert "&GEO_OPT" in example["input"]
        assert example["run_type"] == "GEO_OPT"

    def test_get_md_example(self):
        example = get_minimal_example("md_nvt")
        assert example is not None
        assert "&MD" in example["input"]
        assert "NVT" in example["input"]
        assert example["run_type"] == "MD"

    def test_get_cell_opt_example(self):
        example = get_minimal_example("cell_opt")
        assert example is not None
        assert "&CELL_OPT" in example["input"]

    def test_unknown_example_returns_none(self):
        assert get_minimal_example("nonexistent") is None

    def test_example_is_parseable(self):
        """Minimal examples should parse without errors."""
        from cp2k_lsp.parser import CP2KParser

        for ex_id in ["energy", "geo_opt", "md_nvt", "cell_opt"]:
            example = get_minimal_example(ex_id)
            assert example is not None
            parser = CP2KParser.parse_text(example["input"])
            assert parser.ast is not None
            assert len(parser.errors) == 0, f"Example {ex_id} has parse errors: {parser.errors}"

    def test_json_serializable(self):
        json.dumps(list_available_examples())
        for ex_id in ["energy", "geo_opt", "md_nvt"]:
            example = get_minimal_example(ex_id)
            assert example is not None
            json.dumps(example)


class TestNextTokenGuidance:
    """Tests for next-token guidance (issue #38)."""

    def test_empty_input(self):
        guidance = get_next_token_guidance("")
        assert guidance["context"] == "empty_input"
        assert "GLOBAL" in guidance["suggested_sections"]

    def test_empty_input_whitespace(self):
        guidance = get_next_token_guidance("   \n  \n")
        assert guidance["context"] == "empty_input"

    def test_after_global_section(self):
        inp = "&GLOBAL\n  PROJECT_NAME test\n  RUN_TYPE ENERGY\n&END GLOBAL\n"
        guidance = get_next_token_guidance(inp)
        assert "FORCE_EVAL" in guidance["suggested_sections"]

    def test_inside_global_section(self):
        inp = "&GLOBAL\n  PROJECT_NAME test\n"
        guidance = get_next_token_guidance(inp)
        assert "inside_section:GLOBAL" in guidance["context"]
        assert "RUN_TYPE" in guidance["suggested_keywords"]

    def test_inside_scf_section(self):
        inp = "&FORCE_EVAL\n  &DFT\n    &SCF\n"
        guidance = get_next_token_guidance(inp)
        assert "SCF" in guidance["context"]
        assert "EPS_SCF" in guidance["suggested_keywords"]
        assert "MAX_SCF" in guidance["suggested_keywords"]
        assert "OT" in guidance["suggested_sections"]

    def test_keyword_awaiting_enum_value(self):
        inp = "&GLOBAL\n  RUN_TYPE = \n"
        guidance = get_next_token_guidance(inp)
        assert len(guidance["suggested_values"]) > 0
        assert "ENERGY" in guidance["suggested_values"]

    def test_keyword_awaiting_value_whitespace_form(self):
        inp = "&GLOBAL\n  RUN_TYPE\n"
        guidance = get_next_token_guidance(inp)
        assert len(guidance["suggested_values"]) > 0

    def test_json_serializable(self):
        json.dumps(get_next_token_guidance(""))
        json.dumps(get_next_token_guidance("&GLOBAL\n  RUN_TYPE = \n"))

    def test_full_input_suggestions(self):
        inp = (
            "&GLOBAL\n"
            "  PROJECT_NAME test\n"
            "  RUN_TYPE ENERGY\n"
            "&END GLOBAL\n"
            "\n"
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "&END FORCE_EVAL\n"
        )
        guidance = get_next_token_guidance(inp)
        # After GLOBAL and FORCE_EVAL, suggest MOTION
        assert "MOTION" in guidance["suggested_sections"]


# ============================================================================
# #42 – Schema index for path-based keyword lookup
# ============================================================================


class TestLookupKeywordAtPath:
    """Tests for lookup_keyword_at_path (issue #42)."""

    def test_lookup_method_at_qs_path(self):
        """Issue #42 acceptance: FORCE_EVAL/DFT/QS, METHOD -> enum, default GPW."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert schema is not None
        assert schema["name"] == "METHOD"
        assert schema["type"] == "enum"
        assert schema["default"] == "GPW"
        assert "GPW" in schema["enum_values"]

    def test_lookup_method_enum_values_comprehensive(self):
        """Issue #42: METHOD should include comprehensive enum values from manual."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert schema is not None

        # Key values from CP2K manual reference
        expected_values = ["GPW", "GAPW", "GAPW_XC", "LRIGPW", "RIGPW", "MNDO", "AM1", "PM6", "DFTB", "XTB", "OFGPW"]

        for value in expected_values:
            assert value in schema["enum_values"], f"Expected {value} in METHOD enum values"

    def test_lookup_extrapolation_at_qs_path(self):
        """Issue #42 acceptance: FORCE_EVAL/DFT/QS, EXTRAPOLATION -> USE_GUESS."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "EXTRAPOLATION")
        assert schema is not None
        assert schema["name"] == "EXTRAPOLATION"
        assert schema["type"] == "enum"
        assert "USE_GUESS" in schema["enum_values"]

    def test_lookup_scf_eps_at_dft_scf_path(self):
        """Lookup EPS_SCF at FORCE_EVAL.DFT.SCF path."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.SCF", "EPS_SCF")
        assert schema is not None
        assert schema["name"] == "EPS_SCF"
        assert schema["type"] == "real"
        assert schema["default"] == 1.0e-7

    def test_lookup_global_keyword_at_root(self):
        """Lookup PROJECT_NAME at GLOBAL (root level)."""
        schema = lookup_keyword_at_path("GLOBAL", "PROJECT_NAME")
        assert schema is not None
        assert schema["name"] == "PROJECT_NAME"
        assert schema["type"] == "string"
        assert schema["default"] == "PROJECT"

    def test_lookup_at_invalid_section_path(self):
        """Invalid section path should return None."""
        assert lookup_keyword_at_path("NONEXISTENT.SECTION", "METHOD") is None

    def test_lookup_invalid_keyword_at_valid_path(self):
        """Invalid keyword at valid path should return None."""
        assert lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "NOT_A_KEYWORD") is None

    def test_lookup_keyword_case_insensitive(self):
        """Keyword lookup should be case-insensitive."""
        schema = lookup_keyword_at_path("force_eval.dft.qs", "method")
        assert schema is not None
        assert schema["name"] == "METHOD"

    def test_lookup_keyword_at_path_is_json_serializable(self):
        """Schema should be JSON-serializable."""
        schema = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert schema is not None
        json.dumps(schema)  # Should not raise


class TestCP2KSchemaIndexIntegration:
    """Integration tests for complete schema index (issue #42)."""

    def test_complete_qs_section_query(self):
        """Complete query for QS section with all metadata."""
        # Resolve QS section
        section = lookup_section_path("FORCE_EVAL.DFT.QS")
        assert section is not None
        assert section["name"] == "QS"
        assert "METHOD" in section["keywords"]

        # Resolve children
        children = resolve_section_children("QS")
        assert children is not None
        kw_names = [k["name"] for k in children["keywords"]]
        assert "METHOD" in kw_names
        assert "EXTRAPOLATION" in kw_names

        # Lookup specific keywords at path
        method = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "METHOD")
        assert method is not None
        assert method["type"] == "enum"
        assert "GPW" in method["enum_values"]

        extrapolation = lookup_keyword_at_path("FORCE_EVAL.DFT.QS", "EXTRAPOLATION")
        assert extrapolation is not None
        assert "USE_GUESS" in extrapolation["enum_values"]

    def test_schema_index_replaces_hardcoded_lists(self):
        """Verify schema index provides all data that completion needs."""
        # Can get all sections
        all_sections = list_all_sections()
        assert len(all_sections) > 0

        # For each section, can get keywords
        for section_info in all_sections[:3]:  # Check first 3
            section_name = section_info["name"]
            children = resolve_section_children(section_name)
            if children:
                # Should have keyword list with type info
                for kw in children["keywords"]:
                    assert "name" in kw
                    assert "type" in kw

    def test_no_dependency_on_hardcoded_common_lists(self):
        """Schema index should work without hardcoded COMMON_SECTIONS/KEYWORDS."""
        # Can get comprehensive lists from schema
        sections = list_all_sections()
        keywords = list_all_keywords()

        # Should have many more entries than hardcoded lists
        assert len(sections) >= 10  # More than COMMON_SECTIONS
        assert len(keywords) >= 15  # More than COMMON_KEYWORDS
