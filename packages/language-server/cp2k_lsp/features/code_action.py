"""Code Action Provider (Quick Fix)."""

import re
from typing import List, Optional

from lsprotocol import types as lsp


class CodeActionProvider:
    """Provides code actions (Quick Fixes) for CP2K input."""

    def __init__(self, server):
        self.server = server

    def provide_code_actions(self, params: lsp.CodeActionParams) -> Optional[List[lsp.CodeAction]]:
        """Provide code actions for diagnostics."""
        actions = []
        uri = params.text_document.uri

        for diagnostic in params.context.diagnostics:
            action = self._create_quick_fix(diagnostic, uri)
            if action:
                actions.append(action)

        # Add source actions
        source_actions = self._get_source_actions(params)
        actions.extend(source_actions)

        return actions if actions else None

    def _create_quick_fix(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Create a quick fix for a diagnostic."""
        message = diagnostic.message.lower()

        if "unclosed" in message or "expected" in message:
            return self._fix_unclosed_section(diagnostic, uri)
        elif "mismatch" in message:
            return self._fix_section_mismatch(diagnostic, uri)
        elif "unexpected" in message:
            return self._fix_unexpected_token(diagnostic, uri)

        return None

    def _fix_unclosed_section(self, diagnostic: lsp.Diagnostic, uri: str) -> lsp.CodeAction:
        """Fix unclosed section by adding &END."""
        range_ = diagnostic.range

        return lsp.CodeAction(
            title="Add missing &END tag",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=lsp.WorkspaceEdit(
                changes={
                    uri: [
                        lsp.TextEdit(
                            range=lsp.Range(
                                start=lsp.Position(line=range_.end.line + 1, character=0),
                                end=lsp.Position(line=range_.end.line + 1, character=0),
                            ),
                            new_text="\u0026END\n",
                        )
                    ]
                }
            ),
        )

    def _fix_section_mismatch(self, diagnostic: lsp.Diagnostic, uri: str) -> lsp.CodeAction:
        """Fix section name mismatch."""
        # Extract section names from the error message
        message = diagnostic.message
        match = re.search(r"&(\w+)\s+closed\s+with\s+&(\w+)", message, re.IGNORECASE)

        if match:
            expected_name = match.group(1)
            actual_name = match.group(2)

            return lsp.CodeAction(
                title=f"Change &END {actual_name} to &END {expected_name}",
                kind=lsp.CodeActionKind.QuickFix,
                diagnostics=[diagnostic],
                is_preferred=True,
                edit=lsp.WorkspaceEdit(
                    changes={
                        uri: [
                            lsp.TextEdit(
                                range=lsp.Range(
                                    start=lsp.Position(line=diagnostic.range.start.line, character=0),
                                    end=lsp.Position(line=diagnostic.range.end.line, character=0),
                                ),
                                new_text=f"\u0026END {expected_name}\n",
                            )
                        ]
                    }
                ),
            )

        return lsp.CodeAction(
            title="Fix section name",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            is_preferred=True
        )

    def _fix_unexpected_token(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Fix unexpected token by removing it."""
        return lsp.CodeAction(
            title="Remove unexpected token",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            edit=lsp.WorkspaceEdit(
                changes={
                    uri: [
                        lsp.TextEdit(
                            range=diagnostic.range,
                            new_text="",
                        )
                    ]
                }
            ),
        )

    def _get_source_actions(self, params: lsp.CodeActionParams) -> List[lsp.CodeAction]:
        """Get source-level code actions."""
        actions = []
        uri = params.text_document.uri

        # Add "Organize sections" action
        organize_action = lsp.CodeAction(
            title="Organize CP2K sections",
            kind=lsp.CodeActionKind.SourceOrganizeImports,
            edit=lsp.WorkspaceEdit(changes={uri: []}),
        )
        actions.append(organize_action)

        return actions
