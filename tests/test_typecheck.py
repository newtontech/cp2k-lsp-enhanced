"""Tests for keyword value type-checking."""

import pathlib

from cp2k_input_tools.typecheck import (
    _get_schema_metadata,
    check_required_sections,
    extract_run_type,
    validate_enum,
    validate_text,
    validate_type,
    validate_unit_syntax,
)

TEST_DIR = pathlib.Path(__file__).resolve().parent


class TestValidateType:
    """Tests for basic type validation."""

    def test_integer_valid(self):
        assert validate_type("42", "integer") == (True, "")
        assert validate_type("-5", "integer") == (True, "")
        assert validate_type("0", "integer") == (True, "")

    def test_integer_invalid(self):
        is_valid, msg = validate_type("abc", "integer")
        assert not is_valid
        assert "integer" in msg.lower()

    def test_real_valid(self):
        assert validate_type("3.14", "real") == (True, "")
        assert validate_type("1.0e-5", "real") == (True, "")
        assert validate_type("-0.5", "real") == (True, "")

    def test_real_invalid(self):
        is_valid, msg = validate_type("abc", "real")
        assert not is_valid
        assert "real" in msg.lower()

    def test_logical_valid(self):
        assert validate_type("T", "logical") == (True, "")
        assert validate_type("FALSE", "logical") == (True, "")
        assert validate_type("yes", "logical") == (True, "")

    def test_logical_invalid(self):
        is_valid, msg = validate_type("MAYBE", "logical")
        assert not is_valid
        assert "logical" in msg.lower()

    def test_string_always_valid(self):
        assert validate_type("anything", "string") == (True, "")

    def test_empty_value(self):
        assert validate_type("", "integer") == (True, "")


class TestValidateEnum:
    """Tests for enum value validation."""

    def test_enum_valid(self):
        assert validate_enum("PBE", ["PBE", "B3LYP", "LDA"]) == (True, "")

    def test_enum_invalid(self):
        is_valid, msg = validate_enum("INVALID", ["PBE", "B3LYP", "LDA"])
        assert not is_valid
        assert "Invalid enum" in msg

    def test_enum_case_insensitive(self):
        assert validate_enum("pbe", ["PBE", "B3LYP"]) == (True, "")

    def test_enum_empty(self):
        assert validate_enum("", ["PBE"]) == (True, "")


class TestValidateUnitSyntax:
    """Tests for unit syntax validation."""

    def test_bracketed_unit(self):
        assert validate_unit_syntax("[angstrom] 5.0") == (True, "")

    def test_plain_number(self):
        assert validate_unit_syntax("100") == (True, "")


class TestExtractRunType:
    """Tests for RUN_TYPE extraction."""

    def test_extract_run_type_energy(self):
        text = "&GLOBAL\n  RUN_TYPE ENERGY\n&END GLOBAL\n"
        assert extract_run_type(text) == "ENERGY"

    def test_extract_run_type_geo_opt(self):
        text = "&GLOBAL\n  PROJECT test\n  RUN_TYPE GEO_OPT\n&END GLOBAL\n"
        assert extract_run_type(text) == "GEO_OPT"

    def test_no_run_type(self):
        text = "&GLOBAL\n  PROJECT test\n&END GLOBAL\n"
        assert extract_run_type(text) is None


class TestCheckRequiredSections:
    """Tests for required section detection."""

    def test_geo_opt_missing(self):
        text = "&GLOBAL\n  RUN_TYPE GEO_OPT\n&END GLOBAL\n"
        diags = check_required_sections(text, declared_run_type="GEO_OPT")
        assert len(diags) == 1
        assert "GEO_OPT" in diags[0].message

    def test_geo_opt_present(self):
        text = "&GLOBAL\n  RUN_TYPE GEO_OPT\n&END GLOBAL\n&GEO_OPT\n&END GEO_OPT\n"
        diags = check_required_sections(text, declared_run_type="GEO_OPT")
        assert len(diags) == 0

    def test_md_missing(self):
        text = "&GLOBAL\n  RUN_TYPE MD\n&END GLOBAL\n"
        diags = check_required_sections(text, declared_run_type="MD")
        assert len(diags) == 1

    def test_no_run_type(self):
        text = "&GLOBAL\n  PROJECT test\n&END GLOBAL\n"
        diags = check_required_sections(text, declared_run_type=None)
        assert len(diags) == 0


class TestValidateText:
    """Integration tests for full text validation."""

    def test_valid_input_no_errors(self):
        text = """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL
"""
        diags = validate_text(text)
        # Should not produce type errors for standard keywords
        type_errors = [d for d in diags if d.severity == "error"]
        assert len(type_errors) == 0

    def test_required_section_warning(self):
        text = """&GLOBAL
  RUN_TYPE GEO_OPT
&END GLOBAL
"""
        diags = validate_text(text)
        warnings = [d for d in diags if d.severity == "warning"]
        assert len(warnings) >= 1
        assert any("GEO_OPT" in w.message for w in warnings)

    def test_schema_metadata_loaded(self):
        meta = _get_schema_metadata()
        assert isinstance(meta, dict)
        assert len(meta) > 0
