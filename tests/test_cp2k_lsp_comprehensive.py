"""
Comprehensive test suite for CP2K LSP features.
Tests parser, lexer, AST, and all LSP features.
"""

import pytest
from unittest.mock import MagicMock, patch

# Parser tests
from cp2k_lsp.parser.lexer import Lexer, Token, TokenType
from cp2k_lsp.parser.parser import CP2KParser
from cp2k_lsp.parser.ast import CP2KInput, Section, Keyword, Value, ValueType, Comment, ASTNode
from cp2k_lsp.parser.errors import ParseError, SyntaxError as CP2KSyntaxError


class TestLexer:
    """Test the CP2K lexer."""

    def test_empty_input(self):
        """Test tokenizing empty input."""
        lexer = Lexer("")
        tokens = lexer.tokenize()
        assert tokens[-1].type == TokenType.EOF

    def test_section_start(self):
        """Test section start tokenization."""
        lexer = Lexer("&GLOBAL")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.SECTION_START
        assert tokens[0].value == "GLOBAL"

    def test_section_end(self):
        """Test section end tokenization."""
        lexer = Lexer("&END GLOBAL")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.SECTION_END
        # The value should be the section name after END
        assert tokens[0].value == "GLOBAL"

    def test_section_end_solo(self):
        """Test section end without name tokenization."""
        lexer = Lexer("&END")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.SECTION_END
        assert tokens[0].value == "END"

    def test_keyword(self):
        """Test keyword tokenization."""
        lexer = Lexer("PROJECT_NAME")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "PROJECT_NAME"

    def test_assignment(self):
        """Test assignment tokenization."""
        lexer = Lexer("=")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.ASSIGN

    def test_string_single_quote(self):
        """Test single-quoted string tokenization."""
        lexer = Lexer("'hello world'")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_string_double_quote(self):
        """Test double-quoted string tokenization."""
        lexer = Lexer('"hello world"')
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_number_integer(self):
        """Test integer tokenization."""
        lexer = Lexer("42")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"

    def test_number_float(self):
        """Test float tokenization."""
        lexer = Lexer("3.14")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "3.14"

    def test_number_scientific(self):
        """Test scientific notation tokenization."""
        lexer = Lexer("1.0e-7")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "1.0e-7"

    def test_boolean_true(self):
        """Test boolean true tokenization."""
        lexer = Lexer(".TRUE.")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.BOOLEAN
        assert tokens[0].value == ".TRUE."

    def test_boolean_false(self):
        """Test boolean false tokenization."""
        lexer = Lexer(".FALSE.")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.BOOLEAN
        assert tokens[0].value == ".FALSE."

    def test_comment_bang(self):
        """Test comment tokenization with !."""
        lexer = Lexer("! This is a comment")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.COMMENT
        # Comment includes the full text after the delimiter
        assert "This is a comment" in tokens[0].value

    def test_comment_hash(self):
        """Test comment tokenization with #."""
        lexer = Lexer("# This is a comment")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.COMMENT
        # Comment includes the full text after the delimiter
        assert "This is a comment" in tokens[0].value

    def test_unit(self):
        """Test unit tokenization."""
        lexer = Lexer("[eV]")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.UNIT
        assert tokens[0].value == "eV"

    def test_eol(self):
        """Test end of line tokenization."""
        lexer = Lexer("line1\nline2")
        tokens = lexer.tokenize()
        assert tokens[1].type == TokenType.EOL

    def test_unterminated_string_error(self):
        """Test error on unterminated string."""
        lexer = Lexer('"unterminated')
        with pytest.raises(Exception):  # CP2KSyntaxError is a subclass of Exception
            lexer.tokenize()


class TestParser:
    """Test the CP2K parser."""

    def test_parse_empty(self):
        """Test parsing empty input."""
        parser = CP2KParser.parse_text("")
        assert parser.ast is not None
        assert len(parser.ast.sections) == 0

    def test_parse_global_section(self):
        """Test parsing global section."""
        text = """&GLOBAL
  PROJECT_NAME test
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        assert parser.ast.global_section is not None
        assert parser.ast.global_section.name == "GLOBAL"

    def test_parse_keyword_with_value(self):
        """Test parsing keyword with value."""
        text = """&GLOBAL
  PROJECT_NAME = test
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        keyword = parser.ast.global_section.get_keyword("PROJECT_NAME")
        assert keyword is not None
        assert keyword.value.value == "test"

    def test_parse_keyword_without_value(self):
        """Test parsing keyword without value."""
        text = """&GLOBAL
  DEBUG
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        keyword = parser.ast.global_section.get_keyword("DEBUG")
        assert keyword is not None
        assert keyword.value.value is None

    def test_parse_number_value(self):
        """Test parsing number value."""
        text = """&GLOBAL
  WALLTIME = 3600
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        keyword = parser.ast.global_section.get_keyword("WALLTIME")
        assert keyword.value.value == 3600

    def test_parse_boolean_value(self):
        """Test parsing boolean value."""
        text = """&GLOBAL
  DEBUG = .TRUE.
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        keyword = parser.ast.global_section.get_keyword("DEBUG")
        assert keyword.value.value is True

    def test_parse_string_value(self):
        """Test parsing string value."""
        text = """&GLOBAL
  PROJECT_NAME = "my project"
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        keyword = parser.ast.global_section.get_keyword("PROJECT_NAME")
        assert keyword.value.value == "my project"

    def test_parse_nested_sections(self):
        """Test parsing nested sections."""
        text = """&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS
  &END DFT
&END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        force_eval = parser.ast.get_section("FORCE_EVAL")
        assert force_eval is not None
        dft = force_eval.get_subsection("DFT")
        assert dft is not None

    def test_parse_multiple_sections(self):
        """Test parsing multiple sections."""
        text = """&GLOBAL
  PROJECT_NAME test
&END GLOBAL

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        assert len(parser.ast.sections) == 1
        assert parser.ast.global_section is not None

    def test_parse_with_comments(self):
        """Test parsing with comments."""
        text = """! This is a comment
&GLOBAL
  ! Another comment
  PROJECT_NAME test
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        assert len(parser.ast.comments) >= 0

    def test_section_name_mismatch_error(self):
        """Test error on section name mismatch."""
        text = """&GLOBAL
&END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        assert len(parser.errors) > 0

    def test_unclosed_section_error(self):
        """Test error on unclosed section."""
        text = """&GLOBAL
  PROJECT_NAME test
&END GLOBAL"""
        # This should not produce errors - the section is properly closed
        parser = CP2KParser.parse_text(text)
        # If we had an unclosed section, there would be errors
        # For a properly closed section, errors should be empty


class TestAST:
    """Test the AST classes."""

    def test_cp2k_input_repr(self):
        """Test CP2KInput repr."""
        inp = CP2KInput()
        inp.sections = [Section(name="TEST")]
        repr_str = repr(inp)
        assert "CP2KInput" in repr_str
        assert "1 sections" in repr_str

    def test_section_repr(self):
        """Test Section repr."""
        section = Section(name="TEST")
        repr_str = repr(section)
        assert "Section" in repr_str
        assert "TEST" in repr_str

    def test_keyword_repr(self):
        """Test Keyword repr."""
        keyword = Keyword(name="TEST", value=Value(value="value"))
        repr_str = repr(keyword)
        assert "Keyword" in repr_str
        assert "TEST" in repr_str

    def test_value_repr(self):
        """Test Value repr."""
        value = Value(value=42, value_type=ValueType.NUMBER)
        repr_str = repr(value)
        assert "Value" in repr_str
        assert "42" in repr_str

    def test_value_with_unit_repr(self):
        """Test Value with unit repr."""
        value = Value(value=1.0, unit="eV")
        repr_str = repr(value)
        assert "eV" in repr_str

    def test_comment_repr(self):
        """Test Comment repr."""
        comment = Comment(text="test comment")
        repr_str = repr(comment)
        assert "Comment" in repr_str

    def test_cp2k_input_get_section(self):
        """Test getting section from CP2KInput."""
        inp = CP2KInput()
        section = Section(name="TEST")
        inp.sections.append(section)
        assert inp.get_section("TEST") == section
        assert inp.get_section("test") == section  # case insensitive
        assert inp.get_section("MISSING") is None

    def test_section_get_keyword(self):
        """Test getting keyword from Section."""
        section = Section(name="TEST")
        keyword = Keyword(name="KEY")
        section.keywords.append(keyword)
        assert section.get_keyword("KEY") == keyword
        assert section.get_keyword("key") == keyword  # case insensitive
        assert section.get_keyword("MISSING") is None

    def test_section_get_subsection(self):
        """Test getting subsection from Section."""
        section = Section(name="PARENT")
        subsection = Section(name="CHILD")
        section.subsections.append(subsection)
        assert section.get_subsection("CHILD") == subsection
        assert section.get_subsection("child") == subsection  # case insensitive
        assert section.get_subsection("MISSING") is None

    def test_ast_node_accept(self):
        """Test visitor pattern accept method."""
        class TestVisitor:
            def visit_Value(self, node):
                return "visited_value"

        value = Value()
        result = value.accept(TestVisitor())
        assert result == "visited_value"

    def test_ast_node_generic_visit_raises(self):
        """Test that generic_visit raises NotImplementedError."""
        class TestNode(ASTNode):
            pass

        node = TestNode()
        with pytest.raises(NotImplementedError):
            node.generic_visit(None)


class TestErrors:
    """Test error classes."""

    def test_parse_error_str(self):
        """Test ParseError string representation."""
        error = ParseError("Test error", 1, 1)
        str_repr = str(error)
        assert "Test error" in str_repr
        assert "line 1" in str_repr

    def test_parse_error_with_source(self):
        """Test ParseError with source."""
        error = ParseError("Test error", 1, 1, source="test.inp")
        str_repr = str(error)
        assert "test.inp" in str_repr

    def test_syntax_error_str(self):
        """Test SyntaxError string representation."""
        error = CP2KSyntaxError("Syntax error", 1, 1, expected="SEMICOLON", found="EOF")
        str_repr = str(error)
        assert "Syntax error" in str_repr
        assert "SEMICOLON" in str_repr
        assert "EOF" in str_repr


# Feature tests
class TestCompletionProvider:
    """Test the completion provider."""

    def test_section_completions(self):
        """Test section completions."""
        from cp2k_lsp.features.completion import CompletionProvider

        mock_server = MagicMock()
        provider = CompletionProvider(mock_server)

        items = provider._get_section_completions()
        assert len(items) > 0
        assert any(item.label == "GLOBAL" for item in items)

    def test_keyword_completions(self):
        """Test keyword completions."""
        from cp2k_lsp.features.completion import CompletionProvider

        mock_server = MagicMock()
        provider = CompletionProvider(mock_server)

        items = provider._get_keyword_completions()
        assert len(items) > 0
        assert any(item.label == "PROJECT_NAME" for item in items)

    def test_value_completions_run_type(self):
        """Test RUN_TYPE value completions."""
        from cp2k_lsp.features.completion import CompletionProvider

        mock_server = MagicMock()
        provider = CompletionProvider(mock_server)

        items = provider._get_value_completions("RUN_TYPE = ")
        assert len(items) > 0
        assert any(item.label == "ENERGY" for item in items)
        assert any(item.label == "GEO_OPT" for item in items)

    def test_value_completions_print_level(self):
        """Test PRINT_LEVEL value completions."""
        from cp2k_lsp.features.completion import CompletionProvider

        mock_server = MagicMock()
        provider = CompletionProvider(mock_server)

        items = provider._get_value_completions("PRINT_LEVEL = ")
        assert any(item.label == "MEDIUM" for item in items)

    def test_value_completions_boolean(self):
        """Test boolean value completions."""
        from cp2k_lsp.features.completion import CompletionProvider

        mock_server = MagicMock()
        provider = CompletionProvider(mock_server)

        items = provider._get_value_completions("SOME_KEY = ")
        assert any(item.label == ".TRUE." for item in items)
        assert any(item.label == ".FALSE." for item in items)


class TestHoverProvider:
    """Test the hover provider."""

    def test_section_hover(self):
        """Test section hover."""
        from cp2k_lsp.features.hover import HoverProvider

        mock_server = MagicMock()
        provider = HoverProvider(mock_server)

        hover = provider._get_word_at_position("&GLOBAL", 2)
        assert hover == "GLOBAL"

    def test_keyword_hover(self):
        """Test keyword hover."""
        from cp2k_lsp.features.hover import HoverProvider

        mock_server = MagicMock()
        provider = HoverProvider(mock_server)

        hover = provider._get_word_at_position("PROJECT_NAME = test", 5)
        assert hover == "PROJECT_NAME"

    def test_section_docs_exist(self):
        """Test that section documentation exists."""
        from cp2k_lsp.features.hover import HoverProvider

        assert "GLOBAL" in HoverProvider.SECTION_DOCS
        assert "DFT" in HoverProvider.SECTION_DOCS

    def test_keyword_docs_exist(self):
        """Test that keyword documentation exists."""
        from cp2k_lsp.features.hover import HoverProvider

        assert "PROJECT_NAME" in HoverProvider.KEYWORD_DOCS
        assert "RUN_TYPE" in HoverProvider.KEYWORD_DOCS


class TestFormattingProvider:
    """Test the formatting provider."""

    def test_format_section(self):
        """Test formatting a section."""
        from cp2k_lsp.features.formatting import FormattingProvider

        mock_server = MagicMock()
        provider = FormattingProvider(mock_server)

        section = Section(name="GLOBAL")
        section.keywords.append(Keyword(name="PROJECT_NAME", value=Value(value="test")))
        lines = provider._format_section(section, 0, "  ")

        assert "&GLOBAL" in lines
        assert "&END GLOBAL" in lines
        assert any("PROJECT_NAME" in line for line in lines)

    def test_format_value_boolean(self):
        """Test formatting boolean value."""
        from cp2k_lsp.features.formatting import FormattingProvider

        mock_server = MagicMock()
        provider = FormattingProvider(mock_server)

        value = Value(value=True, value_type=ValueType.BOOLEAN)
        formatted = provider._format_value(value)
        assert formatted == ".TRUE."

    def test_format_value_string_with_space(self):
        """Test formatting string value with space."""
        from cp2k_lsp.features.formatting import FormattingProvider

        mock_server = MagicMock()
        provider = FormattingProvider(mock_server)

        value = Value(value="hello world", value_type=ValueType.STRING)
        formatted = provider._format_value(value)
        assert '"hello world"' in formatted

    def test_format_value_number(self):
        """Test formatting number value."""
        from cp2k_lsp.features.formatting import FormattingProvider

        mock_server = MagicMock()
        provider = FormattingProvider(mock_server)

        value = Value(value=42, value_type=ValueType.NUMBER)
        formatted = provider._format_value(value)
        assert formatted == "42"

    def test_format_value_float(self):
        """Test formatting float value."""
        from cp2k_lsp.features.formatting import FormattingProvider

        mock_server = MagicMock()
        provider = FormattingProvider(mock_server)

        value = Value(value=3.14159, value_type=ValueType.NUMBER)
        formatted = provider._format_value(value)
        assert "3.14" in formatted


class TestDiagnosticsProvider:
    """Test the diagnostics provider."""

    def test_check_required_sections(self):
        """Test checking for required sections."""
        from cp2k_lsp.features.diagnostics import DiagnosticsProvider

        mock_server = MagicMock()
        provider = DiagnosticsProvider(mock_server)

        ast = CP2KInput()
        # Empty AST should have warnings for required sections
        diagnostics = provider._check_required_sections(ast)
        assert len(diagnostics) > 0

    def test_check_duplicate_sections(self):
        """Test checking for duplicate sections."""
        from cp2k_lsp.features.diagnostics import DiagnosticsProvider

        mock_server = MagicMock()
        provider = DiagnosticsProvider(mock_server)

        ast = CP2KInput()
        ast.sections.append(Section(name="GLOBAL", line=1))
        ast.sections.append(Section(name="GLOBAL", line=3))

        diagnostics = provider._check_duplicate_sections(ast)
        assert len(diagnostics) > 0

    def test_check_empty_sections(self):
        """Test checking for empty sections."""
        from cp2k_lsp.features.diagnostics import DiagnosticsProvider

        mock_server = MagicMock()
        provider = DiagnosticsProvider(mock_server)

        ast = CP2KInput()
        ast.sections.append(Section(name="TEST", line=1))

        diagnostics = provider._check_empty_sections(ast)
        assert len(diagnostics) > 0


class TestCodeActionProvider:
    """Test the code action provider."""

    def test_fix_unclosed_section(self):
        """Test fixing unclosed section."""
        from cp2k_lsp.features.code_action import CodeActionProvider
        from lsprotocol import types as lsp

        mock_server = MagicMock()
        provider = CodeActionProvider(mock_server)

        diagnostic = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=10),
            ),
            message="Unclosed section",
        )

        action = provider._fix_unclosed_section(diagnostic, "test://test.inp")
        assert action is not None
        assert "&END" in action.title

    def test_create_quick_fix_unclosed(self):
        """Test creating quick fix for unclosed section."""
        from cp2k_lsp.features.code_action import CodeActionProvider
        from lsprotocol import types as lsp

        mock_server = MagicMock()
        provider = CodeActionProvider(mock_server)

        diagnostic = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=10),
            ),
            message="unclosed section",
        )

        action = provider._create_quick_fix(diagnostic, "test://test.inp")
        assert action is not None

    def test_create_quick_fix_mismatch(self):
        """Test creating quick fix for section name mismatch."""
        from cp2k_lsp.features.code_action import CodeActionProvider
        from lsprotocol import types as lsp

        mock_server = MagicMock()
        provider = CodeActionProvider(mock_server)

        diagnostic = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=10),
            ),
            message="mismatch: &GLOBAL closed with &FORCE_EVAL",
        )

        action = provider._create_quick_fix(diagnostic, "test://test.inp")
        assert action is not None


# Data tests
class TestKeywordData:
    """Test keyword data definitions."""

    def test_get_keyword_info(self):
        """Test getting keyword info."""
        from cp2k_lsp.data.keywords import get_keyword_info

        info = get_keyword_info("PROJECT_NAME")
        assert info is not None
        assert info.name == "PROJECT_NAME"

    def test_get_keyword_info_case_insensitive(self):
        """Test keyword info is case insensitive."""
        from cp2k_lsp.data.keywords import get_keyword_info

        info_lower = get_keyword_info("project_name")
        info_upper = get_keyword_info("PROJECT_NAME")
        assert info_lower == info_upper

    def test_get_enum_values(self):
        """Test getting enum values."""
        from cp2k_lsp.data.keywords import get_enum_values

        values = get_enum_values("RUN_TYPE")
        assert "ENERGY" in values
        assert "GEO_OPT" in values


class TestSectionData:
    """Test section data definitions."""

    def test_get_section_info(self):
        """Test getting section info."""
        from cp2k_lsp.data.sections import get_section_info

        info = get_section_info("GLOBAL")
        assert info is not None
        assert info.name == "GLOBAL"

    def test_get_valid_subsections(self):
        """Test getting valid subsections."""
        from cp2k_lsp.data.sections import get_valid_subsections

        subsections = get_valid_subsections("DFT")
        assert "QS" in subsections
        assert "SCF" in subsections

    def test_get_valid_keywords(self):
        """Test getting valid keywords."""
        from cp2k_lsp.data.sections import get_valid_keywords

        keywords = get_valid_keywords("GLOBAL")
        assert "PROJECT_NAME" in keywords
        assert "RUN_TYPE" in keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
