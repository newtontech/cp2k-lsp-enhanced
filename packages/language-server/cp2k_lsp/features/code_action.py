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
