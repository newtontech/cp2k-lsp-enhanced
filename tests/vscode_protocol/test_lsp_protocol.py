"""VS Code protocol smoke tests for CP2K LSP.

Tests parser, semantic token provider, and LSP protocol components
without requiring full LSP server initialization.
"""

import sys
from pathlib import Path

import pytest

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

ROOT_DIR = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT_DIR / "tests"
INPUT_DIR = TEST_DIR / "inputs"


@pytest.fixture
def sample_input():
    return """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
  METHOD QUICKSTEP
  &DFT
    BASIS_SET_FILE_NAME "./BASIS_SETS"
    POTENTIAL_FILE_NAME "./POTENTIALS"
    &SCF
      EPS_SCF 1.0E-7
      MAX_SCF 50
    &END SCF
  &END DFT
&END FORCE_EVAL
"""


@pytest.fixture
def invalid_input():
    return """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL
&GLOBAL
  PROJECT duplicate
&END
"""


@pytest.fixture
def preprocessor_input():
    return """@SET MY_VAR hello
@SET NUM 42
&GLOBAL
  PROJECT ${MY_VAR}
  RUN_TYPE ENERGY
&END GLOBAL
&FORCE_EVAL
  @IF ${NUM} > 10
  METHOD QUICKSTEP
  @ELSE
  METHOD PATTERN_METHOD
  @ENDIF
&END FORCE_EVAL
"""


@pytest.fixture
def comment_input():
    return """! This is a comment
&GLOBAL
  ! Comment inside section
  PROJECT test
  RUN_TYPE ENERGY  ! Inline comment
&END GLOBAL
"""


@pytest.fixture
def unit_input():
    return """&GLOBAL
  PROJECT test
&END GLOBAL
&FORCE_EVAL
  &SUBSYS
    &CELL
      A [angstrom] 10.0 0.0 0.0
      B [angstrom] 0.0 10.0 0.0
      C [angstrom] 0.0 0.0 10.0
    &END CELL
  &END SUBSYS
&END FORCE_EVAL
"""


class TestParser:
    def test_parse_valid_input(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        assert parser.ast is not None
        assert len(parser.errors) == 0

    def test_parse_global_section(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        assert parser.ast.global_section is not None
        assert parser.ast.global_section.name.upper() == "GLOBAL"

    def test_parse_nested_sections(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        section_names = [s.name.upper() for s in parser.ast.sections]
        assert "FORCE_EVAL" in section_names
        force_eval = next(s for s in parser.ast.sections if s.name.upper() == "FORCE_EVAL")
        subsection_names = [s.name.upper() for s in force_eval.subsections]
        assert "DFT" in subsection_names

    def test_parse_keywords(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        global_section = parser.ast.global_section
        keyword_names = [k.name.upper() for k in global_section.keywords]
        assert "PROJECT" in keyword_names
        assert "RUN_TYPE" in keyword_names
        assert "PRINT_LEVEL" in keyword_names

    def test_parse_keyword_values(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        global_section = parser.ast.global_section
        project_kw = next(k for k in global_section.keywords if k.name.upper() == "PROJECT")
        assert project_kw.value.value == "test"
        run_type_kw = next(k for k in global_section.keywords if k.name.upper() == "RUN_TYPE")
        assert run_type_kw.value.value == "ENERGY"

    def test_parse_invalid_input(self, invalid_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(invalid_input, "file:///invalid.inp")
        assert parser.ast is not None

    def test_parse_comments(self, comment_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(comment_input, "file:///comments.inp")
        assert parser.ast is not None
        assert len(parser.ast.comments) > 0

    def test_parse_units(self, unit_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(unit_input, "file:///units.inp")
        assert parser.ast is not None

    def test_parse_preprocessor(self, preprocessor_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(preprocessor_input, "file:///preproc.inp")
        assert parser is not None


class TestDocumentSymbols:
    def test_symbols_from_ast(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        assert parser.ast is not None
        if parser.ast.global_section:
            assert parser.ast.global_section.name.upper() == "GLOBAL"
        section_names = [s.name.upper() for s in parser.ast.sections]
        assert "FORCE_EVAL" in section_names

    def test_symbol_tree_structure(self, sample_input):
        from cp2k_lsp.parser import CP2KParser

        parser = CP2KParser.parse_text(sample_input, "file:///test.inp")
        ast = parser.ast
        assert ast.global_section is not None
        assert len(ast.global_section.keywords) > 0
        force_eval = next(s for s in ast.sections if s.name.upper() == "FORCE_EVAL")
        assert len(force_eval.subsections) > 0


class TestSemanticTokens:
    def test_semantic_token_provider_exists(self):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        assert SemanticTokenProvider is not None

    def test_semantic_tokens_for_sections(self, sample_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(sample_input)
        assert len(tokens) > 0
        section_tokens = [t for t in tokens if t.token_type == "section"]
        assert len(section_tokens) > 0

    def test_semantic_tokens_for_keywords(self, sample_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(sample_input)
        keyword_tokens = [t for t in tokens if t.token_type == "keyword"]
        assert len(keyword_tokens) > 0

    def test_semantic_tokens_for_values(self, sample_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(sample_input)
        value_tokens = [t for t in tokens if t.token_type == "value"]
        assert len(value_tokens) > 0

    def test_semantic_tokens_for_comments(self, comment_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(comment_input)
        comment_tokens = [t for t in tokens if t.token_type == "comment"]
        assert len(comment_tokens) > 0

    def test_semantic_tokens_for_units(self, unit_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(unit_input)
        unit_tokens = [t for t in tokens if t.token_type == "unit"]
        assert len(unit_tokens) > 0

    def test_semantic_tokens_for_preprocessor(self, preprocessor_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(preprocessor_input)
        preprocessor_tokens = [t for t in tokens if t.token_type == "preprocessor"]
        assert len(preprocessor_tokens) > 0

    def test_semantic_tokens_format(self, sample_input):
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(sample_input)
        for token in tokens:
            assert hasattr(token, "line")
            assert hasattr(token, "start_char")
            assert hasattr(token, "length")
            assert hasattr(token, "token_type")
            assert hasattr(token, "modifiers")
            assert token.line >= 0
            assert token.start_char >= 0
            assert token.length > 0


class TestRealInputFiles:
    def test_nacl_input_parses(self):
        nacl_path = INPUT_DIR / "NaCl.inp"
        if not nacl_path.exists():
            pytest.skip(f"NaCl.inp not found: {nacl_path}")
        from cp2k_lsp.parser import CP2KParser

        content = nacl_path.read_text()
        parser = CP2KParser.parse_text(content, str(nacl_path))
        assert parser.ast is not None

    def test_test01_input_parses(self):
        test_path = INPUT_DIR / "test01.inp"
        if not test_path.exists():
            pytest.skip(f"test01.inp not found: {test_path}")
        from cp2k_lsp.parser import CP2KParser

        content = test_path.read_text()
        parser = CP2KParser.parse_text(content, str(test_path))
        assert parser.ast is not None

    def test_nacl_semantic_tokens(self):
        nacl_path = INPUT_DIR / "NaCl.inp"
        if not nacl_path.exists():
            pytest.skip(f"NaCl.inp not found: {nacl_path}")
        from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider

        content = nacl_path.read_text()
        provider = SemanticTokenProvider()
        tokens = provider.get_semantic_tokens(content)
        assert len(tokens) > 0
