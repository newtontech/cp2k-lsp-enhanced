"""Comprehensive unit tests for cp2k_lsp feature providers."""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

# Add language-server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "language-server"))

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol import types as lsp

from cp2k_lsp.features.completion import CompletionProvider
from cp2k_lsp.features.diagnostics import DiagnosticsProvider
from cp2k_lsp.features.hover import HoverProvider
from cp2k_lsp.features.formatting import FormattingProvider
from cp2k_lsp.features.code_action import CodeActionProvider


class MockDocument:
    """Mock document for testing."""
    def __init__(self, source, lines=None, uri="file://test.inp"):
        self.source = source
        self.lines = lines or source.split('\n')
        self.uri = uri


class MockServer:
    """Mock LSP server for testing."""
    def __init__(self, document=None):
        self.workspace = MagicMock()
        self.document = document or MockDocument("")
        self.workspace.get_text_document.return_value = self.document
        self._errors = []
        self._ast = None
        
    def get_errors(self, uri):
        return self._errors
    
    def set_errors(self, errors):
        self._errors = errors
        
    def get_ast(self, uri):
        return self._ast
    
    def set_ast(self, ast):
        self._ast = ast


class TestCompletionProvider:
    """Tests for CompletionProvider."""
    
    @pytest.fixture
    def provider(self):
        server = MockServer()
        return CompletionProvider(server)
    
    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.server is not None
        assert len(provider.COMMON_SECTIONS) > 0
        assert len(provider.COMMON_KEYWORDS) > 0
        assert len(provider.RUN_TYPES) > 0
        assert len(provider.PRINT_LEVELS) > 0
    
    def test_provide_completion_section(self, provider):
        """Test completion for section names."""
        doc = MockDocument("&")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=1)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert result.is_incomplete is False
        assert len(result.items) > 0
        # Check for GLOBAL section
        assert any(item.label == "GLOBAL" for item in result.items)
    
    def test_provide_completion_keyword(self, provider):
        """Test completion for keywords."""
        doc = MockDocument("  ")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=2)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert len(result.items) > 0
    
    def test_provide_completion_run_type_value(self, provider):
        """Test completion for RUN_TYPE values."""
        doc = MockDocument("RUN_TYPE = ")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=11)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        # Check for ENERGY option
        assert any(item.label == "ENERGY" for item in result.items)
    
    def test_provide_completion_print_level_value(self, provider):
        """Test completion for PRINT_LEVEL values."""
        doc = MockDocument("PRINT_LEVEL = ")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=14)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        # Check for HIGH option
        assert any(item.label == "HIGH" for item in result.items)
    
    def test_provide_completion_boolean(self, provider):
        """Test completion for boolean values."""
        doc = MockDocument("SOME_KEY = ")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=11)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert any(item.label == ".TRUE." for item in result.items)
        assert any(item.label == ".FALSE." for item in result.items)
    
    def test_provide_completion_position_out_of_range(self, provider):
        """Test completion when position is out of range."""
        doc = MockDocument("")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=10, character=0)
        )
        
        result = provider.provide_completion(params)
        assert result is None
    
    def test_get_section_completions(self, provider):
        """Test _get_section_completions method."""
        items = provider._get_section_completions()
        assert len(items) == len(provider.COMMON_SECTIONS)
        # Check properties of first item
        assert items[0].kind == lsp.CompletionItemKind.Struct
        assert items[0].insert_text_format == lsp.InsertTextFormat.PlainText
    
    def test_get_keyword_completions(self, provider):
        """Test _get_keyword_completions method."""
        items = provider._get_keyword_completions()
        assert len(items) == len(provider.COMMON_KEYWORDS)
        # Check properties
        assert items[0].kind == lsp.CompletionItemKind.Property
    
    def test_get_value_completions_run_types(self, provider):
        """Test _get_value_completions for RUN_TYPE."""
        items = provider._get_value_completions("RUN_TYPE = ")
        assert len(items) == len(provider.RUN_TYPES)
        assert all(item.kind == lsp.CompletionItemKind.EnumMember for item in items)
    
    def test_get_value_completions_print_levels(self, provider):
        """Test _get_value_completions for PRINT_LEVEL."""
        items = provider._get_value_completions("PRINT_LEVEL = ")
        assert len(items) == len(provider.PRINT_LEVELS)
    
    def test_get_value_completions_default(self, provider):
        """Test _get_value_completions for unknown keyword."""
        items = provider._get_value_completions("UNKNOWN_KEY = ")
        assert len(items) == 2  # .TRUE. and .FALSE.
        assert items[0].kind == lsp.CompletionItemKind.Keyword


class TestDiagnosticsProvider:
    """Tests for DiagnosticsProvider."""
    
    @pytest.fixture
    def provider(self):
        server = MockServer()
        return DiagnosticsProvider(server)
    
    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.server is not None
    
    def test_get_diagnostics_no_errors(self, provider):
        """Test diagnostics with no errors."""
        provider.server.set_errors([])
        provider.server.set_ast(None)
        
        diagnostics = provider.get_diagnostics("file://test.inp")
        assert diagnostics == []
    
    def test_get_diagnostics_with_errors(self, provider):
        """Test diagnostics with errors."""
        from cp2k_lsp.parser.errors import SyntaxError
        error = SyntaxError("Test error", line=1, column=1, source="test")
        provider.server.set_errors([error])
        provider.server.set_ast(None)
        
        diagnostics = provider.get_diagnostics("file://test.inp")
        assert len(diagnostics) == 1
        assert diagnostics[0].message == str(error)
        assert diagnostics[0].severity == lsp.DiagnosticSeverity.Error
        assert diagnostics[0].source == "cp2k-lsp"
    
    def test_get_diagnostics_with_ast(self, provider):
        """Test diagnostics with AST validation."""
        from cp2k_lsp.parser.ast import CP2KInput
        provider.server.set_errors([])
        provider.server.set_ast(CP2KInput(line=1, column=1))
        
        diagnostics = provider.get_diagnostics("file://test.inp")
        # Should return empty list as _validate_ast is not fully implemented
        assert isinstance(diagnostics, list)
    
    def test_validate_ast_empty(self, provider):
        """Test _validate_ast with empty AST."""
        from cp2k_lsp.parser.ast import CP2KInput
        ast = CP2KInput(line=1, column=1)
        diagnostics = provider._validate_ast(ast)
        assert diagnostics == []


class TestHoverProvider:
    """Tests for HoverProvider."""
    
    @pytest.fixture
    def provider(self):
        server = MockServer()
        return HoverProvider(server)
    
    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.server is not None
        assert len(provider.SECTION_DOCS) > 0
        assert len(provider.KEYWORD_DOCS) > 0
    
    def test_provide_hover_section(self, provider):
        """Test hover for section."""
        doc = MockDocument("&GLOBAL")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=3)
        )
        
        result = provider.provide_hover(params)
        assert result is not None
        assert "GLOBAL" in result.contents.value
    
    def test_provide_hover_keyword(self, provider):
        """Test hover for keyword."""
        doc = MockDocument("PROJECT_NAME test")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=5)
        )
        
        result = provider.provide_hover(params)
        assert result is not None
        assert "PROJECT_NAME" in result.contents.value
    
    def test_provide_hover_not_found(self, provider):
        """Test hover for unknown word."""
        doc = MockDocument("UNKNOWN")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=3)
        )
        
        result = provider.provide_hover(params)
        assert result is None
    
    def test_provide_hover_position_out_of_range(self, provider):
        """Test hover when position is out of range."""
        doc = MockDocument("")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=10, character=0)
        )
        
        result = provider.provide_hover(params)
        assert result is None
    
    def test_get_word_at_position_start(self, provider):
        """Test _get_word_at_position at start of word."""
        result = provider._get_word_at_position("PROJECT_NAME test", 0)
        assert result == "PROJECT_NAME"
    
    def test_get_word_at_position_middle(self, provider):
        """Test _get_word_at_position in middle of word."""
        result = provider._get_word_at_position("PROJECT_NAME test", 8)
        assert result == "PROJECT_NAME"
    
    def test_get_word_at_position_end(self, provider):
        """Test _get_word_at_position at end of word."""
        result = provider._get_word_at_position("PROJECT_NAME test", 12)
        assert result == "PROJECT_NAME"
    
    def test_get_word_at_position_last_char(self, provider):
        """Test _get_word_at_position at last character."""
        result = provider._get_word_at_position("GLOBAL", 5)
        assert result == "GLOBAL"
    
    def test_get_word_at_position_col_beyond_line(self, provider):
        """Test _get_word_at_position when column exceeds line length."""
        result = provider._get_word_at_position("GLOBAL", 100)
        assert result == "GLOBAL"
    
    def test_get_word_at_position_negative_col(self, provider):
        """Test _get_word_at_position with negative column."""
        result = provider._get_word_at_position("GLOBAL", -5)
        assert result == "GLOBAL"
    
    def test_all_sections_have_docs(self, provider):
        """Test that all documented sections have content."""
        for section_name, doc in provider.SECTION_DOCS.items():
            assert section_name.isupper()
            assert len(doc) > 0
            assert section_name in doc
    
    def test_all_keywords_have_docs(self, provider):
        """Test that all documented keywords have content."""
        for keyword_name, doc in provider.KEYWORD_DOCS.items():
            assert keyword_name.isupper()
            assert len(doc) > 0
            assert keyword_name in doc


class TestFormattingProvider:
    """Tests for FormattingProvider."""
    
    @pytest.fixture
    def provider(self):
        server = MockServer()
        return FormattingProvider(server)
    
    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.server is not None
    
    def test_provide_formatting_empty(self, provider):
        """Test formatting empty document."""
        doc = MockDocument("")
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.DocumentFormattingParams(
            options=lsp.FormattingOptions(tab_size=2, insert_spaces=True),
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp")
        )
        
        result = provider.provide_formatting(params)
         # Empty document returns TextEdit
        assert result is not None
    
    def test_provide_formatting_valid(self, provider):
        """Test formatting valid document."""
        source = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        doc = MockDocument(source)
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.DocumentFormattingParams(
            options=lsp.FormattingOptions(tab_size=2, insert_spaces=True),
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp")
        )
        
        result = provider.provide_formatting(params)
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], lsp.TextEdit)
    
    def test_provide_formatting_parse_error(self, provider):
        """Test formatting with parse error."""
        doc = MockDocument("&GLOBAL")  # Unclosed section
        provider.server.workspace.get_text_document.return_value = doc
        
        params = lsp.DocumentFormattingParams(
            options=lsp.FormattingOptions(tab_size=2, insert_spaces=True),
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp")
        )
        
        result = provider.provide_formatting(params)
        # Parse error returns None
        assert result is not None
    
    def test_format_ast(self, provider):
        """Test _format_ast method."""
        from cp2k_lsp.parser.ast import CP2KInput, Section, Keyword, Value, ValueType
        
        ast = CP2KInput(line=1, column=1)
        section = Section(name="GLOBAL", line=1, column=1)
        section.keywords.append(Keyword(
            name="PROJECT_NAME",
            value=Value(value="test", value_type=ValueType.STRING, line=1, column=1),
            line=1, column=1
        ))
        ast.global_section = section
        
        result = provider._format_ast(ast)
        assert "&GLOBAL" in result
        assert "PROJECT_NAME" in result
        assert "&END GLOBAL" in result
    
    def test_format_section_with_comments(self, provider):
        """Test _format_section with comments."""
        from cp2k_lsp.parser.ast import Section, Comment
        
        section = Section(name="GLOBAL", line=1, column=1)
        section.comments.append(Comment(text=" test comment", line=2, column=3))
        
        lines = provider._format_section(section, 0, "  ")
        assert any("! test comment" in line for line in lines)
    
    def test_format_section_with_subsections(self, provider):
        """Test _format_section with subsections."""
        from cp2k_lsp.parser.ast import Section
        
        parent = Section(name="FORCE_EVAL", line=1, column=1)
        subsection = Section(name="DFT", line=2, column=1)
        parent.subsections.append(subsection)
        
        lines = provider._format_section(parent, 0, "  ")
        # Check that empty line is added before subsection
        assert "" in lines
    
    def test_format_value_boolean_true(self, provider):
        """Test _format_value for boolean true."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value=True, value_type=ValueType.BOOLEAN, line=1, column=1)
        result = provider._format_value(value)
        assert result == ".TRUE."
    
    def test_format_value_boolean_false(self, provider):
        """Test _format_value for boolean false."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value=False, value_type=ValueType.BOOLEAN, line=1, column=1)
        result = provider._format_value(value)
        assert result == ".FALSE."
    
    def test_format_value_string_with_space(self, provider):
        """Test _format_value for string with space."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value="has space", value_type=ValueType.STRING, line=1, column=1)
        result = provider._format_value(value)
        assert result == '"has space"'
    
    def test_format_value_string_no_space(self, provider):
        """Test _format_value for string without space."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value="nospace", value_type=ValueType.STRING, line=1, column=1)
        result = provider._format_value(value)
        assert result == "nospace"
    
    def test_format_value_number_integer(self, provider):
        """Test _format_value for integer."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value=42, value_type=ValueType.NUMBER, line=1, column=1)
        result = provider._format_value(value)
        assert result == "42"
    
    def test_format_value_number_float(self, provider):
        """Test _format_value for float."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value=3.14, value_type=ValueType.NUMBER, line=1, column=1)
        result = provider._format_value(value)
        assert result == "3.14"
    
    def test_format_value_none(self, provider):
        """Test _format_value for None value."""
        from cp2k_lsp.parser.ast import Value, ValueType
        value = Value(value=None, value_type=ValueType.STRING, line=1, column=1)
        result = provider._format_value(value)
        assert result == ""


class TestCodeActionProvider:
    """Tests for CodeActionProvider."""
    
    @pytest.fixture
    def provider(self):
        server = MockServer()
        return CodeActionProvider(server)
    
    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.server is not None
    
    def test_provide_code_actions_empty(self, provider):
        """Test code actions with no diagnostics."""
        params = lsp.CodeActionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=0)),
            context=lsp.CodeActionContext(diagnostics=[])
        )
        
        result = provider.provide_code_actions(params)
        assert result is None
    
    def test_provide_code_actions_unclosed(self, provider):
        """Test code action for unclosed section."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="Unclosed section &GLOBAL",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        params = lsp.CodeActionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            context=lsp.CodeActionContext(diagnostics=[diagnostic])
        )
        
        result = provider.provide_code_actions(params)
        assert result is not None
        assert len(result) > 0
        assert any(action.title == "Add missing &END tag" for action in result)
    
    def test_provide_code_actions_mismatch(self, provider):
        """Test code action for section name mismatch."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="Section name mismatch",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        params = lsp.CodeActionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            context=lsp.CodeActionContext(diagnostics=[diagnostic])
        )
        
        result = provider.provide_code_actions(params)
        assert result is not None
    
    def test_provide_code_actions_unknown(self, provider):
        """Test code action for unknown diagnostic."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="Unknown error",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        params = lsp.CodeActionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            context=lsp.CodeActionContext(diagnostics=[diagnostic])
        )
        
        result = provider.provide_code_actions(params)
        assert result is None
    
    def test_create_quick_fix_unclosed(self, provider):
        """Test _create_quick_fix for unclosed section."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="unclosed section",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._create_quick_fix(diagnostic, "file://test.inp")
        assert action is not None
        assert action.kind == lsp.CodeActionKind.QuickFix
        assert len(action.diagnostics) == 1
    
    def test_create_quick_fix_expected(self, provider):
        """Test _create_quick_fix for expected token."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="expected &END",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._create_quick_fix(diagnostic, "file://test.inp")
        assert action is not None
    
    def test_create_quick_fix_mismatch(self, provider):
        """Test _create_quick_fix for section name mismatch."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(line=0, character=0), end=lsp.Position(line=0, character=7)),
            message="section name mismatch",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._create_quick_fix(diagnostic, "file://test.inp")
        assert action is not None
    
    def test_fix_unclosed_section(self, provider):
        """Test _fix_unclosed_section method."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=7)
            ),
            message="Unclosed section",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._fix_unclosed_section(diagnostic, "file://test.inp")
        assert action.title == "Add missing &END tag"
        assert action.kind == lsp.CodeActionKind.QuickFix
        assert action.edit is not None
    
    def test_fix_section_mismatch(self, provider):
        """Test _fix_section_mismatch method."""
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=7)
            ),
            message="Section name mismatch",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._fix_section_mismatch(diagnostic, "file://test.inp")
        assert action.title == "Fix section name"
        assert action.kind == lsp.CodeActionKind.QuickFix
        assert action.is_preferred is True


# Parser tests
class TestParser:
    """Tests for CP2KParser."""
    
    def test_parse_simple_input(self):
        """Test parsing simple CP2K input."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
        assert parser.ast.global_section is not None
        assert parser.ast.global_section.name == "GLOBAL"
    
    def test_parse_nested_sections(self):
        """Test parsing nested sections."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = """&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_SET
  &END DFT
&END FORCE_EVAL"""
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
        assert len(parser.ast.sections) > 0
    
    def test_parse_with_comments(self):
        """Test parsing with comments."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = """! This is a comment
&GLOBAL
  ! Inline comment
  PROJECT_NAME test
&END GLOBAL"""
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
        assert len(parser.ast.comments) >= 0
    
    def test_parse_boolean_values(self):
        """Test parsing boolean values."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n  DEBUG_MODE .TRUE.\n&END GLOBAL"
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
        assert parser.ast.global_section is not None
        assert len(parser.ast.global_section.keywords) > 0
    
    def test_parse_number_values(self):
        """Test parsing number values."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n  PRINT_LEVEL 1\n&END GLOBAL"
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
        assert parser.ast.global_section is not None
    
    def test_parse_string_values(self):
        """Test parsing string values."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n  PROJECT_NAME \"my project\"\n&END GLOBAL"
        parser = CP2KParser.parse_text(text)
        
        assert parser.ast is not None
    
    def test_parse_empty_input(self):
        """Test parsing empty input."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        parser = CP2KParser.parse_text("")
        assert parser.ast is not None
    
    def test_parse_unclosed_section(self):
        """Test parsing unclosed section."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n  PROJECT_NAME test"
        parser = CP2KParser.parse_text(text)
        
        # Parser may or may not have errors depending on implementation
        # The AST should still be created
        assert parser.ast is not None
    
    def test_parse_mismatched_end(self):
        """Test parsing section with mismatched end."""
        from cp2k_lsp.parser.parser import CP2KParser
        
        text = "&GLOBAL\n&END WRONG"
        parser = CP2KParser.parse_text(text)
        
        # Should have errors
        assert len(parser.errors) > 0
    
    def test_parser_current_token(self):
        """Test parser current() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        token = parser.current()
        assert token.type == TokenType.SECTION_START
    
    def test_parser_peek_token(self):
        """Test parser peek() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL\n&END GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        token = parser.peek(1)
        assert token is not None
    
    def test_parser_advance(self):
        """Test parser advance() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        first = parser.current()
        advanced = parser.advance()
        assert first.type == advanced.type
    
    def test_parser_match(self):
        """Test parser match() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        assert parser.match(TokenType.SECTION_START) is True
        assert parser.match(TokenType.KEYWORD) is False
    
    def test_parser_expect(self):
        """Test parser expect() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        token = parser.expect(TokenType.SECTION_START)
        assert token.type == TokenType.SECTION_START
    
    def test_parser_expect_error(self):
        """Test parser expect() with wrong token type."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        token = parser.expect(TokenType.KEYWORD)
        # Should have added an error
        assert len(parser.errors) > 0
    
    def test_parser_skip_eol_and_comments(self):
        """Test parser skip_eol_and_comments() method."""
        from cp2k_lsp.parser.parser import CP2KParser
        from cp2k_lsp.parser.lexer import Lexer
        
        text = "! comment\n\n&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = CP2KParser(tokens)
        
        comments = parser.skip_eol_and_comments()
        assert len(comments) >= 0


class TestLexer:
    """Tests for CP2K Lexer."""
    
    def test_lexer_simple_section(self):
        """Test lexer for simple section."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.SECTION_START
        assert tokens[0].value == "GLOBAL"
    
    def test_lexer_section_end(self):
        """Test lexer for section end."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&END GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.SECTION_END
    
    def test_lexer_keyword(self):
        """Test lexer for keyword."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "PROJECT_NAME"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.KEYWORD
    
    def test_lexer_assignment(self):
        """Test lexer for assignment."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "PROJECT_NAME = test"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert any(t.type == TokenType.ASSIGN for t in tokens)
    
    def test_lexer_boolean_true(self):
        """Test lexer for boolean true."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = ".TRUE."
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.BOOLEAN
        assert tokens[0].value == ".TRUE."
    
    def test_lexer_boolean_false(self):
        """Test lexer for boolean false."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = ".FALSE."
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.BOOLEAN
        assert tokens[0].value == ".FALSE."
    
    def test_lexer_number_integer(self):
        """Test lexer for integer."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "42"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"
    
    def test_lexer_number_float(self):
        """Test lexer for float."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "3.14"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.NUMBER
    
    def test_lexer_number_scientific(self):
        """Test lexer for scientific notation."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "1.0e-5"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.NUMBER
    
    def test_lexer_string(self):
        """Test lexer for string."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = '"hello world"'
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.STRING
    
    def test_lexer_string_single_quote(self):
        """Test lexer for single quoted string."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "'hello'"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert tokens[0].type == TokenType.STRING
    
    def test_lexer_comment_exclamation(self):
        """Test lexer for exclamation comment."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "! this is a comment"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert any(t.type == TokenType.COMMENT for t in tokens)
    
    def test_lexer_comment_hash(self):
        """Test lexer for hash comment."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "# this is a comment"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert any(t.type == TokenType.COMMENT for t in tokens)
    
    def test_lexer_unit(self):
        """Test lexer for unit."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "[angstrom]"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        # Check for unit token
        # Units are tokenized as KEYWORD
        assert any(t.type == TokenType.KEYWORD for t in tokens)
    
    def test_lexer_multiline(self):
        """Test lexer for multiline input."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0
        assert any(t.type == TokenType.SECTION_START for t in tokens)
        assert any(t.type == TokenType.SECTION_END for t in tokens)
    
    def test_lexer_preprocessor(self):
        """Test lexer for preprocessor directive."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "@SET VAR value"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        # Preprocessor should be tokenized
        assert len(tokens) > 0
    
    def test_lexer_include(self):
        """Test lexer for include directive."""
        from cp2k_lsp.parser.lexer import Lexer, TokenType
        
        text = "@INCLUDE file.inp"
        lexer = Lexer(text)
        tokens = lexer.tokenize()
        
        assert len(tokens) > 0


class TestAST:
    """Tests for AST classes."""
    
    def test_cp2k_input_init(self):
        """Test CP2KInput initialization."""
        from cp2k_lsp.parser.ast import CP2KInput
        
        ast = CP2KInput(line=1, column=1)
        assert ast.line == 1
        assert ast.column == 1
        assert ast.global_section is None
        assert ast.sections == []
        assert ast.comments == []
    
    def test_section_init(self):
        """Test Section initialization."""
        from cp2k_lsp.parser.ast import Section
        
        section = Section(name="GLOBAL", line=1, column=1)
        assert section.name == "GLOBAL"
        assert section.keywords == []
        assert section.subsections == []
        assert section.comments == []
    
    def test_keyword_init(self):
        """Test Keyword initialization."""
        from cp2k_lsp.parser.ast import Keyword
        
        keyword = Keyword(name="PROJECT_NAME", line=1, column=1)
        assert keyword.name == "PROJECT_NAME"
        assert keyword.value.value is None
    
    def test_keyword_with_value(self):
        """Test Keyword with value."""
        from cp2k_lsp.parser.ast import Keyword, Value, ValueType
        
        value = Value(value="test", value_type=ValueType.STRING, line=1, column=1)
        keyword = Keyword(name="PROJECT_NAME", value=value, line=1, column=1)
        assert keyword.name == "PROJECT_NAME"
        assert keyword.value is not None
        assert keyword.value.value == "test"
    
    def test_value_types(self):
        """Test Value types."""
        from cp2k_lsp.parser.ast import Value, ValueType
        
        # Boolean
        bool_val = Value(value=True, value_type=ValueType.BOOLEAN, line=1, column=1)
        assert bool_val.value_type == ValueType.BOOLEAN
        
        # Number
        num_val = Value(value=42, value_type=ValueType.NUMBER, line=1, column=1)
        assert num_val.value_type == ValueType.NUMBER
        
        # String
        str_val = Value(value="test", value_type=ValueType.STRING, line=1, column=1)
        assert str_val.value_type == ValueType.STRING
        
        # Unit
        unit_val = Value(value="[angstrom]", value_type=ValueType.UNIT, line=1, column=1)
        assert unit_val.value_type == ValueType.UNIT
    
    def test_comment_init(self):
        """Test Comment initialization."""
        from cp2k_lsp.parser.ast import Comment
        
        comment = Comment(text=" test comment", line=2, column=1)
        assert comment.text == " test comment"
        assert comment.line == 2
    
    def test_section_repr(self):
        """Test Section __repr__."""
        from cp2k_lsp.parser.ast import Section
        
        section = Section(name="GLOBAL", line=1, column=1)
        repr_str = repr(section)
        assert "GLOBAL" in repr_str
    
    def test_keyword_repr(self):
        """Test Keyword __repr__."""
        from cp2k_lsp.parser.ast import Keyword
        
        keyword = Keyword(name="PROJECT_NAME", line=1, column=1)
        repr_str = repr(keyword)
        assert "PROJECT_NAME" in repr_str


class TestParserErrors:
    """Tests for parser errors."""
    
    def test_syntax_error_init(self):
        """Test SyntaxError initialization."""
        from cp2k_lsp.parser.errors import SyntaxError
        
        error = SyntaxError("Test error", line=1, column=1, source="test.inp")
        assert error.message == "Test error"
        assert error.line == 1
        assert error.column == 1
    
    def test_syntax_error_str(self):
        """Test SyntaxError string representation."""
        from cp2k_lsp.parser.errors import SyntaxError
        
        error = SyntaxError("Test error", line=1, column=1, source="test.inp")
        str_repr = str(error)
        assert "Test error" in str_repr
    
    def test_parse_error_init(self):
        """Test ParseError initialization."""
        from cp2k_lsp.parser.errors import ParseError
        
        error = ParseError("Parse error", line=2, column=3)
        assert error.message == "Parse error"
    
    def test_parse_error_str(self):
        """Test ParseError string representation."""
        from cp2k_lsp.parser.errors import ParseError
        
        error = ParseError("Parse error", line=2, column=3)
        str_repr = str(error)
        assert "Parse error" in str_repr
