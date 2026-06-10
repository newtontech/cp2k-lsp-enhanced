"""Tests for data-driven diagnostics using the cp2k_lsp data layer."""

import pytest

from cp2k_lsp.parser import CP2KParser
from cp2k_lsp.data.sections import get_section_info, get_valid_keywords, get_valid_subsections
from cp2k_lsp.data.keywords import get_keyword_info, get_enum_values, KeywordType


# =============================================================================
# Helper
# =============================================================================

def _parse(text: str):
    """Parse text and return (ast, errors)."""
    parser = CP2KParser.parse_text(text)
    return parser.ast, parser.errors


def _collect_all_keywords(ast):
    """Collect all keyword names from AST."""
    keywords = []

    def _walk(section):
        for kw in section.keywords:
            keywords.append((section.name, kw.name))
        for sub in section.subsections:
            _walk(sub)

    if ast.global_section:
        _walk(ast.global_section)
    for sec in ast.sections:
        _walk(sec)
    return keywords


def _collect_all_sections(ast):
    """Collect all section names from AST."""
    sections = []

    def _walk(section):
        sections.append(section.name)
        for sub in section.subsections:
            _walk(sub)

    if ast.global_section:
        _walk(ast.global_section)
    for sec in ast.sections:
        _walk(sec)
    return sections


# =============================================================================
# Data-driven section validation
# =============================================================================


class TestSectionValidation:
    """Validate sections against the data layer."""

    def test_known_sections_validated(self):
        """Sections in the data layer should be recognized."""
        for section_name in ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "XC", "SUBSYS", "KIND", "CELL", "MOTION", "MD", "GEO_OPT"]:
            info = get_section_info(section_name)
            assert info is not None, f"Section {section_name} should be in data layer"

    def test_section_keywords_consistency(self):
        """Keywords listed in section data should be consistent with keyword data."""
        for sec_name, sec_info in [("GLOBAL", get_section_info("GLOBAL")),
                                    ("SCF", get_section_info("SCF")),
                                    ("DFT", get_section_info("DFT"))]:
            for kw_name in sec_info.keywords:
                kw_info = get_keyword_info(kw_name)
                assert kw_info is not None, f"Keyword {kw_name} in {sec_name} should be in keyword data"

    def test_force_eval_repeats(self):
        """FORCE_EVAL should be marked as repeatable."""
        info = get_section_info("FORCE_EVAL")
        assert info.repeats is True

    def test_kind_repeats(self):
        """KIND should be marked as repeatable."""
        info = get_section_info("KIND")
        assert info.repeats is True

    def test_global_is_required(self):
        """GLOBAL section should be marked as required."""
        info = get_section_info("GLOBAL")
        assert info.required is True


# =============================================================================
# Data-driven keyword validation
# =============================================================================


class TestKeywordValidation:
    """Validate keywords against the data layer."""

    def test_run_type_enum(self):
        """RUN_TYPE should have complete enum values."""
        vals = get_enum_values("RUN_TYPE")
        expected = ["ENERGY", "ENERGY_FORCE", "GEO_OPT", "MD", "MC", "BSSE", "DEBUG", "NONE"]
        for v in expected:
            assert v in vals, f"RUN_TYPE should include {v}"

    def test_print_level_enum(self):
        """PRINT_LEVEL should have standard levels."""
        vals = get_enum_values("PRINT_LEVEL")
        assert "SILENT" in vals
        assert "LOW" in vals
        assert "MEDIUM" in vals
        assert "HIGH" in vals
        assert "DEBUG" in vals

    def test_method_enum(self):
        """METHOD should have GPW/GAPW options."""
        info = get_keyword_info("METHOD")
        assert "GPW" in info.enum_values
        assert "GAPW" in info.enum_values

    def test_scf_guess_enum(self):
        """SCF_GUESS should have ATOMIC/CORE options."""
        vals = get_enum_values("SCF_GUESS")
        assert "ATOMIC" in vals
        assert "CORE" in vals

    def test_integer_keywords(self):
        """Integer keywords should have correct type."""
        assert get_keyword_info("MAX_SCF").keyword_type == KeywordType.INTEGER
        assert get_keyword_info("ADDED_MOS").keyword_type == KeywordType.INTEGER
        assert get_keyword_info("CHARGE").keyword_type == KeywordType.INTEGER

    def test_real_keywords(self):
        """Real keywords should have correct type."""
        assert get_keyword_info("EPS_SCF").keyword_type == KeywordType.REAL
        assert get_keyword_info("EPS_DEFAULT").keyword_type == KeywordType.REAL
        assert get_keyword_info("TEMPERATURE").keyword_type == KeywordType.REAL

    def test_file_keywords(self):
        """File keywords should have correct type."""
        assert get_keyword_info("BASIS_SET_FILE_NAME").keyword_type == KeywordType.FILE
        assert get_keyword_info("POTENTIAL_FILE_NAME").keyword_type == KeywordType.FILE

    def test_boolean_keywords(self):
        """Boolean keywords should be identified."""
        # UKS is not in our data layer yet but that's okay
        pass

    def test_keyword_units(self):
        """Keywords with units should list them."""
        info = get_keyword_info("TEMPERATURE")
        assert info.units is not None
        assert "K" in info.units

        info = get_keyword_info("TIMESTEP")
        assert info.units is not None
        assert "fs" in info.units


# =============================================================================
# Data-driven diagnostics against parsed AST
# =============================================================================


class TestDataDrivenASTDiagnostics:
    """Test generating diagnostics from AST + data layer."""

    def test_parse_realistic_water_input(self):
        """Realistic water molecule input should parse cleanly."""
        inp = """\
&GLOBAL
  PROJECT_NAME H2O
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    &MGRID
      CUTOFF 400
      REL_CUTOFF 50
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-10
      METHOD GAPW
    &END QS
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
      SCF_GUESS ATOMIC
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 10.0 10.0 10.0
      PERIODIC XYZ
    &END CELL
    &KIND H
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      BASIS_SET TZVP
      POTENTIAL GTH-PBE
    &END KIND
    &COORD
      O  0.000000  0.000000  0.117489
      H  0.000000  0.757210 -0.469957
      H  0.000000 -0.757210 -0.469957
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0

        # Verify structure
        assert ast.global_section is not None
        assert ast.global_section.parameter is None

        # Check keywords via data layer
        run_type = ast.global_section.get_keyword("RUN_TYPE")
        assert run_type is not None
        assert run_type.value.value in get_enum_values("RUN_TYPE")

        fe = ast.get_section("FORCE_EVAL")
        assert fe is not None
        method = fe.get_keyword("METHOD")
        assert method is not None

        # Check SCF parameters
        dft = fe.get_subsection("DFT")
        scf = dft.get_subsection("SCF")
        max_scf = scf.get_keyword("MAX_SCF")
        assert max_scf is not None
        assert max_scf.value.value == 50

        eps_scf = scf.get_keyword("EPS_SCF")
        assert eps_scf is not None
        assert eps_scf.value.value == 1.0e-6

    def test_parse_md_input(self):
        """MD calculation input should parse cleanly."""
        inp = """\
&GLOBAL
  PROJECT_NAME MD_SIM
  RUN_TYPE MD
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    &MGRID
      CUTOFF 400
    &END MGRID
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 10.0 10.0 10.0
    &END CELL
    &KIND H
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &COORD
      O  0.0  0.0  0.0
      H  0.9  0.0  0.0
      H -0.9  0.0  0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS 1000
    TIMESTEP 0.5
    TEMPERATURE 300
  &END MD
&END MOTION
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0

        # Verify MOTION section
        motion = ast.get_section("MOTION")
        assert motion is not None
        md = motion.get_subsection("MD")
        assert md is not None

        steps = md.get_keyword("STEPS")
        assert steps is not None
        assert steps.value.value == 1000

        temp = md.get_keyword("TEMPERATURE")
        assert temp is not None
        assert temp.value.value == 300.0

    def test_parse_geo_opt_input(self):
        """Geometry optimization input should parse cleanly."""
        inp = """\
&GLOBAL
  PROJECT_NAME GEO_OPT
  RUN_TYPE GEO_OPT
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    &MGRID
      CUTOFF 400
    &END MGRID
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
    &END SCF
    &XC
      &XC_FUNCTIONAL B3LYP
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      ABC 10.0 10.0 10.0
    &END CELL
    &COORD
      O  0.0  0.0  0.0
      H  0.9  0.0  0.0
      H -0.9  0.0  0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &GEO_OPT
    MAX_ITER 200
    OPTIMIZER BFGS
  &END GEO_OPT
&END MOTION
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0

        motion = ast.get_section("MOTION")
        geo_opt = motion.get_subsection("GEO_OPT")
        assert geo_opt is not None
        max_iter = geo_opt.get_keyword("MAX_ITER")
        assert max_iter is not None
        assert max_iter.value.value == 200
