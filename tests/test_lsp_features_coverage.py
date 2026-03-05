"""Focused tests for LSP features."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
    def __init__(self, source, lines=None, uri="file://test.inp"):
        self.source = source
        self.lines = lines or source.split('\n')
        self.uri = uri
        self.path = uri.replace("file://", "")


class MockServer:
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
    def test_init(self):
        server = MockServer()
        provider = CompletionProvider(server)
        assert provider.server == server

    def test_provide_completion_section(self):
        server = MockServer()
        provider = CompletionProvider(server)
        doc = MockDocument("&")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=1)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert len(result.items) > 0
        assert any("GLOBAL" in item.label for item in result.items)

    def test_provide_completion_run_type(self):
        server = MockServer()
        provider = CompletionProvider(server)
        doc = MockDocument("RUN_TYPE = ")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=12)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert any(item.label == "ENERGY" for item in result.items)

    def test_provide_completion_boolean(self):
        server = MockServer()
        provider = CompletionProvider(server)
        doc = MockDocument("SOME_BOOL = ")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=12)
        )
        
        result = provider.provide_completion(params)
        assert result is not None
        assert any(item.label == ".TRUE." for item in result.items)

    def test_provide_completion_out_of_range(self):
        server = MockServer()
        provider = CompletionProvider(server)
        doc = MockDocument("line1")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=10, character=0)
        )
        
        result = provider.provide_completion(params)
        assert result is None

    def test_get_section_completions(self):
        server = MockServer()
        provider = CompletionProvider(server)
        items = provider._get_section_completions()
        assert len(items) > 0
        assert any(item.label == "GLOBAL" for item in items)

    def test_resolve_completion(self):
        server = MockServer()
        provider = CompletionProvider(server)
        item = lsp.CompletionItem(label="TEST")
        result = provider.resolve_completion(item)
        assert result == item


class TestDiagnosticsProvider:
    def test_init(self):
        server = MockServer()
        provider = DiagnosticsProvider(server)
        assert provider.server == server

    def test_get_diagnostics_with_errors(self):
        from cp2k_lsp.parser.errors import ParseError
        
        server = MockServer()
        provider = DiagnosticsProvider(server)
        errors = [ParseError("Test error", 1, 5, "test.inp")]
        server.set_errors(errors)
        
        diagnostics = provider.get_diagnostics("file://test.inp")
        assert len(diagnostics) == 1
        assert "Test error" in diagnostics[0].message

    def test_check_required_sections_missing(self):
        from cp2k_lsp.parser.ast import CP2KInput
        
        server = MockServer()
        provider = DiagnosticsProvider(server)
        ast = CP2KInput()
        
        diagnostics = provider._check_required_sections(ast)
        assert len(diagnostics) == 2

    def test_check_required_sections_present(self):
        from cp2k_lsp.parser.ast import CP2KInput, Section
        
        server = MockServer()
        provider = DiagnosticsProvider(server)
        ast = CP2KInput()
        ast.global_section = Section(name="GLOBAL")
        ast.sections.append(Section(name="FORCE_EVAL"))
        
        diagnostics = provider._check_required_sections(ast)
        assert len(diagnostics) == 0

    def test_check_empty_sections(self):
        from cp2k_lsp.parser.ast import CP2KInput, Section
        
        server = MockServer()
        provider = DiagnosticsProvider(server)
        ast = CP2KInput()
        empty_section = Section(name="TEST", line=1)
        ast.sections.append(empty_section)
        
        diagnostics = provider._check_empty_sections(ast)
        assert len(diagnostics) == 1
        assert "Empty section" in diagnostics[0].message


class TestHoverProvider:
    def test_init(self):
        server = MockServer()
        provider = HoverProvider(server)
        assert provider.server == server

    def test_provide_hover_section(self):
        server = MockServer()
        provider = HoverProvider(server)
        doc = MockDocument("&GLOBAL")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=2)
        )
        
        result = provider.provide_hover(params)
        assert result is not None
        assert "GLOBAL" in result.contents.value

    def test_provide_hover_keyword(self):
        server = MockServer()
        provider = HoverProvider(server)
        doc = MockDocument("PROJECT_NAME test")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=0, character=5)
        )
        
        result = provider.provide_hover(params)
        assert result is not None
        assert "PROJECT_NAME" in result.contents.value

    def test_provide_hover_out_of_range(self):
        server = MockServer()
        provider = HoverProvider(server)
        doc = MockDocument("line1")
        server.workspace.get_text_document.return_value = doc
        
        params = lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            position=lsp.Position(line=10, character=0)
        )
        
        result = provider.provide_hover(params)
        assert result is None

    def test_get_word_at_position(self):
        server = MockServer()
        provider = HoverProvider(server)
        
        word = provider._get_word_at_position("PROJECT_NAME test", 5)
        assert word == "PROJECT_NAME"


class TestFormattingProvider:
    def test_init(self):
        server = MockServer()
        provider = FormattingProvider(server)
        assert provider.server == server

    def test_format_value_boolean(self):
        from cp2k_lsp.parser.ast import Value, ValueType
        
        server = MockServer()
        provider = FormattingProvider(server)
        
        value = Value(value=True, value_type=ValueType.BOOLEAN)
        result = provider._format_value(value)
        assert result == ".TRUE."
        
        value = Value(value=False, value_type=ValueType.BOOLEAN)
        result = provider._format_value(value)
        assert result == ".FALSE."


class TestCodeActionProvider:
    def test_init(self):
        server = MockServer()
        provider = CodeActionProvider(server)
        assert provider.server == server

    def test_provide_code_actions_empty(self):
        server = MockServer()
        provider = CodeActionProvider(server)
        
        params = lsp.CodeActionParams(
            text_document=lsp.TextDocumentIdentifier(uri="file://test.inp"),
            range=lsp.Range(start=lsp.Position(0, 0), end=lsp.Position(0, 10)),
            context=lsp.CodeActionContext(diagnostics=[])
        )
        
        result = provider.provide_code_actions(params)
        # Should return source actions even with no diagnostics
        assert result is not None

    def test_fix_unclosed_section(self):
        server = MockServer()
        provider = CodeActionProvider(server)
        
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(0, 0), end=lsp.Position(0, 10)),
            message="Unclosed section",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._fix_unclosed_section(diagnostic, "file://test.inp")
        assert action is not None
        assert "&END" in action.title

    def test_fix_section_mismatch(self):
        server = MockServer()
        provider = CodeActionProvider(server)
        
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(0, 0), end=lsp.Position(0, 10)),
            message="Section name mismatch: &GLOBAL closed with &END FORCE_EVAL",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._fix_section_mismatch(diagnostic, "file://test.inp")
        assert action is not None
        assert "GLOBAL" in action.title

    def test_fix_unexpected_token(self):
        server = MockServer()
        provider = CodeActionProvider(server)
        
        diagnostic = lsp.Diagnostic(
            range=lsp.Range(start=lsp.Position(0, 0), end=lsp.Position(0, 5)),
            message="Unexpected token",
            severity=lsp.DiagnosticSeverity.Error
        )
        
        action = provider._fix_unexpected_token(diagnostic, "file://test.inp")
        assert action is not None
        assert "Remove" in action.title
