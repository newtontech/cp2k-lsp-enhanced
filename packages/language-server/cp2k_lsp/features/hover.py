"""Hover Provider."""

from typing import Optional

from lsprotocol import types as lsp


class HoverProvider:
    """Provides hover information for CP2K input."""

    # Documentation for common sections
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
        "KIND": """**KIND** - Atomic kind definition

Defines properties of atomic species:
- ELEMENT - Chemical element
- BASIS_SET - Basis set name
- POTENTIAL - Pseudopotential
- MAGNETIZATION - Initial magnetic moment
""",
        "CELL": """**CELL** - Unit cell definition

Defines the simulation cell:
- A, B, C - Cell vectors
- ALPHA, BETA, GAMMA - Cell angles
- PERIODIC - Periodic boundary conditions
- SYMMETRY - Space group symmetry
""",
        "COORD": """**COORD** - Atomic coordinates

Defines atomic positions:
- Cartesian or fractional coordinates
- UNIT - Coordinate unit (ANGSTROM, BOHR)
- SCALED - Use scaled coordinates
""",
    }

    # Documentation for common keywords
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
        "BASIS_SET": """**BASIS_SET** - Basis set name

Specifies the Gaussian basis set for this atomic kind.
Common choices: DZVP-MOLOPT-SR-GTH, TZVP-MOLOPT-GTH

**Type**: String
**Required**: Yes
""",
        "POTENTIAL": """**POTENTIAL** - Pseudopotential name

Specifies the pseudopotential for this atomic kind.
Common choices: GTH-PBE, GTH-BLYP

**Type**: String
""",
        "ELEMENT": """**ELEMENT** - Chemical element symbol

Specifies the chemical element for this atomic kind.

**Type**: String
**Required**: Yes
""",
    }

    def __init__(self, server):
        self.server = server

    def provide_hover(self, params: lsp.HoverParams) -> Optional[lsp.Hover]:
        """Provide hover information."""
        uri = params.text_document.uri
        position = params.position

        document = self.server.workspace.get_text_document(uri)
        lines = document.lines

        if position.line >= len(lines):
            return None

        line = lines[position.line]
        word = self._get_word_at_position(line, position.character)
        word_upper = word.upper()

        # Check if it's a section
        if word_upper in self.SECTION_DOCS:
            return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=self.SECTION_DOCS[word_upper]))

        # Check if it's a keyword
        if word_upper in self.KEYWORD_DOCS:
            return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=self.KEYWORD_DOCS[word_upper]))

        # Check from keyword database if available
        try:
            from cp2k_lsp.data.keywords import get_keyword_info
            kw_info = get_keyword_info(word_upper)
            if kw_info:
                doc = f"**{kw_info.name}**\n\n{kw_info.description}\n\n**Type**: {kw_info.keyword_type.value}"
                if kw_info.default is not None:
                    doc += f"\n**Default**: {kw_info.default}"
                if kw_info.required:
                    doc += "\n**Required**: Yes"
                return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=doc))
        except ImportError:
            pass

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
