"""Comprehensive tests for LSP server and related modules."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

# Add language-server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "language-server"))

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol import types as lsp

from cp2k_lsp.server import CP2KLanguageServer, main
from cp2k_lsp.parser.parser import CP2KParser
from cp2k_lsp.parser.lexer import Lexer, TokenType
from cp2k_lsp.parser.ast import CP2KInput, Section, Keyword, Value, ValueType, Comment
from cp2k_lsp.parser.errors import ParseError, SyntaxError
from cp2k_lsp.data.keywords import KeywordInfo, KeywordType, get_keyword_info, get_enum_values, CP2K_KEYWORDS
from cp2k_lsp.data.sections import SectionInfo, get_section_info, get_valid_subsections, get_valid_keywords, CP2K_SECTIONS


class MockDocument:
    """Mock document for testing."""
    def __init__(self, source, lines=None, uri="file://test.inp"):
        self.source = source
        self.lines = lines or source.split('\n')
        self.uri = uri
        self.path = uri.replace("file://", "")


class MockServer:
    """Mock LSP server for testing."""
    def __init__(self, document=None):
        self.workspace = MagicMock()
        self.document = document or MockDocument("")
        self.workspace.get_text_document.return_value = self.document
        self._errors = []
        self._ast = None
        self.parsed_documents = {}
        self.parser_errors = {}
        
    def get_errors(self, uri):
        return self._errors
    
    def set_errors(self, errors):
        self._errors = errors
        
    def get_ast(self, uri):
        return self._ast
    
    def set_ast(self, ast):
        self._ast = ast


class TestCP2KLanguageServer:
    """Tests for CP2KLanguageServer."""
    
    def test_server_init(self):
        """Test server initialization."""
        server = CP2KLanguageServer()
        assert server.name == "cp2k-lsp"
        assert server.version == "0.1.0"
        assert isinstance(server.parsed_documents, dict)
        assert isinstance(server.parser_errors, dict)
    
    def test_server_setup_handlers(self):
        """Test handler setup."""
        server = CP2KLanguageServer()
        # Handlers are set up in __init__
        assert hasattr(server, 'diagnostics')
        assert hasattr(server, 'completion')
        assert hasattr(server, 'hover')
        assert hasattr(server, 'formatting')
        assert hasattr(server, 'code_action')
    
    def test_parse_document(self):
        """Test document parsing."""
        server = CP2KLanguageServer()
        
        # Mock workspace document
        mock_doc = MockDocument("&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL")
        mock_workspace = MagicMock()
        mock_workspace.get_text_document.return_value = mock_doc
        
        # Mock the lsp workspace
        mock_lsp = MagicMock()
        mock_lsp.workspace = mock_workspace
        with patch.object(server, 'lsp', mock_lsp):
            server._parse_document("file://test.inp")
        
        assert "file://test.inp" in server.parsed_documents
        assert "file://test.inp" in server.parser_errors
    
    def test_get_ast_cached(self):
        """Test getting cached AST."""
        server = CP2KLanguageServer()
        
        mock_ast = CP2KInput()
        server.parsed_documents["file://test.inp"] = mock_ast
        server.parser_errors["file://test.inp"] = []
        
        result = server.get_ast("file://test.inp")
        assert result == mock_ast
    
    def test_get_ast_not_cached(self):
        """Test getting AST when not cached."""
        server = CP2KLanguageServer()
        
        mock_doc = MockDocument("&GLOBAL\n&END GLOBAL")
        mock_workspace = MagicMock()
        mock_workspace.get_text_document.return_value = mock_doc
        
        # Mock the lsp workspace
        mock_lsp = MagicMock()
        mock_lsp.workspace = mock_workspace
        with patch.object(server, 'lsp', mock_lsp):
            result = server.get_ast("file://test.inp")
        assert result is not None
    
    def test_get_errors_cached(self):
        """Test getting cached errors."""
        server = CP2KLanguageServer()
        
        server.parser_errors["file://test.inp"] = ["error1", "error2"]
        server.parsed_documents["file://test.inp"] = None
        
        result = server.get_errors("file://test.inp")
        assert result == ["error1", "error2"]


class TestCP2KParser:
    """Tests for CP2KParser."""
    
    def test_parser_init(self):
        """Test parser initialization."""
        tokens = []
        parser = CP2KParser(tokens, "test.inp")
        assert parser.tokens == tokens
        assert parser.source == "test.inp"
        assert parser.pos == 0
        assert parser.errors == []
    
    def test_current_token(self):
        """Test getting current token."""
        from cp2k_lsp.parser.lexer import Token
        tokens = [
            Token(TokenType.KEYWORD, "PROJECT_NAME", 1, 1),
            Token(TokenType.EOF, "", 1, 15)
        ]
        parser = CP2KParser(tokens)
        assert parser.current().type == TokenType.KEYWORD
    
    def test_advance(self):
        """Test advancing token position."""
        from cp2k_lsp.parser.lexer import Token
        tokens = [
            Token(TokenType.KEYWORD, "PROJECT_NAME", 1, 1),
            Token(TokenType.EOF, "", 1, 15)
        ]
        parser = CP2KParser(tokens)
        parser.advance()
        assert parser.pos == 1
    
    def test_expect_valid(self):
        """Test expecting a valid token type."""
        from cp2k_lsp.parser.lexer import Token
        tokens = [
            Token(TokenType.KEYWORD, "PROJECT_NAME", 1, 1),
            Token(TokenType.EOF, "", 1, 15)
        ]
        parser = CP2KParser(tokens)
        token = parser.expect(TokenType.KEYWORD)
        assert token.type == TokenType.KEYWORD
    
    def test_match(self):
        """Test matching token types."""
        from cp2k_lsp.parser.lexer import Token
        tokens = [
            Token(TokenType.KEYWORD, "PROJECT_NAME", 1, 1),
            Token(TokenType.EOF, "", 1, 15)
        ]
        parser = CP2KParser(tokens)
        assert parser.match(TokenType.KEYWORD) == True
        assert parser.match(TokenType.SECTION_START) == False
    
    def test_parse_empty(self):
        """Test parsing empty input."""
        from cp2k_lsp.parser.lexer import Token
        tokens = [Token(TokenType.EOF, "", 1, 1)]
        parser = CP2KParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, CP2KInput)
        assert ast.sections == []
    
    def test_parse_global_section(self):
        """Test parsing global section."""
        text = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        parser = CP2KParser.parse_text(text, "test.inp")
        assert parser.ast is not None
        assert parser.ast.global_section is not None
        assert parser.ast.global_section.name == "GLOBAL"
    
    def test_parse_section(self):
        """Test parsing a section."""
        text = "&FORCE_EVAL\n  METHOD QUICKSTEP\n&END FORCE_EVAL"
        parser = CP2KParser.parse_text(text, "test.inp")
        assert len(parser.ast.sections) == 1
        assert parser.ast.sections[0].name == "FORCE_EVAL"
    
    def test_parse_keyword_with_value(self):
        """Test parsing keyword with value."""
        text = "&GLOBAL\n  PROJECT_NAME = test\n&END GLOBAL"
        parser = CP2KParser.parse_text(text, "test.inp")
        section = parser.ast.global_section
        assert len(section.keywords) == 1
        assert section.keywords[0].name == "PROJECT_NAME"
    
    def test_parse_comment(self):
        """Test parsing comments."""
        text = "! This is a comment\n&GLOBAL\n&END GLOBAL"
        parser = CP2KParser.parse_text(text, "test.inp")
        assert len(parser.ast.comments) >= 1


class TestLexer:
    """Tests for Lexer."""
    
    def test_lexer_init(self):
        """Test lexer initialization."""
        lexer = Lexer("test content", "test.inp")
        assert lexer.text == "test content"
        assert lexer.source == "test.inp"
        assert lexer.pos == 0
        assert lexer.line == 1
        assert lexer.column == 1
    
    def test_tokenize_empty(self):
        """Test tokenizing empty string."""
        lexer = Lexer("")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
    
    def test_tokenize_section_start(self):
        """Test tokenizing section start."""
        lexer = Lexer("&GLOBAL")
        tokens = lexer.tokenize()
        assert any(t.type == TokenType.SECTION_START for t in tokens)
    
    def test_tokenize_section_end(self):
        """Test tokenizing section end."""
        lexer = Lexer("&END GLOBAL")
        tokens = lexer.tokenize()
        assert any(t.type == TokenType.SECTION_END for t in tokens)
    
    def test_tokenize_keyword(self):
        """Test tokenizing keyword."""
        lexer = Lexer("PROJECT_NAME")
        tokens = lexer.tokenize()
        keyword_tokens = [t for t in tokens if t.type == TokenType.KEYWORD]
        assert len(keyword_tokens) == 1
        assert keyword_tokens[0].value == "PROJECT_NAME"
    
    def test_tokenize_string(self):
        """Test tokenizing string."""
        lexer = Lexer('"test string"')
        tokens = lexer.tokenize()
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) == 1
        assert string_tokens[0].value == "test string"
    
    def test_tokenize_number(self):
        """Test tokenizing number."""
        lexer = Lexer("123.456")
        tokens = lexer.tokenize()
        number_tokens = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(number_tokens) == 1
        assert number_tokens[0].value == "123.456"
    
    def test_tokenize_boolean_true(self):
        """Test tokenizing boolean true."""
        lexer = Lexer(".TRUE.")
        tokens = lexer.tokenize()
        bool_tokens = [t for t in tokens if t.type == TokenType.BOOLEAN]
        assert len(bool_tokens) == 1
        assert bool_tokens[0].value == ".TRUE."
    
    def test_tokenize_boolean_false(self):
        """Test tokenizing boolean false."""
        lexer = Lexer(".FALSE.")
        tokens = lexer.tokenize()
        bool_tokens = [t for t in tokens if t.type == TokenType.BOOLEAN]
        assert len(bool_tokens) == 1
        assert bool_tokens[0].value == ".FALSE."
    
    def test_tokenize_comment(self):
        """Test tokenizing comment."""
        lexer = Lexer("! comment text")
        tokens = lexer.tokenize()
        comment_tokens = [t for t in tokens if t.type == TokenType.COMMENT]
        assert len(comment_tokens) == 1
        assert comment_tokens[0].value == "! comment text"
    
    def test_tokenize_assignment(self):
        """Test tokenizing assignment."""
        lexer = Lexer("=")
        tokens = lexer.tokenize()
        assign_tokens = [t for t in tokens if t.type == TokenType.ASSIGN]
        assert len(assign_tokens) == 1


class TestAST:
    """Tests for AST classes."""
    
    def test_value_node(self):
        """Test Value node."""
        value = Value(value=42, value_type=ValueType.NUMBER, line=1, column=1)
        assert value.value == 42
        assert value.value_type == ValueType.NUMBER
        assert "42" in repr(value)
    
    def test_value_node_with_unit(self):
        """Test Value node with unit."""
        value = Value(value=10.0, value_type=ValueType.NUMBER, unit="angstrom")
        assert value.unit == "angstrom"
        assert "angstrom" in repr(value)
    
    def test_keyword_node(self):
        """Test Keyword node."""
        value = Value(value="test", value_type=ValueType.STRING)
        keyword = Keyword(name="PROJECT_NAME", value=value, line=1, column=1)
        assert keyword.name == "PROJECT_NAME"
        assert "PROJECT_NAME" in repr(keyword)
    
    def test_comment_node(self):
        """Test Comment node."""
        comment = Comment(text="test comment", line=1, column=1)
        assert comment.text == "test comment"
        assert "test comment" in repr(comment)
    
    def test_section_node(self):
        """Test Section node."""
        section = Section(name="GLOBAL", line=1, column=1)
        assert section.name == "GLOBAL"
        assert section.keywords == []
        assert section.subsections == []
        assert "GLOBAL" in repr(section)
    
    def test_section_get_keyword(self):
        """Test Section.get_keyword method."""
        section = Section(name="GLOBAL")
        keyword = Keyword(name="PROJECT_NAME", value=Value(value="test"))
        section.keywords.append(keyword)
        
        found = section.get_keyword("PROJECT_NAME")
        assert found == keyword
        
        not_found = section.get_keyword("NONEXISTENT")
        assert not_found is None
    
    def test_section_get_subsection(self):
        """Test Section.get_subsection method."""
        section = Section(name="FORCE_EVAL")
        subsection = Section(name="DFT")
        section.subsections.append(subsection)
        
        found = section.get_subsection("DFT")
        assert found == subsection
        
        not_found = section.get_subsection("NONEXISTENT")
        assert not_found is None
    
    def test_cp2kinput_node(self):
        """Test CP2KInput node."""
        inp = CP2KInput(line=1, column=1)
        assert inp.global_section is None
        assert inp.sections == []
        assert inp.comments == []
    
    def test_cp2kinput_get_section(self):
        """Test CP2KInput.get_section method."""
        inp = CP2KInput()
        global_section = Section(name="GLOBAL")
        inp.global_section = global_section
        
        found = inp.get_section("GLOBAL")
        assert found == global_section
        
        section = Section(name="FORCE_EVAL")
        inp.sections.append(section)
        
        found2 = inp.get_section("FORCE_EVAL")
        assert found2 == section
        
        not_found = inp.get_section("NONEXISTENT")
        assert not_found is None


class TestParseErrors:
    """Tests for parser errors."""
    
    def test_parse_error(self):
        """Test ParseError."""
        error = ParseError("test error", 1, 5, "test.inp")
        assert error.message == "test error"
        assert error.line == 1
        assert error.column == 5
        assert error.source == "test.inp"
        assert "test.inp" in str(error)
    
    def test_parse_error_no_source(self):
        """Test ParseError without source."""
        error = ParseError("test error", 1, 5)
        assert error.source is None
        assert "line 1" in str(error)
    
    def test_syntax_error(self):
        """Test SyntaxError."""
        error = SyntaxError("syntax error", 1, 5, "test.inp", expected="keyword", found="section")
        assert error.expected == "keyword"
        assert error.found == "section"
        assert "keyword" in str(error)
        assert "section" in str(error)


class TestKeywordData:
    """Tests for keyword data module."""
    
    def test_keyword_type_enum(self):
        """Test KeywordType enum."""
        assert KeywordType.STRING.value == "string"
        assert KeywordType.INTEGER.value == "integer"
        assert KeywordType.REAL.value == "real"
        assert KeywordType.BOOLEAN.value == "boolean"
        assert KeywordType.ENUM.value == "enum"
        assert KeywordType.ARRAY.value == "array"
        assert KeywordType.FILE.value == "file"
    
    def test_keyword_info(self):
        """Test KeywordInfo dataclass."""
        info = KeywordInfo(
            name="TEST_KEYWORD",
            description="A test keyword",
            keyword_type=KeywordType.STRING,
            default="default_value"
        )
        assert info.name == "TEST_KEYWORD"
        assert info.description == "A test keyword"
        assert info.keyword_type == KeywordType.STRING
        assert info.default == "default_value"
    
    def test_get_keyword_info(self):
        """Test get_keyword_info function."""
        info = get_keyword_info("PROJECT_NAME")
        assert info is not None
        assert info.name == "PROJECT_NAME"
        
        not_found = get_keyword_info("NONEXISTENT")
        assert not_found is None
    
    def test_get_keyword_info_case_insensitive(self):
        """Test get_keyword_info is case insensitive."""
        info_lower = get_keyword_info("project_name")
        info_upper = get_keyword_info("PROJECT_NAME")
        assert info_lower == info_upper
    
    def test_get_enum_values(self):
        """Test get_enum_values function."""
        values = get_enum_values("RUN_TYPE")
        assert "ENERGY" in values
        assert "GEO_OPT" in values
        
        no_values = get_enum_values("PROJECT_NAME")
        assert no_values == []
    
    def test_cp2k_keywords_defined(self):
        """Test that CP2K_KEYWORDS is populated."""
        assert len(CP2K_KEYWORDS) > 0
        assert "PROJECT_NAME" in CP2K_KEYWORDS
        assert "RUN_TYPE" in CP2K_KEYWORDS


class TestSectionData:
    """Tests for section data module."""
    
    def test_section_info(self):
        """Test SectionInfo dataclass."""
        info = SectionInfo(
            name="TEST_SECTION",
            description="A test section",
            keywords=["KEY1", "KEY2"],
            subsections=["SUB1"],
            required=True,
            repeats=False
        )
        assert info.name == "TEST_SECTION"
        assert info.description == "A test section"
        assert info.keywords == ["KEY1", "KEY2"]
        assert info.subsections == ["SUB1"]
        assert info.required == True
        assert info.repeats == False
    
    def test_get_section_info(self):
        """Test get_section_info function."""
        info = get_section_info("GLOBAL")
        assert info is not None
        assert info.name == "GLOBAL"
        
        not_found = get_section_info("NONEXISTENT")
        assert not_found is None
    
    def test_get_section_info_case_insensitive(self):
        """Test get_section_info is case insensitive."""
        info_lower = get_section_info("global")
        info_upper = get_section_info("GLOBAL")
        assert info_lower == info_upper
    
    def test_get_valid_subsections(self):
        """Test get_valid_subsections function."""
        subsections = get_valid_subsections("GLOBAL")
        assert isinstance(subsections, list)
        
        empty = get_valid_subsections("NONEXISTENT")
        assert empty == []
    
    def test_get_valid_keywords(self):
        """Test get_valid_keywords function."""
        keywords = get_valid_keywords("GLOBAL")
        assert isinstance(keywords, list)
        assert "PROJECT_NAME" in keywords
        
        empty = get_valid_keywords("NONEXISTENT")
        assert empty == []
    
    def test_cp2k_sections_defined(self):
        """Test that CP2K_SECTIONS is populated."""
        assert len(CP2K_SECTIONS) > 0
        assert "GLOBAL" in CP2K_SECTIONS
        assert "FORCE_EVAL" in CP2K_SECTIONS
        assert "DFT" in CP2K_SECTIONS
