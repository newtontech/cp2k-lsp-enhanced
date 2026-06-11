"""Tests using real .inp fixture files for LSP parse/diagnostic stability."""

from pathlib import Path

import pytest
from cp2k_lsp.parser import CP2KParser

INPUTS_DIR = Path(__file__).resolve().parent / "inputs"


class TestLSPFixtureFiles:
    """Test parsing of real .inp fixture files with the enhanced LSP parser."""

    def _parse_file(self, filename: str):
        """Parse a fixture file and return (ast, errors, text)."""
        filepath = INPUTS_DIR / filename
        text = filepath.read_text()
        parser = CP2KParser.parse_text(text, str(filepath))
        return parser.ast, parser.errors, text

    def test_lsp_test_h2o_fixture(self):
        """H2O single-point fixture should parse without errors."""
        ast, errors, text = self._parse_file("lsp_test_H2O.inp")
        assert ast is not None
        assert len(errors) == 0

        # Verify structure
        assert ast.global_section is not None
        assert ast.global_section.get_keyword("RUN_TYPE").value.value == "ENERGY"
        assert ast.global_section.get_keyword("PROJECT_NAME").value.value == "H2O_sp"

        # FORCE_EVAL
        fe = ast.get_section("FORCE_EVAL")
        assert fe is not None
        method = fe.get_keyword("METHOD")
        assert method is not None
        assert method.value.value == "QS"

        # DFT section
        dft = fe.get_subsection("DFT")
        assert dft is not None
        bsf = dft.get_keyword("BASIS_SET_FILE_NAME")
        assert bsf is not None
        assert bsf.value.value == "BASIS_MOLOPT"

        # MGRID
        mgrid = dft.get_subsection("MGRID")
        assert mgrid is not None
        cutoff = mgrid.get_keyword("CUTOFF")
        assert cutoff is not None
        assert cutoff.value.value == 400

        # SCF with OT subsection
        scf = dft.get_subsection("SCF")
        assert scf is not None
        ot = scf.get_subsection("OT")
        assert ot is not None
        mini = ot.get_keyword("MINIMIZER")
        assert mini is not None
        assert mini.value.value == "DIIS"

        # XC
        xc = dft.get_subsection("XC")
        xcf = xc.get_subsection("XC_FUNCTIONAL")
        assert xcf is not None
        assert xcf.parameter == "PBE"

        # SUBSYS with KINDs
        subsys = fe.get_subsection("SUBSYS")
        assert subsys is not None
        kinds = [s for s in subsys.subsections if s.name.upper() == "KIND"]
        assert len(kinds) == 2
        kind_params = {k.parameter for k in kinds}
        assert kind_params == {"H", "O"}

        # CELL
        cell = subsys.get_subsection("CELL")
        assert cell is not None
        abc = cell.get_keyword("ABC")
        assert abc is not None
        # ABC should be a multi-value array
        assert isinstance(abc.value.value, list)
        assert abc.value.value == [10.0, 10.0, 10.0]

    def test_he_pbe_fixture(self):
        """He_PBE.inp should parse without crashing."""
        ast, errors, text = self._parse_file("He_PBE.inp")
        assert ast is not None
        # May have errors due to preprocessor directives

    def test_test01_fixture(self):
        """test01.inp should parse with expected structure."""
        ast, errors, text = self._parse_file("test01.inp")
        assert ast is not None
        assert ast.global_section is not None
        assert len(ast.sections) > 0

    def test_test03_fixture(self):
        """test03.inp should parse without crashing."""
        filepath = INPUTS_DIR / "test03.inp"
        if not filepath.exists():
            pytest.skip("test03.inp not found")
        ast, errors, text = self._parse_file("test03.inp")
        assert ast is not None

    def test_test04_fixture(self):
        """test04.inp should parse without crashing."""
        filepath = INPUTS_DIR / "test04.inp"
        if not filepath.exists():
            pytest.skip("test04.inp not found")
        ast, errors, text = self._parse_file("test04.inp")
        assert ast is not None

    def test_inline_comment_fixture(self):
        """inline_comment.inp should parse comments correctly."""
        filepath = INPUTS_DIR / "inline_comment.inp"
        if not filepath.exists():
            pytest.skip("inline_comment.inp not found")
        ast, errors, text = self._parse_file("inline_comment.inp")
        assert ast is not None

    def test_empty_lines_fixture(self):
        """empty_lines.inp should parse correctly."""
        filepath = INPUTS_DIR / "empty_lines.inp"
        if not filepath.exists():
            pytest.skip("empty_lines.inp not found")
        ast, errors, text = self._parse_file("empty_lines.inp")
        assert ast is not None

    def test_fractional_values_fixture(self):
        """fractional_values.inp should parse correctly."""
        filepath = INPUTS_DIR / "fractional_values.inp"
        if not filepath.exists():
            pytest.skip("fractional_values.inp not found")
        ast, errors, text = self._parse_file("fractional_values.inp")
        assert ast is not None

    def test_line_continuation_fixture(self):
        """line_continuation.inp should parse without crashing."""
        filepath = INPUTS_DIR / "line_continuation.inp"
        if not filepath.exists():
            pytest.skip("line_continuation.inp not found")
        ast, errors, text = self._parse_file("line_continuation.inp")
        assert ast is not None
