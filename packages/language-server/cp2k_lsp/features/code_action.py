"""Code Action Provider (Quick Fix)."""

from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.code_actions import get_code_actions


class CodeActionProvider:
    """Provides code actions (Quick Fixes) for CP2K input."""

    def __init__(self, server):
        self.server = server

    def provide_code_actions(self, params: lsp.CodeActionParams) -> Optional[List[lsp.CodeAction]]:
        """Provide code actions for diagnostics."""
        uri = params.text_document.uri
        document = self.server.workspace.get_text_document(uri)
        text = document.source

        actions: list[lsp.CodeAction] = []
        for diagnostic in params.context.diagnostics or []:
            diagnostic_code = str(diagnostic.code) if diagnostic.code is not None else None
            diagnostic_data = diagnostic.data if isinstance(diagnostic.data, dict) else None
            actions.extend(
                get_code_actions(
                    text=text,
                    diagnostic_range=diagnostic.range,
                    diagnostic_message=diagnostic.message,
                    uri=uri,
                    diagnostic_code=diagnostic_code,
                    diagnostic_data=diagnostic_data,
                )
            )

        return actions or None

    def _create_quick_fix(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Backward-compatible quick-fix helper used by older tests."""
        diagnostic_data = diagnostic.data if isinstance(diagnostic.data, dict) else {}
        suggested_fix = str(diagnostic_data.get("suggested_fix", ""))
        replacement = ""
        if " with " in suggested_fix:
            replacement = suggested_fix.rsplit(" with ", 1)[-1].rstrip(".")
        elif suggested_fix:
            replacement = suggested_fix.rstrip(".").split()[-1]
        if not replacement:
            return None
        return lsp.CodeAction(
            title=f"Replace with {replacement}",
            kind=lsp.CodeActionKind.QuickFix,
            is_preferred=True,
            edit=lsp.WorkspaceEdit(changes={uri: [lsp.TextEdit(range=diagnostic.range, new_text=replacement)]}),
        )

    def _fix_unclosed_section(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Backward-compatible helper for inserting a missing &END."""
        section_name = "SECTION"
        marker = "&"
        if marker in diagnostic.message:
            section_name = diagnostic.message.split(marker, 1)[1].split()[0]
        return lsp.CodeAction(
            title=f"Add missing &END {section_name}",
            kind=lsp.CodeActionKind.QuickFix,
            is_preferred=True,
            edit=lsp.WorkspaceEdit(
                changes={
                    uri: [
                        lsp.TextEdit(
                            range=lsp.Range(start=diagnostic.range.end, end=diagnostic.range.end),
                            new_text=f"\n&END {section_name}",
                        )
                    ]
                }
            ),
        )

    def _fix_section_mismatch(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Backward-compatible helper for section mismatch diagnostics."""
        return lsp.CodeAction(
            title="Fix section name mismatch",
            kind=lsp.CodeActionKind.QuickFix,
            is_preferred=True,
            edit=lsp.WorkspaceEdit(changes={uri: [lsp.TextEdit(range=diagnostic.range, new_text="&END")]}),
        )
