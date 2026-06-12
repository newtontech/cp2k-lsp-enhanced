"""Code Action Provider (Quick Fix)."""

import re
from typing import Any, List, Optional

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
        
        return actions if actions else None
    
    def _create_quick_fix(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Create a quick fix for a diagnostic."""
        code = str(diagnostic.code or "")
        if code in {"cp2k.version.removed_keyword", "cp2k.version.deprecated_keyword"}:
            return self._fix_version_policy_replacement(diagnostic, uri)

        message = diagnostic.message.lower()
        
        if "unclosed" in message or "expected" in message:
            return self._fix_unclosed_section(diagnostic, uri)
        elif "mismatch" in message:
            return self._fix_section_mismatch(diagnostic, uri)
        
        return None

    def _fix_version_policy_replacement(self, diagnostic: lsp.Diagnostic, uri: str) -> Optional[lsp.CodeAction]:
        """Replace a removed/deprecated keyword when the version policy names a safe target."""
        replacement = _replacement_from_diagnostic(diagnostic)
        if not replacement:
            return None
        return lsp.CodeAction(
            title=f"Replace with {replacement}",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            is_preferred=True,
            edit=lsp.WorkspaceEdit(
                changes={
                    uri: [
                        lsp.TextEdit(
                            range=diagnostic.range,
                            new_text=replacement,
                        )
                    ]
                }
            ),
        )
    
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
                                end=lsp.Position(line=range_.end.line + 1, character=0)
                            ),
                            new_text="\u0026END\n"
                        )
                    ]
                }
            )
        )
    
    def _fix_section_mismatch(self, diagnostic: lsp.Diagnostic, uri: str) -> lsp.CodeAction:
        """Fix section name mismatch."""
        return lsp.CodeAction(
            title="Fix section name",
            kind=lsp.CodeActionKind.QuickFix,
            diagnostics=[diagnostic],
            is_preferred=True
        )


def _replacement_from_diagnostic(diagnostic: lsp.Diagnostic) -> str | None:
    data = getattr(diagnostic, "data", None)
    hint = ""
    if isinstance(data, dict):
        hint_value: Any = data.get("suggested_fix")
        if isinstance(hint_value, str):
            hint = hint_value
    if not hint:
        hint = diagnostic.message
    match = re.search(r"\bReplace\s+\S+\s+with\s+([A-Za-z][A-Za-z0-9_\-]*)\b", hint, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()
