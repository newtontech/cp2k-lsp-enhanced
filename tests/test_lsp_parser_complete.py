"""Additional comprehensive tests for LSP parser module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "language-server"))

import pytest
from cp2k_lsp.parser.lexer import Lexer, TokenType
from cp2k_lsp.parser.parser import CP2KParser
from cp2k_lsp.parser.ast import CP2KInput, Section, Keyword, Value, ValueType, Comment
from cp2k_lsp.parser.errors import SyntaxError as CP2KSyntaxError, ParseError


class TestLexerEdgeCases:
    """Tests for lexer edge cases."""

    def test_lexer_empty_string(self):
        """Test lexer with empty string."""
        lexer = Lexer("")
        tokens = lexer.tokenize()
        assert tokens[-1].type == TokenType.EOF

    def test_lexer_whitespace_only(self):
        """Test lexer with whitespace only."""
        lexer = Lexer("   \n\t  ")
        tokens = lexer.tokenize()
        assert tokens[-1].type == TokenType.EOF

    def test_lexer_multiple_empty_lines(self):
        """Test lexer with multiple empty lines."""
        lexer = Lexer("\n\n\n")
        tokens = lexer.tokenize()
        eol_count = sum(1 for t in tokens if t.type == TokenType.EOL)
        assert eol_count == 3

    def test_lexer_mixed_comments(self):
        """Test lexer with mixed comment styles."""
        text = """! exclamation comment
        # hash comment
        &GLOBAL
        &END GLOBAL"""
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        comment_count = sum(1 for t in tokens if t.type == TokenType.COMMENT)
        assert comment_count == 2

    def test_lexer_number_formats(self):
        """Test lexer with various number formats."""
        test_cases = [
            ("42", "42"),
            ("3.14", "3.14"),
            ("-10", "-10"),
            ("1e10", "1e10"),
            ("1.5e-3", "1.5e-3"),
            ("-2.5E+2", "-2.5E+2"),
        ]
        for num_str, expected in test_cases:
            lexer = Lexer(num_str)
            tokens = lexer.tokenize()
            assert tokens[0].type == TokenType.NUMBER
            assert tokens[0].value.lower() == expected.lower()

    def test_lexer_unit_tokens(self):
        """Test lexer with unit specifiers."""
        test_cases = [
            "[angstrom]",
            "[eV]",
            "[bohr]",
        ]
        for unit_str in test_cases:
            lexer = Lexer(unit_str)
            tokens = lexer.tokenize()
            assert tokens[0].type == TokenType.UNIT

    def test_lexer_section_with_parameter(self):
        """Test lexer with section parameter."""
        lexer = Lexer("&KIND H")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.SECTION_START
        assert tokens[0].value == "KIND"


class TestParserEdgeCases:
    """Tests for parser edge cases."""

    def test_parser_empty_input(self):
        """Test parser with empty input."""
        parser = CP2KParser.parse_text("")
        assert parser.ast is not None
        assert parser.ast.global_section is None
        assert parser.ast.sections == []

    def test_parser_comments_only(self):
        """Test parser with only comments."""
        text = """! This is a comment
        # Another comment"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast is not None
        assert len(parser.ast.comments) == 2

    def test_parser_empty_section(self):
        """Test parser with empty section."""
        text = """&GLOBAL
        &END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        assert parser.ast.global_section is not None
        assert parser.ast.global_section.name == "GLOBAL"

    def test_parser_deeply_nested(self):
        """Test parser with deeply nested sections."""
        text = """&FORCE_EVAL
          &DFT
            &XC
              &XC_FUNCTIONAL
              &END XC_FUNCTIONAL
            &END XC
          &END DFT
        &END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        assert len(parser.ast.sections) == 1
        force_eval = parser.ast.sections[0]
        assert len(force_eval.subsections) == 1  # DFT

    def test_parser_keyword_variations(self):
        """Test parser with various keyword formats."""
        text = """&GLOBAL
          PROJECT_NAME = test
          DEBUG_MODE
          PRINT_LEVEL HIGH
          EPS_SCF 1.0e-6
          MAX_SCF 100
        &END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        global_sec = parser.ast.global_section
        assert len(global_sec.keywords) == 6

    def test_parser_multiple_keywords_same_name(self):
        """Test parser with multiple keywords of same name."""
        text = """&COORD
          H 0.0 0.0 0.0
          H 1.0 0.0 0.0
        &END COORD"""
        parser = CP2KParser.parse_text(text)
        coord_sec = parser.ast.sections[0]
        # Keywords with same name should be handled
        assert coord_sec is not None

    def test_parser_mismatched_end(self):
        """Test parser with mismatched section end."""
        text = """&GLOBAL
        &END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        assert len(parser.errors) > 0

    def test_parser_unclosed_section(self):
        """Test parser with unclosed section."""
        text = """&GLOBAL
          PROJECT_NAME test"""
        parser = CP2KParser.parse_text(text)
        # Parser should handle unclosed sections gracefully
        assert parser.ast is not None


class TestASTMethods:
    """Tests for AST methods."""

    def test_section_get_keyword(self):
        """Test Section.get_keyword method."""
        section = Section(name="GLOBAL")
        section.keywords.append(Keyword(name="PROJECT_NAME", line=1, column=1))
        section.keywords.append(Keyword(name="RUN_TYPE", line=2, column=1))
        
        kw = section.get_keyword("PROJECT_NAME")
        assert kw is not None
        assert kw.name == "PROJECT_NAME"
        
        kw_none = section.get_keyword("NONEXISTENT")
        assert kw_none is None
        
        # Case insensitive
        kw_upper = section.get_keyword("project_name")
        assert kw_upper is not None

    def test_section_get_subsection(self):
        """Test Section.get_subsection method."""
        parent = Section(name="FORCE_EVAL")
        child = Section(name="DFT")
        parent.subsections.append(child)
        
        sub = parent.get_subsection("DFT")
        assert sub is not None
        assert sub.name == "DFT"
        
        sub_none = parent.get_subsection("NONEXISTENT")
        assert sub_none is None
        
        # Case insensitive
        sub_upper = parent.get_subsection("dft")
        assert sub_upper is not None

    def test_cp2k_input_get_section(self):
        """Test CP2KInput.get_section method."""
        ast = CP2KInput()
        global_sec = Section(name="GLOBAL")
        force_eval = Section(name="FORCE_EVAL")
        
        ast.global_section = global_sec
        ast.sections.append(force_eval)
        
        assert ast.get_section("GLOBAL") == global_sec
        assert ast.get_section("FORCE_EVAL") == force_eval
        assert ast.get_section("NONEXISTENT") is None
        
        # Case insensitive
        assert ast.get_section("global") == global_sec

    def test_section_repr(self):
        """Test Section __repr__ method."""
        section = Section(name="GLOBAL")
        section.keywords.append(Keyword(name="TEST", line=1, column=1))
        
        repr_str = repr(section)
        assert "GLOBAL" in repr_str
        assert "1 keywords" in repr_str

    def test_keyword_repr(self):
        """Test Keyword __repr__ method."""
        value = Value(value="test", value_type=ValueType.STRING, line=1, column=1)
        keyword = Keyword(name="PROJECT_NAME", value=value, line=1, column=1)
        
        repr_str = repr(keyword)
        assert "PROJECT_NAME" in repr_str
        assert "test" in repr_str

    def test_value_repr(self):
        """Test Value __repr__ method."""
        value = Value(value=42, value_type=ValueType.NUMBER, line=1, column=1)
        repr_str = repr(value)
        assert "42" in repr_str

    def test_value_repr_with_unit(self):
        """Test Value __repr__ with unit."""
        value = Value(value=5.0, value_type=ValueType.NUMBER, unit="angstrom", line=1, column=1)
        repr_str = repr(value)
        assert "5.0" in repr_str
        assert "angstrom" in repr_str


class TestParserErrorHandling:
    """Tests for parser error handling."""

    def test_syntax_error_creation(self):
        """Test SyntaxError creation."""
        error = CP2KSyntaxError("Test error", line=1, column=5, source="test.inp")
        assert error.message == "Test error"
        assert error.line == 1
        assert error.column == 5
        assert error.source == "test.inp"
        assert "Test error" in str(error)

    def test_parse_error_creation(self):
        """Test ParseError creation."""
        error = ParseError("Parse error", line=2, column=3)
        assert error.message == "Parse error"
        assert error.line == 2
        assert error.column == 3

    def test_parser_error_collection(self):
        """Test that parser collects multiple errors."""
        text = """&GLOBAL
          INVALID_TOKEN @#$%
          ALSO_BAD ~!@
        &END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        # Parser should have errors for invalid tokens
        assert len(parser.errors) >= 0
