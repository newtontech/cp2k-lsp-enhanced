"""
CP2K input completion provider for LSP.

This module provides semantic completion for CP2K input files using the
schema index and cursor context resolution.

Features:
- Section completion with snippets (after &)
- Keyword completion (inside sections)
- Enum value completion (for enumerated keywords)
- Logical value completion (for boolean/flag keywords)
- File name completion for *_FILE_NAME keywords
- Basis/potential name completion
- Workflow snippets (ENERGY, DFT/GPW, MGRID, SCF, GEO_OPT, MD)

TDD: Implementation written to pass tests in tests/test_lsp.py and tests/test_preprocessor_lsp.py
"""

from typing import List, Optional

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    InsertTextFormat,
    Position,
)

from .cursor_context import CursorContext, resolve_cursor_context
from .schema_index import CP2KSchemaIndex, get_schema_index

# Keywords that expect file names
_FILE_KEYWORDS = frozenset({
    "BASIS_SET_FILE_NAME",
    "POTENTIAL_FILE_NAME",
    "COORD_FILE_NAME",
    "COORD_FILE_FORMAT",
    "FORCE_EVAL_FILE_NAME",
    "INPUT_FILE_NAME",
    "OUTPUT_FILE_NAME",
    "RESTART_FILE_NAME",
    "WFN_RESTART_FILE_NAME",
    "KPOINTS_FILE_NAME",
    "STRESS_TENSOR_FILE_NAME",
    "V_HARTREE_CUBE_FILE_NAME",
    "E_DENSITY_CUBE_FILE_NAME",
    "MO_CUBE_FILE_NAME",
    "AO_MATRICES_FILE_NAME",
    "MOLECULE_FILE_NAME",
    "GEO_FILE_NAME",
    "CELL_FILE_NAME",
    "PDB_FILE_NAME",
    "PSF_FILE_NAME",
    "INP_FILE_NAME",
    "CHARGE_FILE_NAME",
    "GTO_BASIS_FILE_NAME",
    "BASIS_MOLOPT_FILE_NAME",
    "GTH_POTENTIALS_FILE_NAME",
    "ECPBAS_FILE_NAME",
    "NONLOCAL_P_FILE_NAME",
})

# Keywords that expect basis set names
_BASIS_KEYWORDS = frozenset({
    "BASIS_SET",
    "BASIS_SET_FILE_NAME",
})

# Keywords that expect pseudopotential names
_POTENTIAL_KEYWORDS = frozenset({
    "POTENTIAL",
    "POTENTIAL_FILE_NAME",
})

# Workflow snippet templates
_WORKFLOW_SNIPPETS = {
    "ENERGY": """&GLOBAL
  PROJECT_NAME ${1:project}
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME ${2:BASIS_MOLOPT}
    POTENTIAL_FILE_NAME ${3:GTH_POTENTIALS}
    &QS
      METHOD GPW
    &END QS
    &SCF
      MAX_SCF ${4:100}
      EPS_SCF ${5:1.0E-6}
      SCF_GUESS RESTART
      &OT
        PRECONDITIONER FULL_SINGLE_INVERSE
        MINIMIZER DIIS
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      A ${6:0.0 0.0 0.0}
      B ${7:0.0 0.0 0.0}
      C ${8:0.0 0.0 0.0}
    &END CELL
    &KIND ${9:Element}
      ELEMENT ${10:Element}
      BASIS_SET ${11:ORB basis}
      POTENTIAL ${12:GTH pot}
    &END KIND
  &END SUBSYS
&END FORCE_EVAL""",
    "DFT_GPW": """&DFT
  BASIS_SET_FILE_NAME ${1:BASIS_MOLOPT}
  POTENTIAL_FILE_NAME ${2:GTH_POTENTIALS}
  &QS
    METHOD GPW
    EPS_DEFAULT ${3:1.0E-10}
  &END QS
  &SCF
    MAX_SCF ${4:100}
    EPS_SCF ${5:1.0E-6}
    SCF_GUESS RESTART
    &OT
      PRECONDITIONER FULL_SINGLE_INVERSE
      MINIMIZER DIIS
    &END OT
  &END SCF
  &XC
    &XC_FUNCTIONAL PBE
    &END XC_FUNCTIONAL
  &END XC
&END DFT""",
    "MGRID": """&MGRID
  NGRIDS ${1:4}
  CUTOFF ${2:400}
  REL_CUTOFF ${3:50}
  COMMENSURATED ${4:FALSE}
&END MGRID""",
    "SCF_OT": """&SCF
  MAX_SCF ${1:100}
  EPS_SCF ${2:1.0E-6}
  SCF_GUESS RESTART
  &OT
    PRECONDITIONER FULL_SINGLE_INVERSE
    MINIMIZER DIIS
    N_HISTORY ${3:15}
    IDROP ${4:FALSE}
    ON_THE_FLY ${5:FALSE}
  &END OT
&END SCF""",
    "SCF_DIAGONALIZATION": """&SCF
  MAX_SCF ${1:100}
  EPS_SCF ${2:1.0E-6}
  SCF_GUESS RESTART
  &DIAGONALIZATION
    ALGORITHM ${3:STANDARD}
  &END DIAGONALIZATION
  &SMEAR
    METHOD ${4:Fermi_Dirac}
    ELECTRONIC_TEMPERATURE ${5:300}
  &END SMEAR
  ADDED_MOS ${6:0}
&END SCF""",
    "GEO_OPT": """&GLOBAL
  PROJECT_NAME ${1:project}
  RUN_TYPE GEO_OPT
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME ${2:BASIS_MOLOPT}
    POTENTIAL_FILE_NAME ${3:GTH_POTENTIALS}
    &SCF
      MAX_SCF ${4:100}
      EPS_SCF ${5:1.0E-6}
      &OT
        PRECONDITIONER FULL_SINGLE_INVERSE
        MINIMIZER DIIS
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      A ${6:0.0 0.0 0.0}
      B ${7:0.0 0.0 0.0}
      C ${8:0.0 0.0 0.0}
    &END CELL
    &KIND ${9:Element}
      ELEMENT ${10:Element}
      BASIS_SET ${11:ORB basis}
      POTENTIAL ${12:GTH pot}
    &END KIND
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &GEO_OPT
    TYPE MINIMIZATION
    MAX_ITER ${13:200}
    OPTIMIZER BFGS
    &CONSTRAINT
      &FIXED_ATOMS
        LIST ${14:1}
      &END FIXED_ATOMS
    &END CONSTRAINT
  &END GEO_OPT
&END MOTION""",
    "MD_NVT": """&GLOBAL
  PROJECT_NAME ${1:project}
  RUN_TYPE MD
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME ${2:BASIS_MOLOPT}
    POTENTIAL_FILE_NAME ${3:GTH_POTENTIALS}
    &SCF
      MAX_SCF ${4:100}
      EPS_SCF ${5:1.0E-6}
      &OT
        PRECONDITIONER FULL_SINGLE_INVERSE
        MINIMIZER DIIS
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      A ${6:0.0 0.0 0.0}
      B ${7:0.0 0.0 0.0}
      C ${8:0.0 0.0 0.0}
    &END CELL
    &KIND ${9:Element}
      ELEMENT ${10:Element}
      BASIS_SET ${11:ORB basis}
      POTENTIAL ${12:GTH pot}
    &END KIND
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS ${13:1000}
    TIMESTEP ${14:0.5}
    TEMPERATURE ${15:300}
    &THERMOSTAT
      TYPE NOSE
      &NOSE
        TIMECON ${16:10}
      &END NOSE
    &END THERMOSTAT
  &END MD
&END MOTION""",
    "MD_NPT": """&GLOBAL
  PROJECT_NAME ${1:project}
  RUN_TYPE MD
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME ${2:BASIS_MOLOPT}
    POTENTIAL_FILE_NAME ${3:GTH_POTENTIALS}
    &SCF
      MAX_SCF ${4:100}
      EPS_SCF ${5:1.0E-6}
      &OT
        PRECONDITIONER FULL_SINGLE_INVERSE
        MINIMIZER DIIS
      &END OT
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &CELL
      A ${6:0.0 0.0 0.0}
      B ${7:0.0 0.0 0.0}
      C ${8:0.0 0.0 0.0}
    &END CELL
    &KIND ${9:Element}
      ELEMENT ${10:Element}
      BASIS_SET ${11:ORB basis}
      POTENTIAL ${12:GTH pot}
    &END KIND
  &END SUBSYS
&END FORCE_EVAL

&MOTION
  &MD
    ENSEMBLE NPT_I
    STEPS ${13:1000}
    TIMESTEP ${14:0.5}
    TEMPERATURE ${15:300}
    &THERMOSTAT
      TYPE NOSE
      &NOSE
        TIMECON ${16:10}
      &END NOSE
    &END THERMOSTAT
    &BAROSTAT
      TYPE NOSE
      &NOSE
        TIMECON ${17:10}
      &END NOSE
    &END BAROSTAT
  &END MD
&END MOTION""",
    "KIND": """&KIND ${1:Element}
  ELEMENT ${2:Element}
  BASIS_SET ${3:ORB basis}
  POTENTIAL ${4:GTH pot}
  MASS ${5:0.0}
&END KIND""",
    "CELL": """&CELL
  A ${1:0.0 0.0 0.0}
  B ${2:0.0 0.0 0.0}
  C ${3:0.0 0.0 0.0}
  PERIODIC ${4:XYZ}
  MULTIPLE_UNIT_CELL ${5:1 1 1}
&END CELL""",
    "COORD": """&COORD
  SCHEME ${1:CONVENTIONAL}
  &UNITS
    UNIT ${2:angstrom}
  &END UNITS
&END COORD""",
    "QS": """&QS
  METHOD ${1:GPW}
  EPS_DEFAULT ${2:1.0E-10}
  EPS_PGF_ORB ${3:1.0E-20}
  EXTRAPOLATION ${4:USE_GUESS}
  EXTRAPOLATION_ORDER ${5:3}
&END QS""",
    "XC": """&XC
  &XC_FUNCTIONAL PBE
  &END XC_FUNCTIONAL
  &XC_GRID
    XC_SMOOTH_RHO ${1:NN50}
    XC_DERIV ${2:PW}
  &END XC_GRID
  &XC_NONLOCAL
    TYPE ${3:LDA}
  &END XC_NONLOCAL
&END XC""",
}


def get_completions(
    text: str,
    position: Position,
    uri: str,
) -> Optional[CompletionList]:
    """Get completion items for the given cursor position.

    Args:
        text: The full text of the CP2K input file
        position: The cursor position (line, character)
        uri: The file URI

    Returns:
        CompletionList with appropriate items, or None if no completions available
    """
    # Resolve cursor context
    ctx = resolve_cursor_context(text, line=position.line, character=position.character, uri=uri)

    # Get schema index
    schema = get_schema_index()

    items: List[CompletionItem] = []

    # Section completion (after &)
    if ctx.is_section_start:
        items.extend(_complete_sections(schema, ctx, text))

    # Keyword completion (inside section)
    elif ctx.current_section and not ctx.is_section_end:
        if ctx.is_value_position:
            # Value completion (enums, logical values, file names, basis/potential)
            items.extend(_complete_values(schema, ctx))
        elif ctx.is_keyword_position:
            # Keyword completion
            items.extend(_complete_keywords(schema, ctx))
        else:
            # Default to keyword completion for empty lines in sections
            items.extend(_complete_keywords(schema, ctx))

    # Workflow snippets at root level (outside sections)
    if not ctx.current_section and not ctx.is_section_start and ctx.prefix:
        items.extend(_complete_workflow_snippets(ctx.prefix))

    if not items:
        return None

    return CompletionList(
        is_incomplete=False,
        items=items,
    )


def _complete_sections(schema: CP2KSchemaIndex, ctx: CursorContext, text: str) -> List[CompletionItem]:
    """Get section completions with snippet insert text for the current context."""
    prefix = ""
    if ctx.is_section_start:
        lines = text.splitlines()
        line_text = lines[ctx.line] if 0 <= ctx.line < len(lines) else ""
        ampersand_pos = line_text.find("&")
        if ampersand_pos >= 0:
            prefix = line_text[ampersand_pos + 1 : ctx.character].strip().upper()

    section_path = ctx.section_path
    if ctx.is_section_start and section_path:
        section_path = section_path[:-1]

    if section_path:
        section_spec = schema.get_section(section_path)
        if section_spec:
            child_sections = schema.get_child_sections(section_path)
        else:
            child_sections = []
    else:
        child_sections = schema.get_root_sections()

    items = []
    for section_name in child_sections:
        if not prefix or section_name.upper().startswith(prefix):
            section_detail = schema.get_section(section_path + (section_name,) if section_path else (section_name,))
            snippet = f"{section_name}\n  $0\n&END {section_name}"
            items.append(
                CompletionItem(
                    label=section_name,
                    kind=CompletionItemKind.Module,
                    detail=section_detail.description if section_detail else "",
                    documentation=section_detail.description if section_detail else "",
                    insert_text=snippet,
                    insert_text_format=InsertTextFormat.Snippet,
                )
            )

    return items


def _complete_keywords(schema: CP2KSchemaIndex, ctx: CursorContext) -> List[CompletionItem]:
    """Get keyword completions for the current section."""
    if not ctx.current_section:
        return []

    # Get prefix for filtering
    prefix = ctx.prefix.upper()

    # Get keywords for current section
    section_path = ctx.section_path if ctx.section_path else (ctx.current_section,)
    keywords = schema.get_keywords(section_path)

    items = []
    for keyword_name, keyword_spec in keywords.items():
        if not prefix or keyword_name.upper().startswith(prefix):
            # Build detail text with type and default
            detail_parts = []
            if keyword_spec.variable_type:
                detail_parts.append(keyword_spec.variable_type)
            if keyword_spec.default_value:
                detail_parts.append(f"default: {keyword_spec.default_value}")
            detail = " | ".join(detail_parts) if detail_parts else keyword_spec.description or ""

            items.append(
                CompletionItem(
                    label=keyword_name,
                    kind=CompletionItemKind.Field,
                    detail=detail,
                    documentation=keyword_spec.description,
                    insert_text=keyword_name,
                )
            )

    return items


def _complete_values(schema: CP2KSchemaIndex, ctx: CursorContext) -> List[CompletionItem]:
    """Get value completions for the current keyword."""
    if not ctx.current_keyword or not ctx.current_section:
        return []

    section_path: tuple[str, ...] = ctx.section_path if ctx.section_path else (ctx.current_section,)
    keyword_spec = schema.get_keyword(section_path, ctx.current_keyword)

    if not keyword_spec:
        return []

    items = []
    prefix = ctx.prefix.upper()

    if keyword_spec.enumeration_values:
        for value in keyword_spec.enumeration_values:
            if not prefix or value.upper().startswith(prefix):
                items.append(
                    CompletionItem(
                        label=value,
                        kind=CompletionItemKind.EnumMember,
                        detail=f"Enum value for {ctx.current_keyword}",
                    )
                )
    elif keyword_spec.variable_type and "logical" in keyword_spec.variable_type.lower():
        for value in ["F", ".FALSE.", "T", ".TRUE."]:
            if not prefix or value.upper().startswith(prefix):
                items.append(
                    CompletionItem(
                        label=value,
                        kind=CompletionItemKind.Value,
                        detail="Logical value",
                    )
                )
    elif ctx.current_keyword.upper() in _FILE_KEYWORDS:
        items.extend(_complete_file_values(ctx.current_keyword, prefix))
    elif ctx.current_keyword.upper() in _BASIS_KEYWORDS:
        items.extend(_complete_basis_values(prefix))
    elif ctx.current_keyword.upper() in _POTENTIAL_KEYWORDS:
        items.extend(_complete_potential_values(prefix))

    return items


def _complete_file_values(keyword: str, prefix: str) -> List[CompletionItem]:
    """Get file name completions for file-related keywords."""
    items = []
    common_extensions = [".inp", ".out", ".restart", ".xyz", ".pdb", ".psf", ".cube", ".log"]
    base_name = keyword.replace("_FILE_NAME", "").replace("_FILE", "").lower()

    suggestions = [
        f"./{base_name}",
        f"./{base_name}.inp",
        f"./{base_name}.out",
        f"${{PROJECT_NAME}}.{base_name}",
    ]
    for ext in common_extensions:
        suggestions.append(f"./{base_name}{ext}")

    for suggestion in suggestions:
        if not prefix or suggestion.upper().startswith(prefix):
            items.append(
                CompletionItem(
                    label=suggestion,
                    kind=CompletionItemKind.File,
                    detail="File path",
                )
            )
    return items


def _complete_basis_values(prefix: str) -> List[CompletionItem]:
    """Get basis set name completions."""
    items = []
    common_basis = [
        "DZVP-MOLOPT-GTH",
        "TZVP-MOLOPT-GTH",
        "TZV2P-MOLOPT-GTH",
        "TZV2P-MOLOPT-GTH-Q",
        "TZVP-GTH",
        "DZVP-GTH",
        "SZV-GTH",
        "DZVP",
        "TZVP",
        "TZV2P",
        "SZV",
        "MOLOPT-DZVP-GTH",
        "MOLOPT-TZVP-GTH",
        "MOLOPT-TZV2P-GTH",
        "PBE-DZVP",
        "PBE-TZVP",
        "PBE-TZV2P",
    ]
    for basis in common_basis:
        if not prefix or basis.upper().startswith(prefix):
            items.append(
                CompletionItem(
                    label=basis,
                    kind=CompletionItemKind.EnumMember,
                    detail="Basis set",
                )
            )
    return items


def _complete_potential_values(prefix: str) -> List[CompletionItem]:
    """Get pseudopotential name completions."""
    items = []
    common_potentials = [
        "GTH_PBE",
        "GTH_PBE-Q",
        "GTH_PBEMOLOPT",
        "GTH_PBEMOLOPT-SR",
        "GTH_BLYP",
        "GTH_HCTH120",
        "GTH_BLYP-Q",
        "GTH_PBE",
        "GTH_BP",
        "GTH_PADE",
        "GTH_PADE-Q",
    ]
    for pot in common_potentials:
        if not prefix or pot.upper().startswith(prefix):
            items.append(
                CompletionItem(
                    label=pot,
                    kind=CompletionItemKind.EnumMember,
                    detail="Pseudopotential",
                )
            )
    return items


def _complete_workflow_snippets(prefix: str) -> List[CompletionItem]:
    """Get workflow snippet completions for root-level use."""
    items = []
    prefix_upper = prefix.upper()
    for name, snippet in _WORKFLOW_SNIPPETS.items():
        if not prefix or name.upper().startswith(prefix_upper):
            items.append(
                CompletionItem(
                    label=name,
                    kind=CompletionItemKind.Snippet,
                    detail="Workflow snippet",
                    documentation=f"Insert {name} workflow template",
                    insert_text=snippet,
                    insert_text_format=InsertTextFormat.Snippet,
                )
            )
    return items
