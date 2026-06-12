"""Completion Provider - Schema-backed implementation.

Replaces hard-coded CP2K completions with schema-backed section and keyword
completion using the CP2K schema index and cursor context resolution.

Features:
- Section completion driven by current section path
- Keyword completion driven by current section path
- Enum/typed value completion for keywords with enum values
- Logical value completion for boolean/flag keywords
- Graceful fallback for unknown sections or keywords

TDD: Implementation written to pass tests in tests/test_completion.py
"""

from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.cursor_context import CursorContext, CursorContextResolver
from cp2k_input_tools.schema_index import CP2KSchemaIndex, get_schema_index


class CompletionProvider:
    """Provides completion items for CP2K input.

    Uses the CP2K schema index and cursor context resolution to provide
    context-aware completions. Falls back gracefully when schema lookup fails.
    """

    def __init__(self, server):
        self.server = server
        self._schema_index: Optional[CP2KSchemaIndex] = None
        self._cursor_resolver = CursorContextResolver()

    @property
    def schema_index(self) -> Optional[CP2KSchemaIndex]:
        """Get the schema index, loading it lazily on first access."""
        if self._schema_index is None:
            try:
                self._schema_index = get_schema_index()
            except Exception:
                # Schema loading failed, fall back to no completions
                return None
        return self._schema_index

    def provide_completion(self, params: lsp.CompletionParams) -> Optional[lsp.CompletionList]:
        """Provide completion items.

        Args:
            params: LSP completion parameters

        Returns:
            CompletionList with appropriate items, or None if no completions
        """
        uri = params.text_document.uri
        position = params.position

        document = self.server.workspace.get_text_document(uri)
        lines = document.lines

        if position.line >= len(lines):
            return None

        # Resolve cursor context
        ctx = self._cursor_resolver.resolve_cursor_context(
            uri=uri,
            lines=lines,
            line=position.line,
            character=position.character,
        )

        # Get schema index
        schema = self.schema_index

        items: List[lsp.CompletionItem] = []

        if ctx.is_section_start:
            # Section completion
            items = self._complete_sections(schema, ctx, position)
        elif ctx.current_section and not ctx.is_section_end:
            if ctx.is_value_position:
                # Value completion (enums, logical values)
                items = self._complete_values(schema, ctx)
            elif ctx.is_keyword_position:
                # Keyword completion
                items = self._complete_keywords(schema, ctx)
            else:
                # Default to keyword completion for empty lines in sections
                items = self._complete_keywords(schema, ctx)

        if not items:
            return None

        return lsp.CompletionList(is_incomplete=False, items=items)

    def _complete_sections(
        self,
        schema: Optional[CP2KSchemaIndex],
        ctx: CursorContext,
        position: lsp.Position,
    ) -> List[lsp.CompletionItem]:
        """Get section completions for the current context.

        Returns child sections of the current section path, or root sections
        if at top level.

        Args:
            schema: The schema index (may be None if loading failed)
            ctx: Cursor context
            position: LSP position

        Returns:
            List of completion items
        """
        if schema is None:
            # Fallback to empty list if schema unavailable
            return []

        # Get prefix from section name after &
        prefix = ctx.prefix.upper()

        # Get available sections
        if ctx.section_path:
            # Get child sections of current section
            section_spec = schema.get_section(ctx.section_path)
            if section_spec:
                child_sections = schema.get_child_sections(ctx.section_path)
            else:
                # Current section not found in schema, return empty
                child_sections = []
        else:
            # Get root sections
            child_sections = schema.get_root_sections()

        # Filter and create completion items
        items: List[lsp.CompletionItem] = []
        for section_name in child_sections:
            if not prefix or section_name.upper().startswith(prefix):
                # Get section description for detail
                section_path = ctx.section_path + (section_name,) if ctx.section_path else (section_name,)
                section_detail = schema.get_section(section_path)
                detail = section_detail.description if section_detail else ""

                # Build snippet for section completion
                # If client supports snippets, provide &SECTION\n  $0\n&END SECTION
                snippet = f"{section_name}\n  $0\n&END {section_name}"

                item = lsp.CompletionItem(
                    label=section_name,
                    kind=lsp.CompletionItemKind.Module,
                    detail=detail,
                    documentation=detail if detail else None,
                    insert_text=snippet,
                    insert_text_format=lsp.InsertTextFormat.Snippet,
                )
                items.append(item)

        return items

    def _complete_keywords(
        self,
        schema: Optional[CP2KSchemaIndex],
        ctx: CursorContext,
    ) -> List[lsp.CompletionItem]:
        """Get keyword completions for the current section.

        Args:
            schema: The schema index (may be None if loading failed)
            ctx: Cursor context

        Returns:
            List of completion items
        """
        if schema is None or not ctx.current_section:
            return []

        prefix = ctx.prefix.upper()

        section_path = ctx.section_path if ctx.section_path else (ctx.current_section,)
        keywords = schema.get_keywords(section_path)

        items: List[lsp.CompletionItem] = []
        for keyword_name, keyword_spec in keywords.items():
            if not prefix or keyword_name.upper().startswith(prefix):
                # Build detail text with type and default
                detail_parts: List[str] = []
                if keyword_spec.variable_type:
                    detail_parts.append(keyword_spec.variable_type)
                if keyword_spec.default_value:
                    detail_parts.append(f"default: {keyword_spec.default_value}")
                detail = " | ".join(detail_parts) if detail_parts else keyword_spec.description or ""

                # Build documentation string
                doc_parts: List[str] = []
                if keyword_spec.description:
                    doc_parts.append(f"**{keyword_name}** - {keyword_spec.description}")
                if keyword_spec.enumeration_values:
                    doc_parts.append("\n**Enum values:**")
                    for val in keyword_spec.enumeration_values[:10]:  # Limit to 10 values
                        doc_parts.append(f"  - `{val}`")
                    if len(keyword_spec.enumeration_values) > 10:
                        doc_parts.append(f"  - ... and {len(keyword_spec.enumeration_values) - 10} more")
                documentation = "\n".join(doc_parts) if doc_parts else None

                item = lsp.CompletionItem(
                    label=keyword_name,
                    kind=lsp.CompletionItemKind.Field,
                    detail=detail,
                    documentation=documentation,
                    insert_text=keyword_name,
                )
                items.append(item)

        return items

    def _complete_values(
        self,
        schema: Optional[CP2KSchemaIndex],
        ctx: CursorContext,
    ) -> List[lsp.CompletionItem]:
        """Get value completions for the current keyword.

        Args:
            schema: The schema index (may be None if loading failed)
            ctx: Cursor context

        Returns:
            List of completion items
        """
        if schema is None or not ctx.current_keyword or not ctx.current_section:
            return []

        section_path = ctx.section_path if ctx.section_path else (ctx.current_section,)
        keyword_spec = schema.get_keyword(section_path, ctx.current_keyword)

        if not keyword_spec:
            return []

        items: List[lsp.CompletionItem] = []
        prefix = ctx.prefix.upper()

        # Enum completion
        if keyword_spec.enumeration_values:
            for value in keyword_spec.enumeration_values:
                if not prefix or value.upper().startswith(prefix):
                    item = lsp.CompletionItem(
                        label=value,
                        kind=lsp.CompletionItemKind.EnumMember,
                        detail=f"Enum value for {ctx.current_keyword}",
                    )
                    items.append(item)

        # Logical value completion (for boolean/flag keywords)
        elif keyword_spec.variable_type and "logical" in keyword_spec.variable_type.lower():
            logical_values = ["F", ".FALSE.", "T", ".TRUE."]
            for value in logical_values:
                if not prefix or value.upper().startswith(prefix):
                    item = lsp.CompletionItem(
                        label=value,
                        kind=lsp.CompletionItemKind.Value,
                        detail="Logical value",
                    )
                    items.append(item)

        return items
