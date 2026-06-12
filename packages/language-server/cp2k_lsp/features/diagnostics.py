"""Diagnostics Provider."""

import re
from typing import List

from lsprotocol import types as lsp

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")


class DiagnosticsProvider:
    """Provides diagnostics for CP2K input files."""
    
    def __init__(self, server):
        self.server = server
    
    def get_diagnostics(self, uri: str) -> List[lsp.Diagnostic]:
        """Get diagnostics for a document."""
        diagnostics: List[lsp.Diagnostic] = []
        
        # Get parser errors
        errors = self.server.get_errors(uri)
        for error in errors:
            diagnostic = lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=error.line - 1, character=error.column - 1),
                    end=lsp.Position(line=error.line - 1, character=error.column + 10)
                ),
                message=str(error),
                severity=lsp.DiagnosticSeverity.Error,
                source="cp2k-lsp"
            )
            diagnostics.append(diagnostic)
        
        # Get AST validation diagnostics
        ast = self.server.get_ast(uri)
        if ast:
            diagnostics.extend(self._validate_ast(ast))

        diagnostics.extend(self._version_policy_diagnostics(uri))
        
        return diagnostics
    
    def _validate_ast(self, ast) -> List[lsp.Diagnostic]:
        """Validate AST and return diagnostics."""
        diagnostics: List[lsp.Diagnostic] = []
        
        # Check for unclosed sections is done in parser
        # Additional semantic validation can be added here
        
        return diagnostics

    def _version_policy_diagnostics(self, uri: str) -> List[lsp.Diagnostic]:
        """Run optional version-policy diagnostics when configured."""
        try:
            from cp2k_input_tools.version_policy import lint_version_policy_from_env
        except Exception:
            return []

        try:
            document = self.server.workspace.get_text_document(uri)
            text = document.source
        except Exception:
            return []

        lines = text.splitlines()
        diagnostics: List[lsp.Diagnostic] = []
        for item in lint_version_policy_from_env(text):
            line = item.line if item.line is not None else 0
            column = item.column if item.column is not None else 0
            line_text = lines[line] if line < len(lines) else ""
            end_column = _token_end(line_text, column)
            data = {"suggested_fix": item.suggested_fix} if item.suggested_fix else None
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=line, character=column),
                        end=lsp.Position(line=line, character=end_column),
                    ),
                    message=item.message,
                    severity=_severity_to_lsp(item.severity),
                    source=item.source,
                    code=item.code,
                    data=data,
                )
            )
        return diagnostics


def _severity_to_lsp(severity: str) -> lsp.DiagnosticSeverity:
    if severity == "error":
        return lsp.DiagnosticSeverity.Error
    if severity == "warning":
        return lsp.DiagnosticSeverity.Warning
    return lsp.DiagnosticSeverity.Information


def _token_end(line: str, column: int) -> int:
    match = _TOKEN_RE.match(line[column:])
    if match:
        return column + match.end()
    return max(column + 1, len(line))
