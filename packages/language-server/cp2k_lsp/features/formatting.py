"""Formatting Provider."""

from typing import Any, List, Optional

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

    def _format_ast(self, ast: Any, indent_level: int = 0) -> str:
        """Format a parsed cp2k_input_tools AST.

        This compatibility hook is used by older tests and callers. Runtime LSP
        formatting uses the source-preserving formatter above.
        """
        lines: List[str] = []
        indent = "  " * indent_level

        if hasattr(ast, "global_section") or hasattr(ast, "sections"):
            global_section = getattr(ast, "global_section", None)
            if global_section is not None:
                rendered = self._format_ast(global_section, indent_level)
                if rendered:
                    lines.extend(rendered.splitlines())
            for section in getattr(ast, "sections", []):
                rendered = self._format_ast(section, indent_level)
                if rendered:
                    lines.extend(rendered.splitlines())
            return "\n".join(lines)

        name = getattr(ast, "name", "/")
        if name != "/":
            param = self._format_value(getattr(ast, "parameter", getattr(ast, "param", None)))
            section_header = f"{indent}&{name}"
            if param:
                section_header += f" {param}"
            lines.append(section_header)
            indent_level += 1
            indent = "  " * indent_level

        for keyword in getattr(ast, "keywords", []):
            value_node = getattr(keyword, "value", None)
            value = self._format_value(
                getattr(value_node, "value", None)
                if value_node is not None
                else getattr(keyword, "values", None)
            )
            line = f"{indent}{getattr(keyword, 'name', '')}"
            if value:
                line += f" {value}"
            lines.append(line)

        for subsection in getattr(ast, "subsections", []):
            rendered = self._format_ast(subsection, indent_level)
            if rendered:
                lines.extend(rendered.splitlines())

        if name != "/":
            lines.append(f"{'  ' * (indent_level - 1)}&END {name}")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Serialize parser keyword/section values for compatibility formatting."""
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return " ".join(self._format_value(item) for item in value)
        return str(value)
