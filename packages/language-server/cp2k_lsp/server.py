"""CP2K Language Server."""

import logging
from typing import Dict, List, Optional

from lsprotocol import types as lsp
from pygls.server import LanguageServer

from cp2k_input_tools.cache_invalidation import CacheInvalidator
from cp2k_input_tools.workspace_index import WorkspaceResourceIndex
from cp2k_lsp.agent_commands import AGENT_COMMANDS, execute_command
from cp2k_lsp.features.code_action import CodeActionProvider
from cp2k_lsp.features.completion import CompletionProvider
from cp2k_lsp.features.definition import (
    provide_definition,
    provide_references,
)
from cp2k_lsp.features.diagnostics import DiagnosticsProvider
from cp2k_lsp.features.formatting import FormattingProvider
from cp2k_lsp.features.hover import HoverProvider
from cp2k_lsp.features.resource_completion import provide_resource_completions
from cp2k_lsp.features.resource_diagnostics import provide_resource_diagnostics
from cp2k_lsp.features.semantic_tokens import SemanticTokenProvider
from cp2k_lsp.features.symbols import (
    provide_document_symbols,
    provide_folding_ranges,
)
from cp2k_lsp.parser import CP2KInput, CP2KParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cp2k-lsp")


class CP2KLanguageServer(LanguageServer):
    """CP2K Language Server Protocol implementation."""

    CONFIGURATION_SECTION = "cp2k"

    def __init__(self, *args, **kwargs):
        super().__init__("cp2k-lsp", "0.1.0", *args, **kwargs)
        self.parsed_documents: Dict[str, Optional[CP2KInput]] = {}
        self.parser_errors: Dict[str, List] = {}
        self.document_lines: Dict[str, List[str]] = {}
        self.release_version: Optional[str] = None

        # Workspace resource index + cache invalidator (#123)
        self.workspace_index = WorkspaceResourceIndex()
        self.cache_invalidator = CacheInvalidator(self.workspace_index)

        # Feature providers
        self.diagnostics = DiagnosticsProvider(self)
        self.completion = CompletionProvider(self)
        self.hover = HoverProvider(self)
        self.formatting = FormattingProvider(self)
        self.code_action = CodeActionProvider(self)
        self.semantic_tokens = SemanticTokenProvider()

        self._setup_handlers()
        self._register_agent_commands()

    def _register_agent_commands(self) -> None:
        """Register agent-facing workspace/executeCommand handlers."""

        for command in AGENT_COMMANDS:

            @self.command(command)
            def cmd_agent(ls, arguments, _command=command):
                return execute_command(_command, ls, arguments)

    def _setup_handlers(self) -> None:
        """Setup LSP handlers."""

        @self.feature(lsp.INITIALIZE)
        def initialize(params: lsp.InitializeParams) -> None:
            """Capture release_version from initializationOptions."""
            if params.initialization_options:
                self.release_version = params.initialization_options.get("release_version")

        @self.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
        async def did_open(params: lsp.DidOpenTextDocumentParams):
            self._parse_document(params.text_document.uri)
            await self._publish_diagnostics(params.text_document.uri)

        @self.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
        async def did_change(params: lsp.DidChangeTextDocumentParams):
            self._parse_document(params.text_document.uri)
            await self._publish_diagnostics(params.text_document.uri)

        @self.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
        async def did_close(params: lsp.DidCloseTextDocumentParams):
            uri = params.text_document.uri
            if uri in self.parsed_documents:
                del self.parsed_documents[uri]
            if uri in self.parser_errors:
                del self.parser_errors[uri]
            if uri in self.document_lines:
                del self.document_lines[uri]
            self.workspace_index.clear_document(uri)

        @self.feature(lsp.TEXT_DOCUMENT_COMPLETION)
        def completion(params: lsp.CompletionParams) -> Optional[lsp.CompletionList]:
            base = self.completion.provide_completion(params)
            ast = self.get_ast(params.text_document.uri)
            extras = (
                provide_resource_completions(
                    ast,
                    params.position,
                    params.text_document.uri,
                    self.workspace_index,
                    self.get_lines(params.text_document.uri),
                )
                if ast is not None
                else None
            )
            if extras is None:
                return base
            if base is None:
                return extras
            # Merge items from both lists
            return lsp.CompletionList(
                items=list(base.items) + list(extras.items),
                is_incomplete=base.is_incomplete or extras.is_incomplete,
            )

        @self.feature(lsp.TEXT_DOCUMENT_HOVER)
        def hover_provider(params: lsp.HoverParams) -> Optional[lsp.Hover]:
            return self.hover.provide_hover(params)

        @self.feature(lsp.TEXT_DOCUMENT_FORMATTING)
        def formatting_provider(params: lsp.DocumentFormattingParams) -> Optional[List[lsp.TextEdit]]:
            return self.formatting.provide_formatting(params)

        @self.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
        def code_action_provider(params: lsp.CodeActionParams) -> Optional[List[lsp.CodeAction]]:
            return self.code_action.provide_code_actions(params)

        @self.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
        def document_symbol(
            params: lsp.DocumentSymbolParams
        ) -> Optional[List[lsp.DocumentSymbol]]:
            ast = self.get_ast(params.text_document.uri)
            if ast is None:
                return []
            return provide_document_symbols(ast, self.get_lines(params.text_document.uri))

        @self.feature(lsp.TEXT_DOCUMENT_FOLDING_RANGE)
        def folding_range(
            params: lsp.FoldingRangeParams
        ) -> Optional[List[lsp.FoldingRange]]:
            ast = self.get_ast(params.text_document.uri)
            if ast is None:
                return []
            return provide_folding_ranges(ast)

        @self.feature(lsp.TEXT_DOCUMENT_DEFINITION)
        def definition(
            params: lsp.DefinitionParams
        ) -> Optional[lsp.Location]:
            ast = self.get_ast(params.text_document.uri)
            if ast is None:
                return None
            return provide_definition(
                ast,
                params.position,
                params.text_document.uri,
                self.workspace_index,
                self.get_lines(params.text_document.uri),
            )

        @self.feature(lsp.TEXT_DOCUMENT_REFERENCES)
        def references(
            params: lsp.ReferenceParams
        ) -> Optional[List[lsp.Location]]:
            ast = self.get_ast(params.text_document.uri)
            if ast is None:
                return []
            return provide_references(
                ast,
                params.position,
                params.text_document.uri,
                self.workspace_index,
                params.context.include_declaration if params.context else True,
                self.get_lines(params.text_document.uri),
            )

        @self.feature(lsp.WORKSPACE_DID_CHANGE_WATCHED_FILES)
        def watched_files(params: lsp.DidChangeWatchedFilesParams):
            for change in params.changes:
                uri = change.uri
                path = uri[7:] if uri.startswith("file://") else uri
                if change.type == lsp.FileChangeType.Created:
                    self.cache_invalidator.on_file_created(path)
                elif change.type == lsp.FileChangeType.Changed:
                    self.cache_invalidator.on_file_changed(path)
                else:
                    # FileChangeType.Deleted (1) or any other enum value
                    self.cache_invalidator.on_file_deleted(path)

        @self.feature(lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL)
        def semantic_tokens_full(params: lsp.SemanticTokensParams) -> Optional[lsp.SemanticTokens]:
            return self._provide_semantic_tokens(params)

        @self.feature(lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_RANGE)
        def semantic_tokens_range(params: lsp.SemanticTokensRangeParams) -> Optional[lsp.SemanticTokens]:
            return self._provide_semantic_tokens(params)

    def _parse_document(self, uri: str) -> None:
        """Parse a document and store the AST."""
        try:
            document = self.workspace.get_text_document(uri)
            source = document.source
            self.document_lines[uri] = source.split("\n")
            parser = CP2KParser.parse_text(source, uri)
            self.parsed_documents[uri] = parser.ast
            self.parser_errors[uri] = parser.errors
            # Reindex file references for #123 workspace tracking
            self.workspace_index.parse_cp2k_document(uri, source)
        except Exception as e:
            logger.error(f"Error parsing document {uri}: {e}")
            self.parsed_documents[uri] = None
            self.parser_errors[uri] = []
            self.document_lines[uri] = []

    def _provide_semantic_tokens(
        self, params: lsp.SemanticTokensParams | lsp.SemanticTokensRangeParams
    ) -> Optional[lsp.SemanticTokens]:
        """Provide semantic tokens for a document or range."""
        try:
            document = self.workspace.get_text_document(params.text_document.uri)
            tokens = self.semantic_tokens.get_semantic_tokens(document.source)
            if not tokens:
                return lsp.SemanticTokens(data=[])

            # Build token data array in LSP format:
            # [deltaLine, deltaStartChar, length, tokenType, tokenModifiers]
            token_types = ["section", "keyword", "value", "unit", "comment", "preprocessor", "variable"]
            data = []
            prev_line = 0
            prev_char = 0

            for token in sorted(tokens, key=lambda t: (t.line, t.start_char)):
                delta_line = token.line - prev_line
                if delta_line == 0:
                    delta_char = token.start_char - prev_char
                else:
                    delta_char = token.start_char

                token_type_idx = token_types.index(token.token_type) if token.token_type in token_types else 0
                token_modifiers = 0
                for i, mod in enumerate(["definition", "readonly"]):
                    if mod in token.modifiers:
                        token_modifiers |= (1 << i)

                data.extend([delta_line, delta_char, token.length, token_type_idx, token_modifiers])
                prev_line = token.line
                prev_char = token.start_char

            return lsp.SemanticTokens(data=data)
        except Exception as e:
            logger.error(f"Error providing semantic tokens: {e}")
            return None

    async def _publish_diagnostics(self, uri: str) -> None:
        """Publish diagnostics for a document."""
        diagnostics = self.diagnostics.get_diagnostics(uri)
        # Augment with resource diagnostics (#123) — keep base diagnostics intact
        ast = self.get_ast(uri)
        if ast is not None:
            diagnostics = list(diagnostics) + list(
                provide_resource_diagnostics(
                    ast,
                    uri,
                    self.workspace_index,
                    self.get_lines(uri),
                )
            )
        self.publish_diagnostics(uri, diagnostics)

    def get_ast(self, uri: str) -> Optional[CP2KInput]:
        """Get parsed AST for a document."""
        if uri not in self.parsed_documents:
            self._parse_document(uri)
        return self.parsed_documents.get(uri)

    def get_lines(self, uri: str) -> List[str]:
        """Get source lines for a document (0-indexed)."""
        if uri not in self.document_lines:
            self._parse_document(uri)
        return self.document_lines.get(uri, [])

    def get_errors(self, uri: str) -> List:
        """Get parser errors for a document."""
        if uri not in self.parser_errors:
            self._parse_document(uri)
        return self.parser_errors.get(uri, [])


def main():
    """Main entry point."""
    server = CP2KLanguageServer()
    logger.info("Starting CP2K Language Server...")
    server.start_io()


if __name__ == "__main__":
    main()
