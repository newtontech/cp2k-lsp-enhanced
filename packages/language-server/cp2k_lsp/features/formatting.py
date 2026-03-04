"""Formatting Provider."""

from typing import List, Optional

from cp2k_lsp.parser import CP2KInput, CP2KParser, Section
from lsprotocol import types as lsp


class FormattingProvider:
    """Provides document formatting for CP2K input."""

    def __init__(self, server):
        self.server = server

    def provide_formatting(self, params: lsp.DocumentFormattingParams) -> Optional[List[lsp.TextEdit]]:
        """Format the entire document."""
        uri = params.text_document.uri
        document = self.server.workspace.get_text_document(uri)

        try:
            parser = CP2KParser.parse_text(document.source, uri)
            if parser.ast:
                formatted = self._format_ast(parser.ast)
                return [
                    lsp.TextEdit(
                        range=lsp.Range(
                            start=lsp.Position(line=0, character=0),
                            end=lsp.Position(line=len(document.lines), character=len(document.lines[-1]) if document.lines else 0),
                        ),
                        new_text=formatted,
                    )
                ]
        except Exception:
            pass

        return None

    def _format_ast(self, ast: CP2KInput) -> str:
        """Format AST to string."""
        lines = []
        indent = "  "

        # Global section
        if ast.global_section:
            lines.extend(self._format_section(ast.global_section, 0, indent))

        # Other sections
        for section in ast.sections:
            if lines:
                lines.append("")  # Empty line between sections
            lines.extend(self._format_section(section, 0, indent))

        return "\n".join(lines) + "\n"

    def _format_section(self, section: Section, level: int, indent: str) -> List[str]:
        """Format a section."""
        lines = []
        current_indent = indent * level

        # Section start
        lines.append(f"{current_indent}&{section.name}")

        # Comments
        for comment in section.comments:
            lines.append(f"{current_indent}  !{comment.text}")

        # Keywords
        for keyword in section.keywords:
            if keyword.value.value is not None:
                value_str = self._format_value(keyword.value)
                lines.append(f"{current_indent}  {keyword.name} {value_str}")
            else:
                lines.append(f"{current_indent}  {keyword.name}")

        # Subsections
        for subsection in section.subsections:
            lines.append("")
            lines.extend(self._format_section(subsection, level + 1, indent))

        # Section end
        lines.append(f"{current_indent}&END {section.name}")

        return lines

    def _format_value(self, value) -> str:
        """Format a value."""
        if value.value is None:
            return ""

        from cp2k_lsp.parser.ast import ValueType

        if value.value_type == ValueType.BOOLEAN:
            return ".TRUE." if value.value else ".FALSE."
        elif value.value_type == ValueType.STRING:
            if " " in str(value.value):
                return f'"{value.value}"'
            return str(value.value)
        elif value.value_type == ValueType.NUMBER:
            if isinstance(value.value, float):
                # Format floats with appropriate precision
                return f"{value.value:.10g}"
            return str(value.value)
        else:
            return str(value.value)

    def provide_range_formatting(
        self, params: lsp.DocumentRangeFormattingParams
    ) -> Optional[List[lsp.TextEdit]]:
        """Format a range of the document."""
        uri = params.text_document.uri
        document = self.server.workspace.get_text_document(uri)

        # For range formatting, we format the entire document but return only the range
        # This is a simplified implementation
        try:
            parser = CP2KParser.parse_text(document.source, uri)
            if parser.ast:
                formatted = self._format_ast(parser.ast)
                return [
                    lsp.TextEdit(
                        range=params.range,
                        new_text=formatted,
                    )
                ]
        except Exception:
            pass

        return None

    def provide_on_type_formatting(
        self, params: lsp.DocumentOnTypeFormattingParams
    ) -> Optional[List[lsp.TextEdit]]:
        """Format as the user types."""
        # This is triggered when the user types certain characters
        # For now, return None as it's optional
        return None
