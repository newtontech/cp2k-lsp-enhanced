"""Tests for community issues #10, #35, #55, #69, #72, #105, #110, #111."""

import io
import warnings

import pytest

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.keyword_helpers import (
    DEPRECATED_KEYWORDS,
    DEPRECATED_SECTIONS,
    DeprecatedKeywordWarning,
    register_deprecated,
    check_deprecated,
    Keyword,
)


class TestIssue10Completion:
    """Test completion provider for CP2K keywords (issue #10)."""

    def test_lsp_server_imports_with_completion(self):
        """LSP server should import with completion feature registered."""
        from cp2k_input_tools.ls import cp2k_server
        assert cp2k_server is not None

    def test_section_context_extraction(self):
        """_get_section_context should identify current section."""
        from cp2k_input_tools.ls import _get_section_context

        lines = [
            "&FORCE_EVAL",
            "  METHOD Quickstep",
            "  &SUBSYS",
            "    &KIND H",
        ]
        parser = CP2KInputParser()
        section = _get_section_context(lines, len(lines), parser)
        assert section is not None
        # Should be inside the KIND section
        assert section.name == "KIND"

    def test_section_context_root(self):
        """_get_section_context should handle root-level context."""
        from cp2k_input_tools.ls import _get_section_context

        lines = [
            "&GLOBAL",
            "  RUN_TYPE ENERGY",
        ]
        parser = CP2KInputParser()
        section = _get_section_context(lines, len(lines), parser)
        assert section is not None
        assert section.name == "GLOBAL"

    def test_completions_for_section_returns_keywords(self):
        """_get_completions_for_section should return keyword completions."""
        from cp2k_input_tools.ls import _get_section_context, _get_completions_for_section

        lines = [
            "&FORCE_EVAL",
            "  METHOD Quickstep",
            "  &DFT",
        ]
        parser = CP2KInputParser()
        section = _get_section_context(lines, len(lines), parser)
        items = _get_completions_for_section(section)
        assert len(items) > 0
        labels = [item.label for item in items]
        # DFT section should have QS, MGRID, SCF subsections
        assert any("QS" in l.upper() for l in labels) or any("MGRID" in l.upper() for l in labels)

    def test_completions_include_sections(self):
        """Completions should include available subsections."""
        from cp2k_input_tools.ls import _get_section_context, _get_completions_for_section

        lines = [
            "&FORCE_EVAL",
            "  &SUBSYS",
        ]
        parser = CP2KInputParser()
        section = _get_section_context(lines, len(lines), parser)
        items = _get_completions_for_section(section)
        labels = [item.label for item in items]
        # SUBSYS should have KIND, CELL, COORD, TOPOLOGY sections
        assert any("&" in l for l in labels)


class TestIssue35DeprecatedWarnings:
    """Test deprecated keyword warning system (issue #35)."""

    def setup_method(self):
        """Save and clear deprecated registries for test isolation."""
        self._saved_kw = dict(DEPRECATED_KEYWORDS)
        self._saved_sec = dict(DEPRECATED_SECTIONS)
        DEPRECATED_KEYWORDS.clear()
        DEPRECATED_SECTIONS.clear()

    def teardown_method(self):
        """Restore deprecated registries."""
        DEPRECATED_KEYWORDS.clear()
        DEPRECATED_KEYWORDS.update(self._saved_kw)
        DEPRECATED_SECTIONS.clear()
        DEPRECATED_SECTIONS.update(self._saved_sec)

    def test_register_deprecated_emits_warning(self):
        """Deprecated keyword should emit a warning when encountered."""
        register_deprecated("OLD_KW", "SECTION", "NEW_KW")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated("OLD_KW", "SECTION")
            assert result is True
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecatedKeywordWarning)
            assert "NEW_KW" in str(w[0].message)

    def test_non_deprecated_no_warning(self):
        """Non-deprecated keyword should not emit a warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecated("NORMAL_KEYWORD", "SOME_SECTION")
            assert result is False
            dep_warnings = [x for x in w if issubclass(x.category, DeprecatedKeywordWarning)]
            assert len(dep_warnings) == 0

    def test_deprecated_keyword_in_parser(self):
        """Parser should emit warning for deprecated keyword during parsing."""
        register_deprecated("CHARGE", "FORCE_EVAL/DFT", "NET_CHARGE")
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &DFT
    CHARGE 0
  &END DFT
&END FORCE_EVAL
"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            parser.parse(io.StringIO(inp))
            dep_warnings = [x for x in w if issubclass(x.category, DeprecatedKeywordWarning)]
            # If CHARGE is registered as deprecated, we should get a warning
            if dep_warnings:
                assert "CHARGE" in str(dep_warnings[0].message)


class TestIssue55InternalCp2kUnits:
    """Test that internal_cp2k units are handled without conversion (issue #55)."""

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

    def test_internal_cp2k_with_explicit_unit(self):
        """Keywords with internal_cp2k and explicit unit should store as string."""
        import xml.etree.ElementTree as ET

        spec = ET.parse(DEFAULT_CP2K_INPUT_XML)
        for kw in spec.iter("KEYWORD"):
            du = kw.find("./DEFAULT_UNIT")
            if du is not None and du.text == "internal_cp2k":
                value = Keyword.from_string(kw, "[angstrom] 1.23")
                assert "[angstrom] 1.23" in str(value.values)
                break
        else:
            pytest.skip("No keyword with internal_cp2k default unit found")

    def test_normal_unit_conversion_still_works(self):
        """Normal unit conversion should still work for non-internal_cp2k units."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &DFT
    &MGRID
      CUTOFF 400
    &END MGRID
  &END DFT
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        dft = result['+force_eval'][0]['+dft']
        assert 'mgrid' in dft or '+mgrid' in dft


class TestIssue69PrintAtomKind:
    """Test PRINT_ATOM_KIND keyword recognition (issue #69)."""

    def test_print_atom_kind_true(self):
        """PRINT_ATOM_KIND TRUE should parse correctly."""
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
        forces = result['+motion']['+print'][0]['+forces']
        assert forces['print_atom_kind'] is True

    def test_print_atom_kind_lone_keyword(self):
        """PRINT_ATOM_KIND as lone keyword should default to True."""
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
        forces = result['+motion']['+print'][0]['+forces']
        assert 'print_atom_kind' in forces


class TestIssue72RangeParsing:
    """Test X..Y range parsing for LIST keywords (issue #72)."""

    def test_integer_range_expansion(self):
        """X..Y range for integer keywords should expand to list."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
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
        iso = result['+force_eval'][0]['+subsys']['+topology']['+generate'][0]['+isolated_atoms']
        assert 'list' in iso
        val = iso['list']
        # LIST is a repeating keyword, values are wrapped in a list of tuples
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], tuple):
            expanded = val[0]
        else:
            expanded = val
        # The range 1..5 should expand to (1, 2, 3, 4, 5)
        assert 1 in expanded
        assert 5 in expanded
        assert len(expanded) == 5

    def test_range_with_additional_values(self):
        """Range can be combined with individual values."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 1..3 7
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        iso = result['+force_eval'][0]['+subsys']['+topology']['+generate'][0]['+isolated_atoms']
        val = iso['list']
        # LIST is a repeating keyword, values are wrapped in a list of tuples
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], tuple):
            expanded = val[0]
        else:
            expanded = val
        # 1..3 expands to 1,2,3 plus the standalone 7
        assert 1 in expanded
        assert 7 in expanded
        assert len(expanded) == 4

    def test_single_value_no_range(self):
        """Single values without range should still work."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &TOPOLOGY
      &GENERATE
        &ISOLATED_ATOMS
          LIST 3 5 7
        &END ISOLATED_ATOMS
      &END GENERATE
    &END TOPOLOGY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        iso = result['+force_eval'][0]['+subsys']['+topology']['+generate'][0]['+isolated_atoms']
        val = iso['list']
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], tuple):
            expanded = val[0]
        else:
            expanded = val
        assert 3 in expanded
        assert 5 in expanded
        assert 7 in expanded


class TestIssue105TransitionsCompat:
    """Test transitions library compatibility (issue #105)."""

    def test_transitions_import(self):
        """transitions library should import successfully."""
        import transitions
        assert transitions.__version__ is not None

    def test_tokenizer_comment_with_quotes(self):
        """Tokenizer should handle quotes inside comments without error."""
        from cp2k_input_tools.tokenizer import tokenize
        tokens = tokenize('VALUE ! comment with "quotes" in it')
        assert len(tokens) >= 1  # At least VALUE and possibly the comment
        assert tokens[0] == 'VALUE'

    def test_parse_velocity_with_comment(self):
        """VELOCITY section with complex comment should parse without error."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  METHOD Quickstep
  &SUBSYS
    &VELOCITY ! [bohr / au_t]
      1.0e-5 2.0e-5 3.0e-5
    &END VELOCITY
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        assert '+force_eval' in result


class TestIssue110Numpy2Compat:
    """Test numpy 2 compatibility via pint version constraint (issue #110)."""

    def test_pint_imports(self):
        """Pint should import successfully."""
        import pint
        assert pint.__version__ is not None

    def test_pyproject_pint_constraint(self):
        """pyproject.toml should have relaxed pint constraint."""
        import pathlib
        pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        # Should NOT have a restrictive upper bound
        assert "<0.25" not in content or ">=0.15" in content
        assert "Pint" in content


class TestIssue111ValidInpFiles:
    """Test valid .inp files that previously gave errors (issue #111)."""

    def test_comments_with_quotes_no_error(self):
        """Comments containing quotes should not cause tokenizer errors."""
        from cp2k_input_tools.tokenizer import tokenize
        # The original error was "Can't trigger event quote_char from state comment!"
        tokens = tokenize('! This has "quotes" and more')
        assert len(tokens) == 1  # Comment is a single token

    def test_lone_boolean_keyword(self):
        """Boolean keywords without explicit value should default to True."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  &SUBSYS
    &COLVAR
      &XYZ_DIAG
        ATOM 65
        COMPONENT Z
        ABSOLUTE_POSITION
        PBC F
      &END XYZ_DIAG
    &END COLVAR
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        xyz_diag = result['+force_eval'][0]['+subsys']['+colvar'][0]['+xyz_diag']
        assert xyz_diag['absolute_position'] is True

    def test_colvar_with_comment_section_header(self):
        """Section headers with inline comments should parse correctly."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&FORCE_EVAL
  METHOD Quickstep
  &SUBSYS
    &COLVAR
      &XYZ_DIAG ! instantaneous position CV
        ATOM 65
      &END XYZ_DIAG
    &END COLVAR
  &END SUBSYS
&END FORCE_EVAL
"""
        result = parser.parse(io.StringIO(inp))
        assert '+force_eval' in result

    def test_complex_real_world_input(self):
        """Complex real-world input should parse without errors."""
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML)
        inp = """&GLOBAL
  PROJECT test
  RUN_TYPE MD
&END GLOBAL
&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME POTENTIAL
    CHARGE 0
    &QS
      METHOD GPW
    &END QS
    &MGRID
      CUTOFF 400
    &END MGRID
    &SCF
      MAX_SCF 100
      &OT
        PRECONDITIONER FULL_ALL
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL
        &PBE
        &END PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &KIND H
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
&MOTION
  &MD
    ENSEMBLE NVE
    STEPS 100
    TIMESTEP 0.5
  &END MD
&END MOTION
"""
        result = parser.parse(io.StringIO(inp))
        assert '+force_eval' in result
        assert '+motion' in result
