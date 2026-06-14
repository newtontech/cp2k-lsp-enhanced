"""Formatting Provider."""

from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.formatter import format_document


class FormattingProvider:
    """Provides document formatting for CP2K input."""

    def __init__(self, server):
        self.server = server

    def provide_formatting(self, params: lsp.DocumentFormattingParams) -> Optional[List[lsp.TextEdit]]:
        """Format the entire document using the core formatter with minimal TextEdits."""
        uri = params.text_document.uri
        document = self.server.workspace.get_text_document(uri)

        try:
            edits = format_document(document.source, minimal_edits=True)
            if edits:
                return edits
        except Exception:
            pass

        return None
