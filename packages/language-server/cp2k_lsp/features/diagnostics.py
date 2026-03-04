"""Diagnostics Provider."""

from typing import List

from lsprotocol import types as lsp


class DiagnosticsProvider:
    """Provides diagnostics for CP2K input files."""

    # Common CP2K sections that should be checked
    REQUIRED_SECTIONS = ["GLOBAL", "FORCE_EVAL"]

    def __init__(self, server):
        self.server = server

    def get_diagnostics(self, uri: str) -> List[lsp.Diagnostic]:
        """Get diagnostics for a document."""
        diagnostics = []

        # Get parser errors
        errors = self.server.get_errors(uri)
        for error in errors:
            diagnostic = lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=error.line - 1, character=error.column - 1),
                    end=lsp.Position(line=error.line - 1, character=error.column + 10),
                ),
                message=str(error),
                severity=lsp.DiagnosticSeverity.Error,
                source="cp2k-lsp",
            )
            diagnostics.append(diagnostic)

        # Get AST validation diagnostics
        ast = self.server.get_ast(uri)
        if ast:
            diagnostics.extend(self._validate_ast(ast))

        return diagnostics

    def _validate_ast(self, ast) -> List[lsp.Diagnostic]:
        """Validate AST and return diagnostics."""
        diagnostics = []

        # Check for required sections
        diagnostics.extend(self._check_required_sections(ast))

        # Check for duplicate sections
        diagnostics.extend(self._check_duplicate_sections(ast))

        # Check for empty sections
        diagnostics.extend(self._check_empty_sections(ast))

        return diagnostics

    def _check_required_sections(self, ast) -> List[lsp.Diagnostic]:
        """Check for required CP2K sections."""
        diagnostics = []
        section_names = [s.name.upper() for s in ast.sections]
        if ast.global_section:
            section_names.append("GLOBAL")

        for required in self.REQUIRED_SECTIONS:
            if required not in section_names:
                diagnostics.append(
                    lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=0, character=0),
                            end=lsp.Position(line=0, character=0),
                        ),
                        message=f"Missing required section: &{required}",
                        severity=lsp.DiagnosticSeverity.Warning,
                        source="cp2k-lsp",
                        code="missing-required-section",
                    )
                )

        return diagnostics

    def _check_duplicate_sections(self, ast) -> List[lsp.Diagnostic]:
        """Check for duplicate section names (where not allowed)."""
        diagnostics = []
        seen = set()

        for section in ast.sections:
            name = section.name.upper()
            # GLOBAL should only appear once
            if name == "GLOBAL" and name in seen:
                diagnostics.append(
                    lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=section.line - 1, character=0),
                            end=lsp.Position(line=section.line - 1, character=len(section.name) + 1),
                        ),
                        message=f"Duplicate section: &{section.name}. Only one GLOBAL section allowed.",
                        severity=lsp.DiagnosticSeverity.Warning,
                        source="cp2k-lsp",
                        code="duplicate-section",
                    )
                )
            seen.add(name)

        return diagnostics

    def _check_empty_sections(self, ast) -> List[lsp.Diagnostic]:
        """Check for empty sections."""
        diagnostics = []

        for section in ast.sections:
            if not section.keywords and not section.subsections:
                diagnostics.append(
                    lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=section.line - 1, character=0),
                            end=lsp.Position(line=section.line - 1, character=len(section.name) + 1),
                        ),
                        message=f"Empty section: &{section.name}",
                        severity=lsp.DiagnosticSeverity.Information,
                        source="cp2k-lsp",
                        code="empty-section",
                    )
                )

        return diagnostics
