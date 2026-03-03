"""Comprehensive unit tests for cp2k_lsp feature providers."""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

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
