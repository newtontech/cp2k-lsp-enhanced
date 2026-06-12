"""Hover Provider with schema-backed documentation."""

from typing import Optional

from lsprotocol import types as lsp

from cp2k_input_tools.cursor_context import CursorContextResolver
from cp2k_lsp.agent_api.schema import (
    lookup_keyword_at_path,
    lookup_keyword_schema,
    lookup_section_schema,
)


class HoverProvider:
    """Provides hover information for CP2K input.

    Uses schema lookups to provide dynamic, up-to-date documentation
    for sections and keywords. Falls back to hardcoded docs when schema
    data is unavailable.
    """

    # Documentation for common sections (fallback)
    SECTION_DOCS = {
        "GLOBAL": """**GLOBAL** - Global settings section

Controls overall calculation parameters:
- `PROJECT_NAME` - Name of the project
- `RUN_TYPE` - Type of calculation (ENERGY, GEO_OPT, MD, etc.)
- `PRINT_LEVEL` - Verbosity of output (SILENT, LOW, MEDIUM, HIGH)
""",
        "FORCE_EVAL": """**FORCE_EVAL** - Force evaluation section

Defines how forces are calculated:
- Electronic structure method
- Basis sets and potentials
- Integration grids
""",
        "DFT": """**DFT** - Density Functional Theory section

Settings for DFT calculations:
- Exchange-correlation functional
- Basis sets
- Integration grids
- SCF convergence
""",
        "QS": """**QS** - Quickstep settings

Quickstep-specific parameters:
- Method selection
- Basis set handling
- Cutoff values
""",
        "SCF": """**SCF** - Self-Consistent Field section

SCF convergence settings:
- Maximum iterations
- Convergence thresholds
- Mixing methods
- Diagonalization options
""",
        "XC": """**XC** - Exchange-Correlation functional section

Define the XC functional:
- LDA, GGA, meta-GGA, hybrid functionals
- Functionals like PBE, BLYP, PBE0, etc.
""",
        "MOTION": """**MOTION** - Molecular dynamics and optimization

Controls geometry optimization and MD:
- Optimizer type
- MD ensemble and thermostat
- Convergence criteria
""",
    }

    # Documentation for common keywords (fallback)
    KEYWORD_DOCS = {
        "PROJECT_NAME": """**PROJECT_NAME** - Name of the project

Defines the basename for all output files.

**Type**: String
**Default**: PROJECT
""",
        "RUN_TYPE": """**RUN_TYPE** - Type of calculation

Available options:
- `ENERGY` - Single point energy
- `ENERGY_FORCE` - Energy and forces
- `GEO_OPT` - Geometry optimization
- `MD` - Molecular dynamics
- `BSSE` - Basis set superposition error
- `DEBUG` - Debug run

**Type**: Enum
**Default**: ENERGY
""",
        "PRINT_LEVEL": """**PRINT_LEVEL** - Verbosity of output

Available levels:
- `SILENT` - Minimal output
- `LOW` - Standard output
- `MEDIUM` - More detailed
- `HIGH` - Very detailed
- `DEBUG` - Debug information

**Type**: Enum
**Default**: MEDIUM
""",
        "EPS_SCF": """**EPS_SCF** - SCF convergence threshold

Convergence criterion for SCF iterations.

**Type**: Real
**Default**: 1.0E-7
**Unit**: Hartree
""",
        "MAX_SCF": """**MAX_SCF** - Maximum SCF iterations

Maximum number of SCF iterations before giving up.

**Type**: Integer
**Default**: 50
""",
    }

    def __init__(self, server):
        self.server = server
        self.context_resolver = CursorContextResolver()

    def provide_hover(self, params: lsp.HoverParams) -> Optional[lsp.Hover]:
        """Provide hover information.

        Uses schema lookups to provide dynamic documentation when available,
        falling back to hardcoded docs for backwards compatibility.
        """
        uri = params.text_document.uri
        position = params.position

        document = self.server.workspace.get_text_document(uri)
        lines = document.lines

        if position.line >= len(lines):
            return None

        line = lines[position.line]
        word = self._get_word_at_position(line, position.character)
        word_upper = word.upper()

        if not word_upper:
            return None

        # Get cursor context for section path
        cursor_context = self.context_resolver.resolve_cursor_context(
            uri=uri, lines=lines, line=position.line, character=position.character
        )
        section_path = ".".join(cursor_context.section_path) if cursor_context.section_path else None

        # Try schema-backed hover first
        hover_content = self._get_schema_hover(word_upper, section_path)
        if hover_content:
            return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=hover_content))

        # Fall back to hardcoded docs
        return self._get_fallback_hover(word_upper)

    def _get_schema_hover(self, word_upper: str, section_path: Optional[str]) -> Optional[str]:
        """Get hover content from schema lookups.

        Tries path-based lookup first (more specific), then global lookup.
        Returns formatted markdown or None if schema data unavailable.
        """
        # Try keyword lookup first (with section path if available)
        keyword_schema = None
        if section_path:
            keyword_schema = lookup_keyword_at_path(section_path, word_upper)
        if keyword_schema is None:
            keyword_schema = lookup_keyword_schema(word_upper)

        if keyword_schema:
            return self._format_keyword_hover(keyword_schema)

        # Try section lookup
        section_schema = lookup_section_schema(word_upper)
        if section_schema:
            return self._format_section_hover(section_schema)

        return None

    def _format_keyword_hover(self, schema: dict) -> str:
        """Format keyword schema into markdown hover content."""
        lines = []

        # Title with name and type
        name = schema.get("name", "UNKNOWN")
        kw_type = schema.get("type", "unknown")
        lines.append(f"**{name}** - `{kw_type}`")
        lines.append("")

        # Description
        description = schema.get("description", "")
        if description:
            lines.append(description)
            lines.append("")

        # Default value
        default = schema.get("default")
        if default is not None:
            if isinstance(default, float):
                lines.append(f"**Default**: {default:.1E}")
            else:
                lines.append(f"**Default**: `{default}`")
            lines.append("")

        # Enum values
        enum_values = schema.get("enum_values")
        if enum_values:
            lines.append("**Allowed values**:")
            lines.append("")
            for value in enum_values:
                lines.append(f"- `{value}`")
            lines.append("")

        # Units
        units = schema.get("units")
        if units:
            lines.append(f"**Units**: {', '.join(units)}")
            lines.append("")

        # Required flag
        if schema.get("required"):
            lines.append("**Required**: Yes")
            lines.append("")

        return "\n".join(lines)

    def _format_section_hover(self, schema: dict) -> str:
        """Format section schema into markdown hover content."""
        lines = []

        # Title
        name = schema.get("name", "UNKNOWN")
        lines.append(f"**{name}** - Section")
        lines.append("")

        # Description
        description = schema.get("description", "")
        if description:
            lines.append(description)
            lines.append("")

        # Keywords
        keywords = schema.get("keywords", [])
        if keywords:
            lines.append("**Keywords**:")
            lines.append("")
            for kw in keywords[:10]:  # Limit to first 10 for readability
                lines.append(f"- `{kw}`")
            if len(keywords) > 10:
                lines.append(f"- ... and {len(keywords) - 10} more")
            lines.append("")

        # Subsections
        subsections = schema.get("subsections", [])
        if subsections:
            lines.append("**Subsections**:")
            lines.append("")
            for sub in subsections[:8]:  # Limit to first 8
                lines.append(f"- `{sub}`")
            if len(subsections) > 8:
                lines.append(f"- ... and {len(subsections) - 8} more")
            lines.append("")

        # Properties
        if schema.get("required"):
            lines.append("**Required**: Yes")
        if schema.get("repeats"):
            lines.append("**Repeatable**: Yes")
        lines.append("")

        return "\n".join(lines)

    def _get_fallback_hover(self, word_upper: str) -> Optional[lsp.Hover]:
        """Get hover content from hardcoded fallback docs."""
        # Check if it's a section
        if word_upper in self.SECTION_DOCS:
            return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=self.SECTION_DOCS[word_upper]))

        # Check if it's a keyword
        if word_upper in self.KEYWORD_DOCS:
            return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=self.KEYWORD_DOCS[word_upper]))

        return None

    def _get_word_at_position(self, line: str, col: int) -> str:
        """Get word at cursor position."""
        if col >= len(line):
            col = len(line) - 1
        if col < 0:
            col = 0

        # Find word boundaries
        start = col
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = col
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        return line[start:end]
