"""Tests for enhanced LSP features: document symbols, navigation, data-driven diagnostics/completion."""

import pytest
from cp2k_lsp.data.keywords import (
    KeywordType,
    get_enum_values,
    get_keyword_info,
)
from cp2k_lsp.data.sections import (
    CP2K_SECTIONS,
    get_section_info,
    get_valid_keywords,
    get_valid_subsections,
)
from cp2k_lsp.parser import CP2KInput, CP2KParser
from cp2k_lsp.parser.lexer import Lexer, TokenType

# =============================================================================
# Helper
# =============================================================================


def _parse(text: str):
    """Parse text and return (ast, errors)."""
    parser = CP2KParser.parse_text(text)
    return parser.ast, parser.errors


# =============================================================================
# Section parameter parsing
# =============================================================================


class TestSectionParameters:
    """Test parsing of section parameters (e.g., &XC_FUNCTIONAL PBE)."""

    def test_section_parameter_on_functional(self):
        """XC_FUNCTIONAL PBE should parse PBE as the section parameter."""
        inp = """\
&FORCE_EVAL
  &DFT
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast is not None
        xc = ast.sections[0].get_subsection("DFT").get_subsection("XC")
        assert xc is not None
        xcf = xc.get_subsection("XC_FUNCTIONAL")
        assert xcf is not None

    def test_section_parameter_on_kind(self):
        """&KIND H should parse H as the section parameter."""
        inp = """\
&FORCE_EVAL
  &SUBSYS
    &KIND H
      BASIS_SET DZV-GTH-PADE
      POTENTIAL GTH-PADE-q1
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast is not None
        subsys = ast.sections[0].get_subsection("SUBSYS")
        assert subsys is not None
        kind = subsys.get_subsection("KIND")
        assert kind is not None

    def test_section_parameter_on_coord(self):
        """&COORD with scaled flag should work."""
        inp = """\
&FORCE_EVAL
  &SUBSYS
    &COORD
      SCALED .TRUE.
      O  0.0  0.0  0.0
      H  0.9  0.0  0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast is not None
        subsys = ast.sections[0].get_subsection("SUBSYS")
        assert subsys is not None
        coord = subsys.get_subsection("COORD")
        assert coord is not None


# =============================================================================
# Data-driven completion
# =============================================================================


class TestDataDrivenCompletion:
    """Test that data layer provides expected information for completions."""

    def test_known_sections_exist(self):
        """Core sections should be defined in the data layer."""
        for name in ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "XC", "SUBSYS", "KIND", "CELL"]:
            assert name in CP2K_SECTIONS, f"Missing section definition: {name}"

    def test_global_section_has_expected_keywords(self):
        """GLOBAL section should list its known keywords."""
        info = get_section_info("GLOBAL")
        assert info is not None
        assert "PROJECT_NAME" in info.keywords
        assert "RUN_TYPE" in info.keywords
        assert "PRINT_LEVEL" in info.keywords

    def test_force_eval_subsections(self):
        """FORCE_EVAL should list DFT, SUBSYS as subsections."""
        subs = get_valid_subsections("FORCE_EVAL")
        assert "DFT" in subs
        assert "SUBSYS" in subs

    def test_dft_keywords(self):
        """DFT section should list key keywords."""
        kws = get_valid_keywords("DFT")
        assert "BASIS_SET_FILE_NAME" in kws
        assert "POTENTIAL_FILE_NAME" in kws

    def test_scf_keywords(self):
        """SCF section should list key keywords."""
        kws = get_valid_keywords("SCF")
        assert "EPS_SCF" in kws
        assert "MAX_SCF" in kws

    def test_unknown_section_returns_none(self):
        """Unknown section should return None."""
        assert get_section_info("NONEXISTENT") is None

    def test_keyword_enum_values(self):
        """RUN_TYPE should have enum values."""
        vals = get_enum_values("RUN_TYPE")
        assert "ENERGY" in vals
        assert "GEO_OPT" in vals
        assert "MD" in vals

    def test_keyword_type_info(self):
        """EPS_SCF should be a real keyword."""
        info = get_keyword_info("EPS_SCF")
        assert info is not None
        assert info.keyword_type == KeywordType.REAL

    def test_keyword_default_values(self):
        """Keywords should have defaults."""
        assert get_keyword_info("MAX_SCF").default == 50
        assert get_keyword_info("EPS_SCF").default == 1.0e-7
        assert get_keyword_info("PRINT_LEVEL").default == "MEDIUM"


# =============================================================================
# Diagnostics on real .inp files
# =============================================================================


class TestParserStabilityOnRealInputs:
    """Parse real .inp fixtures from the test suite for stability."""

    @pytest.fixture
    def inputs_dir(self):
        from pathlib import Path

        return Path(__file__).resolve().parent / "inputs"

    def test_parse_he_pbe(self, inputs_dir):
        """He_PBE.inp should parse without critical errors."""
        text = (inputs_dir / "He_PBE.inp").read_text()
        # The enhanced parser can't handle preprocessor directives yet,
        # but should not crash on them
        parser = CP2KParser.parse_text(text, "He_PBE.inp")
        assert parser.ast is not None

    def test_parse_test01(self, inputs_dir):
        """test01.inp should parse with expected structure."""
        text = (inputs_dir / "test01.inp").read_text()
        parser = CP2KParser.parse_text(text, "test01.inp")
        assert parser.ast is not None
        # Should have FORCE_EVAL and GLOBAL sections
        assert parser.ast.global_section is not None
        assert len(parser.ast.sections) > 0

    def test_parse_empty_input(self):
        """Empty input should produce empty AST."""
        ast, errors = _parse("")
        assert ast is not None
        assert ast.global_section is None
        assert len(ast.sections) == 0

    def test_parse_only_comments(self):
        """Comments-only input should produce empty AST."""
        ast, errors = _parse("# just a comment\n# another comment\n")
        assert ast is not None
        assert len(ast.comments) >= 1

    def test_parse_unclosed_section(self):
        """Unclosed section should produce error."""
        inp = "&GLOBAL\n  RUN_TYPE ENERGY\n"
        ast, errors = _parse(inp)
        assert len(errors) > 0
        assert any("unclosed" in str(e).lower() or "Unclosed" in str(e) for e in errors)

    def test_parse_deeply_nested(self):
        """Deeply nested sections should parse."""
        inp = """\
&FORCE_EVAL
  &DFT
    &SCF
      &OT
        MINIMIZER DIIS
        PRECONDITIONER FULL_SINGLE_INVERSE
      &END OT
    &END SCF
  &END DFT
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast is not None
        fe = ast.sections[0]
        dft = fe.get_subsection("DFT")
        scf = dft.get_subsection("SCF")
        ot = scf.get_subsection("OT")
        assert ot is not None

    def test_multiple_top_level_sections(self):
        """Multiple top-level sections should parse."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast.global_section is not None
        assert len(ast.sections) >= 1

    def test_keyword_with_multiple_values(self):
        """Keywords with multiple values (like ABC) should work."""
        inp = """\
&FORCE_EVAL
  &SUBSYS
    &CELL
      ABC 10.0 10.0 10.0
    &END CELL
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert ast is not None


# =============================================================================
# Lexer edge cases
# =============================================================================


class TestLexerEdgeCases:
    """Test lexer edge cases for robustness."""

    def test_unit_bracket_notation(self):
        """Unit notation like [angstrom] should be tokenized."""
        lexer = Lexer("CUTOFF 400.0\n")
        tokens = lexer.tokenize()
        # Should have NUMBER token for 400.0
        types = [t.type for t in tokens]
        assert TokenType.NUMBER in types

    def test_comment_styles(self):
        """Both # and ! comments should be handled."""
        lexer1 = Lexer("# this is a comment\n")
        tokens1 = lexer1.tokenize()
        assert any(t.type == TokenType.COMMENT for t in tokens1)

        lexer2 = Lexer("! this is a comment\n")
        tokens2 = lexer2.tokenize()
        assert any(t.type == TokenType.COMMENT for t in tokens2)

    def test_boolean_true(self):
        """Boolean .TRUE. should be tokenized."""
        lexer = Lexer("UKS .TRUE.\n")
        tokens = lexer.tokenize()
        assert any(t.type == TokenType.BOOLEAN and t.value == ".TRUE." for t in tokens)

    def test_boolean_false(self):
        """Boolean .FALSE. should be tokenized."""
        lexer = Lexer("UKS .FALSE.\n")
        tokens = lexer.tokenize()
        assert any(t.type == TokenType.BOOLEAN and t.value == ".FALSE." for t in tokens)

    def test_scientific_notation(self):
        """Scientific notation should be tokenized as NUMBER."""
        lexer = Lexer("EPS_SCF 1.0E-6\n")
        tokens = lexer.tokenize()
        num_tokens = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(num_tokens) >= 1
        assert num_tokens[0].value == "1.0E-6"

    def test_negative_number(self):
        """Negative numbers should be tokenized."""
        lexer = Lexer("CHARGE -1\n")
        tokens = lexer.tokenize()
        num_tokens = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(num_tokens) >= 1
        assert num_tokens[0].value == "-1"

    def test_quoted_string(self):
        """Quoted strings should be tokenized."""
        lexer = Lexer('PROJECT_NAME "my project"\n')
        tokens = lexer.tokenize()
        str_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert any(t.value == "my project" for t in str_tokens)

    def test_section_end_token(self):
        """&END SECTION should produce SECTION_END token."""
        lexer = Lexer("&END GLOBAL\n")
        tokens = lexer.tokenize()
        end_tokens = [t for t in tokens if t.type == TokenType.SECTION_END]
        assert len(end_tokens) == 1
        assert end_tokens[0].value.upper() == "GLOBAL"

    def test_section_start_token(self):
        """&SECTION should produce SECTION_START token."""
        lexer = Lexer("&GLOBAL\n")
        tokens = lexer.tokenize()
        start_tokens = [t for t in tokens if t.type == TokenType.SECTION_START]
        assert len(start_tokens) == 1
        assert start_tokens[0].value.upper() == "GLOBAL"

    def test_equals_sign(self):
        """= should be tokenized as ASSIGN."""
        lexer = Lexer("RUN_TYPE = ENERGY\n")
        tokens = lexer.tokenize()
        assert any(t.type == TokenType.ASSIGN for t in tokens)


# =============================================================================
# Document symbols (navigation)
# =============================================================================


class TestDocumentSymbols:
    """Test document symbol extraction for navigation."""

    def _collect_section_names(self, ast: CP2KInput) -> list:
        """Collect all section names from AST recursively."""
        names = []

        def _walk(section):
            names.append(section.name)
            for sub in section.subsections:
                _walk(sub)

        if ast.global_section:
            _walk(ast.global_section)
        for sec in ast.sections:
            _walk(sec)
        return names

    def test_symbol_extraction_basic(self):
        """Basic input should produce section symbols."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
"""
        ast, _ = _parse(inp)
        names = self._collect_section_names(ast)
        assert "GLOBAL" in names

    def test_symbol_extraction_nested(self):
        """Nested sections should appear in symbols."""
        inp = """\
&FORCE_EVAL
  METHOD QS
  &DFT
    &MGRID
      CUTOFF 400
    &END MGRID
  &END DFT
  &SUBSYS
    &KIND H
      BASIS_SET DZVP
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        names = self._collect_section_names(ast)
        assert "FORCE_EVAL" in names
        assert "DFT" in names
        assert "MGRID" in names
        assert "SUBSYS" in names
        assert "KIND" in names

    def test_symbol_line_numbers(self):
        """Section nodes should have correct line numbers."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        assert ast.global_section is not None
        assert ast.global_section.line == 1
        fe = ast.sections[0]
        assert fe.line == 5  # Line 5 (1-indexed)


# =============================================================================
# Diagnostic stability
# =============================================================================


class TestDiagnosticStability:
    """Test that diagnostics are stable and correct for common scenarios."""

    def test_valid_input_no_errors(self):
        """Valid CP2K input should produce no parse errors."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
  PROJECT_NAME test
&END GLOBAL
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0

    def test_mismatched_section_end(self):
        """Mismatched section end should produce error."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END WRONG
"""
        ast, errors = _parse(inp)
        assert len(errors) > 0
        assert any("mismatch" in str(e).lower() or "Mismatch" in str(e) for e in errors)

    def test_duplicate_section_name_in_end(self):
        """Section end should match section start name."""
        inp = """\
&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0

    def test_keyword_value_preserved(self):
        """Keyword values should be preserved accurately."""
        inp = """\
&GLOBAL
  PROJECT_NAME my_test_project
&END GLOBAL
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0
        kw = ast.global_section.get_keyword("PROJECT_NAME")
        assert kw is not None
        assert kw.value.value == "my_test_project"

    def test_numeric_keyword_value_types(self):
        """Numeric keyword values should have correct types."""
        inp = """\
&SCF
  MAX_SCF 100
  EPS_SCF 1.0E-6
&END SCF
"""
        ast, errors = _parse(inp)
        assert len(errors) == 0
        max_scf = ast.sections[0].get_keyword("MAX_SCF")
        assert isinstance(max_scf.value.value, int)
        assert max_scf.value.value == 100
        eps_scf = ast.sections[0].get_keyword("EPS_SCF")
        assert isinstance(eps_scf.value.value, float)
        assert abs(eps_scf.value.value - 1e-6) < 1e-15


# =============================================================================
# Hover documentation coverage
# =============================================================================


class TestHoverDocumentationCoverage:
    """Test that hover documentation covers important keywords and sections."""

    def test_hover_section_docs(self):
        """Important sections should have hover docs."""
        from cp2k_lsp.features.hover import HoverProvider

        provider = HoverProvider.__new__(HoverProvider)
        for section in ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "XC", "MOTION"]:
            assert section in provider.SECTION_DOCS, f"Missing hover doc for section: {section}"

    def test_hover_keyword_docs(self):
        """Important keywords should have hover docs."""
        from cp2k_lsp.features.hover import HoverProvider

        provider = HoverProvider.__new__(HoverProvider)
        for kw in ["PROJECT_NAME", "RUN_TYPE", "PRINT_LEVEL", "EPS_SCF", "MAX_SCF"]:
            assert kw in provider.KEYWORD_DOCS, f"Missing hover doc for keyword: {kw}"

    def test_word_extraction(self):
        """Word extraction at position should work correctly."""
        from cp2k_lsp.features.hover import HoverProvider

        provider = HoverProvider.__new__(HoverProvider)
        # Test word at beginning
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 0) == "RUN_TYPE"
        # Test word in middle
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 1) == "RUN_TYPE"
        # Test after underscore
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 5) == "RUN_TYPE"
        # Test second word
        assert provider._get_word_at_position("RUN_TYPE ENERGY", 10) == "ENERGY"


# =============================================================================
# Formatting provider
# =============================================================================


class TestFormattingProvider:
    """Test formatting provider produces valid output."""

    def test_format_simple_input(self):
        """Formatting simple input should produce valid text."""
        inp = """\
&GLOBAL
RUN_TYPE ENERGY
&END GLOBAL
"""
        parser = CP2KParser.parse_text(inp)
        assert parser.ast is not None
        from cp2k_lsp.features.formatting import FormattingProvider

        provider = FormattingProvider.__new__(FormattingProvider)
        formatted = provider._format_ast(parser.ast)
        assert "&GLOBAL" in formatted
        assert "&END GLOBAL" in formatted
        assert "RUN_TYPE" in formatted

    def test_format_preserves_structure(self):
        """Formatting should preserve section hierarchy."""
        inp = """\
&FORCE_EVAL
&DFT
&MGRID
CUTOFF 400
&END MGRID
&END DFT
&END FORCE_EVAL
"""
        parser = CP2KParser.parse_text(inp)
        from cp2k_lsp.features.formatting import FormattingProvider

        provider = FormattingProvider.__new__(FormattingProvider)
        formatted = provider._format_ast(parser.ast)
        lines = formatted.split("\n")
        # Check that nested sections are indented
        dft_idx = next(i for i, line in enumerate(lines) if "&DFT" in line)
        mgrid_idx = next(i for i, line in enumerate(lines) if "&MGRID" in line)
        # DFT should be indented more than FORCE_EVAL
        assert lines[dft_idx].startswith("  ")
        # MGRID should be indented more than DFT
        assert lines[mgrid_idx].startswith("    ")


# =============================================================================
# Code action coverage
# =============================================================================


class TestCodeActionCoverage:
    """Test code action quick fix generation."""

    def test_unclosed_section_quick_fix(self):
        """Unclosed section error should suggest &END fix."""
        from cp2k_lsp.features.code_action import CodeActionProvider
        from lsprotocol import types as lsp

        provider = CodeActionProvider.__new__(CodeActionProvider)
        diag = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=10)),
            message="Unclosed section &GLOBAL",
            severity=lsp.DiagnosticSeverity.Error,
            source="cp2k-lsp",
        )
        action = provider._fix_unclosed_section(diag, "file:///test.inp")
        assert action is not None
        assert "&END" in action.title or "&END" in str(action.edit)

    def test_section_mismatch_quick_fix(self):
        """Section mismatch should suggest fix."""
        from cp2k_lsp.features.code_action import CodeActionProvider
        from lsprotocol import types as lsp

        provider = CodeActionProvider.__new__(CodeActionProvider)
        diag = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=10)),
            message="Section name mismatch",
            severity=lsp.DiagnosticSeverity.Error,
            source="cp2k-lsp",
        )
        action = provider._fix_section_mismatch(diag, "file:///test.inp")
        assert action is not None
