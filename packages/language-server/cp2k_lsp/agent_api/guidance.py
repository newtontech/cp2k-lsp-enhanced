"""Minimal examples and next-token guidance API (#38).

Provides ready-made minimal CP2K input examples for common calculation
types and context-aware suggestions for what to write next given a
partial CP2K input.
"""

from typing import Any, Dict, List, Optional

from cp2k_lsp.data.keywords import get_keyword_info
from cp2k_lsp.data.sections import get_valid_keywords, get_valid_subsections
from cp2k_lsp.parser import CP2KParser

# ---------------------------------------------------------------------------
# Minimal examples – #38
# ---------------------------------------------------------------------------

MINIMAL_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "energy": {
        "description": "Single-point energy calculation for a water molecule using PBE/DZVP",
        "run_type": "ENERGY",
        "input": (
            "&GLOBAL\n"
            "  PROJECT_NAME water_energy\n"
            "  RUN_TYPE ENERGY\n"
            "  PRINT_LEVEL MEDIUM\n"
            "&END GLOBAL\n"
            "\n"
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    BASIS_SET_FILE_NAME BASIS_MOLOPT\n"
            "    POTENTIAL_FILE_NAME GTH_POTENTIALS\n"
            "    &MGRID\n"
            "      CUTOFF 400\n"
            "      REL_CUTOFF 50\n"
            "    &END MGRID\n"
            "    &SCF\n"
            "      SCF_GUESS ATOMIC\n"
            "      EPS_SCF 1.0E-6\n"
            "      MAX_SCF 50\n"
            "      &OT\n"
            "        MINIMIZER DIIS\n"
            "        PRECONDITIONER FULL_SINGLE_INVERSE\n"
            "      &END OT\n"
            "    &END SCF\n"
            "    &XC\n"
            "      &XC_FUNCTIONAL PBE\n"
            "      &END XC_FUNCTIONAL\n"
            "    &END XC\n"
            "  &END DFT\n"
            "  &SUBSYS\n"
            "    &CELL\n"
            "      ABC 10.0 10.0 10.0\n"
            "      PERIODIC XYZ\n"
            "    &END CELL\n"
            "    &KIND H\n"
            "      BASIS_SET DZVP-GTH\n"
            "      POTENTIAL GTH-PBE-q1\n"
            "    &END KIND\n"
            "    &KIND O\n"
            "      BASIS_SET DZVP-GTH\n"
            "      POTENTIAL GTH-PBE-q6\n"
            "    &END KIND\n"
            "    &COORD\n"
            "      O  0.000000  0.000000  0.117489\n"
            "      H  0.000000  0.757210 -0.469957\n"
            "      H  0.000000 -0.757210 -0.469957\n"
            "    &END COORD\n"
            "  &END SUBSYS\n"
            "&END FORCE_EVAL\n"
        ),
    },
    "geo_opt": {
        "description": "Geometry optimisation of a water molecule using B3LYP/TZVP",
        "run_type": "GEO_OPT",
        "input": (
            "&GLOBAL\n"
            "  PROJECT_NAME water_opt\n"
            "  RUN_TYPE GEO_OPT\n"
            "&END GLOBAL\n"
            "\n"
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    BASIS_SET_FILE_NAME BASIS_MOLOPT\n"
            "    POTENTIAL_FILE_NAME GTH_POTENTIALS\n"
            "    &MGRID\n"
            "      CUTOFF 400\n"
            "    &END MGRID\n"
            "    &SCF\n"
            "      EPS_SCF 1.0E-6\n"
            "      MAX_SCF 50\n"
            "      &OT\n"
            "        MINIMIZER DIIS\n"
            "        PRECONDITIONER FULL_SINGLE_INVERSE\n"
            "      &END OT\n"
            "    &END SCF\n"
            "    &XC\n"
            "      &XC_FUNCTIONAL B3LYP\n"
            "      &END XC_FUNCTIONAL\n"
            "    &END XC\n"
            "  &END DFT\n"
            "  &SUBSYS\n"
            "    &CELL\n"
            "      ABC 10.0 10.0 10.0\n"
            "    &END CELL\n"
            "    &KIND H\n"
            "      BASIS_SET TZVP-GTH\n"
            "      POTENTIAL GTH-B3LYP-q1\n"
            "    &END KIND\n"
            "    &KIND O\n"
            "      BASIS_SET TZVP-GTH\n"
            "      POTENTIAL GTH-B3LYP-q6\n"
            "    &END KIND\n"
            "    &COORD\n"
            "      O  0.000000  0.000000  0.117489\n"
            "      H  0.000000  0.757210 -0.469957\n"
            "      H  0.000000 -0.757210 -0.469957\n"
            "    &END COORD\n"
            "  &END SUBSYS\n"
            "&END FORCE_EVAL\n"
            "\n"
            "&MOTION\n"
            "  &GEO_OPT\n"
            "    MAX_ITER 200\n"
            "    OPTIMIZER BFGS\n"
            "  &END GEO_OPT\n"
            "&END MOTION\n"
        ),
    },
    "md_nvt": {
        "description": "NVT molecular dynamics simulation of water using PBE/DZVP",
        "run_type": "MD",
        "input": (
            "&GLOBAL\n"
            "  PROJECT_NAME water_md\n"
            "  RUN_TYPE MD\n"
            "&END GLOBAL\n"
            "\n"
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    BASIS_SET_FILE_NAME BASIS_MOLOPT\n"
            "    POTENTIAL_FILE_NAME GTH_POTENTIALS\n"
            "    &MGRID\n"
            "      CUTOFF 400\n"
            "    &END MGRID\n"
            "    &SCF\n"
            "      EPS_SCF 1.0E-6\n"
            "      MAX_SCF 50\n"
            "      SCF_GUESS RESTART\n"
            "      &OT\n"
            "        MINIMIZER DIIS\n"
            "        PRECONDITIONER FULL_SINGLE_INVERSE\n"
            "      &END OT\n"
            "    &END SCF\n"
            "    &XC\n"
            "      &XC_FUNCTIONAL PBE\n"
            "      &END XC_FUNCTIONAL\n"
            "    &END XC\n"
            "  &END DFT\n"
            "  &SUBSYS\n"
            "    &CELL\n"
            "      ABC 10.0 10.0 10.0\n"
            "      PERIODIC XYZ\n"
            "    &END CELL\n"
            "    &KIND H\n"
            "      BASIS_SET DZVP-GTH\n"
            "      POTENTIAL GTH-PBE-q1\n"
            "    &END KIND\n"
            "    &KIND O\n"
            "      BASIS_SET DZVP-GTH\n"
            "      POTENTIAL GTH-PBE-q6\n"
            "    &END KIND\n"
            "    &COORD\n"
            "      O  0.000000  0.000000  0.117489\n"
            "      H  0.000000  0.757210 -0.469957\n"
            "      H  0.000000 -0.757210 -0.469957\n"
            "    &END COORD\n"
            "  &END SUBSYS\n"
            "&END FORCE_EVAL\n"
            "\n"
            "&MOTION\n"
            "  &MD\n"
            "    ENSEMBLE NVT\n"
            "    STEPS 1000\n"
            "    TIMESTEP 0.5\n"
            "    TEMPERATURE 300\n"
            "    &THERMOSTAT\n"
            "      TYPE CSVR\n"
            "      CSVR_TIMECONST 100\n"
            "    &END THERMOSTAT\n"
            "  &END MD\n"
            "&END MOTION\n"
        ),
    },
    "cell_opt": {
        "description": "Cell optimisation (variable-cell geometry optimisation)",
        "run_type": "CELL_OPT",
        "input": (
            "&GLOBAL\n"
            "  PROJECT_NAME cell_opt\n"
            "  RUN_TYPE CELL_OPT\n"
            "&END GLOBAL\n"
            "\n"
            "&FORCE_EVAL\n"
            "  METHOD QS\n"
            "  &DFT\n"
            "    BASIS_SET_FILE_NAME BASIS_MOLOPT\n"
            "    POTENTIAL_FILE_NAME GTH_POTENTIALS\n"
            "    &MGRID\n"
            "      CUTOFF 400\n"
            "    &END MGRID\n"
            "    &SCF\n"
            "      EPS_SCF 1.0E-6\n"
            "      MAX_SCF 50\n"
            "      &OT\n"
            "        MINIMIZER DIIS\n"
            "        PRECONDITIONER FULL_SINGLE_INVERSE\n"
            "      &END OT\n"
            "    &END SCF\n"
            "    &XC\n"
            "      &XC_FUNCTIONAL PBE\n"
            "      &END XC_FUNCTIONAL\n"
            "    &END XC\n"
            "  &END DFT\n"
            "  &SUBSYS\n"
            "    &CELL\n"
            "      ABC 5.0 5.0 5.0\n"
            "      PERIODIC XYZ\n"
            "    &END CELL\n"
            "    &KIND Si\n"
            "      BASIS_SET DZVP-GTH\n"
            "      POTENTIAL GTH-PBE-q4\n"
            "    &END KIND\n"
            "    &COORD\n"
            "      Si  0.000000  0.000000  0.000000\n"
            "      Si  1.250000  1.250000  1.250000\n"
            "    &END COORD\n"
            "  &END SUBSYS\n"
            "&END FORCE_EVAL\n"
            "\n"
            "&MOTION\n"
            "  &CELL_OPT\n"
            "    MAX_ITER 200\n"
            "    OPTIMIZER BFGS\n"
            "    KEEP_SYMMETRY .TRUE.\n"
            "  &END CELL_OPT\n"
            "&END MOTION\n"
        ),
    },
}


def list_available_examples() -> List[Dict[str, str]]:
    """List all available minimal example templates.

    Each entry has ``id``, ``description``, and ``run_type``.
    """
    return [{"id": key, "description": val["description"], "run_type": val["run_type"]} for key, val in MINIMAL_EXAMPLES.items()]


def get_minimal_example(example_id: str) -> Optional[Dict[str, Any]]:
    """Return a minimal CP2K input example by ID.

    Returns a dict with ``id``, ``description``, ``run_type``, and
    ``input`` (the full CP2K input text).  Returns *None* if the ID is
    unknown.
    """
    example_id = example_id.lower().strip()
    entry = MINIMAL_EXAMPLES.get(example_id)
    if entry is None:
        return None
    return {
        "id": example_id,
        "description": entry["description"],
        "run_type": entry["run_type"],
        "input": entry["input"],
    }


# ---------------------------------------------------------------------------
# Next-token guidance – #38
# ---------------------------------------------------------------------------


def get_next_token_guidance(partial_input: str) -> Dict[str, Any]:
    """Return context-aware suggestions for completing *partial_input*.

    The function parses the partial CP2K input, determines the current
    context (which section the cursor is in, what has already been
    written), and returns suggestions for what could come next.

    Returns a dict with:
      - ``context``: description of the current parsing context
      - ``suggested_sections``: section names that are valid at this point
      - ``suggested_keywords``: keyword names that are valid in the
        current section
      - ``suggested_values``: value suggestions if the cursor is after a
        keyword assignment (e.g., enum values)
      - ``notes``: free-text hints for the agent
    """
    result: Dict[str, Any] = {
        "context": "",
        "suggested_sections": [],
        "suggested_keywords": [],
        "suggested_values": [],
        "notes": "",
    }

    if not partial_input or not partial_input.strip():
        result["context"] = "empty_input"
        result["suggested_sections"] = ["GLOBAL", "FORCE_EVAL", "MOTION"]
        result["notes"] = (
            "Start with &GLOBAL to define the project name and run type, "
            "then add &FORCE_EVAL for the electronic structure calculation."
        )
        return result

    # Parse the partial input (tolerant parsing)
    parser = CP2KParser.parse_text(partial_input, "<guidance>")
    ast = parser.ast

    # Collect all open sections (sections without a matching &END)
    open_sections = _collect_open_sections(partial_input)

    # Determine context
    if open_sections:
        current_section_name = open_sections[-1].upper()
        result["context"] = f"inside_section:{current_section_name}"
        result["notes"] = f"Currently inside &{current_section_name}."

        # Get valid subsections and keywords
        subsections = get_valid_subsections(current_section_name)
        keywords = get_valid_keywords(current_section_name)

        result["suggested_sections"] = subsections
        result["suggested_keywords"] = keywords

        # Check if the last line looks like a keyword assignment awaiting a value
        lines = partial_input.rstrip().split("\n")
        last_line = lines[-1].strip() if lines else ""
        result["suggested_values"] = _suggest_values_for_line(last_line)

        # Check if we're looking at the root level (inside &GLOBAL, &FORCE_EVAL, etc.)
        # and suggest closing the section
        if not result["suggested_values"]:
            top_level = ["GLOBAL", "FORCE_EVAL", "MOTION"]
            existing_top = set()
            if ast:
                if ast.global_section:
                    existing_top.add("GLOBAL")
                for sec in ast.sections:
                    existing_top.add(sec.name.upper())

            if current_section_name in top_level:
                # We're at root level inside a section; after &END, user may want these
                pass
    else:
        # Outside any section
        result["context"] = "root_level"
        existing_top = set()
        if ast:
            if ast.global_section:
                existing_top.add("GLOBAL")
            for sec in ast.sections:
                existing_top.add(sec.name.upper())

        top_level_sections = ["GLOBAL", "FORCE_EVAL", "MOTION"]
        result["suggested_sections"] = [s for s in top_level_sections if s not in existing_top]

        if "GLOBAL" not in existing_top:
            result["notes"] = "Start with &GLOBAL to set the project name and run type."
        elif "FORCE_EVAL" not in existing_top:
            result["notes"] = "Add &FORCE_EVAL to define the electronic structure method."

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_open_sections(text: str) -> List[str]:
    """Return a list of section names that have been opened but not closed."""
    open_stack: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("!") or stripped.startswith("#"):
            continue

        upper = stripped.upper()
        if upper.startswith("&END"):
            # Close the most recent section
            parts = upper.split()
            if len(parts) > 1:
                # &END SECTION_NAME
                sec_name = parts[1]
                # Pop from stack
                for i in range(len(open_stack) - 1, -1, -1):
                    if open_stack[i] == sec_name:
                        open_stack = open_stack[:i]
                        break
            else:
                # Bare &END closes the innermost section
                if open_stack:
                    open_stack.pop()
        elif upper.startswith("&"):
            # Section start
            parts = stripped.split()
            if parts:
                sec_name = parts[0][1:]  # Remove leading &
                if sec_name.upper() not in ("END",):
                    open_stack.append(sec_name.upper())

    return open_stack


def _suggest_values_for_line(line: str) -> List[str]:
    """Check if *line* looks like ``KEYWORD =`` or ``KEYWORD`` awaiting a value.

    Returns a list of suggested values (e.g., enum values for known keywords).
    """
    line = line.strip()
    if not line:
        return []

    # Handle both KEYWORD = VALUE and KEYWORD VALUE forms
    # Check for assignment form: "KEYWORD =" or "KEYWORD = " (no value yet)
    parts_eq = line.split("=", 1)
    if len(parts_eq) == 2:
        kw_name = parts_eq[0].strip().upper()
        value_part = parts_eq[1].strip()
        if not value_part:
            # Assignment without value – suggest values
            return _get_value_suggestions(kw_name)
        return []

    # Handle whitespace form: "KEYWORD" at end (no value yet)
    parts_ws = line.split()
    if parts_ws:
        kw_name = parts_ws[0].upper()
        if len(parts_ws) == 1 and not line.endswith("&"):
            # Just a keyword name, no value yet
            return _get_value_suggestions(kw_name)

    return []


def _get_value_suggestions(kw_name: str) -> List[str]:
    """Return value suggestions for a keyword name."""
    info = get_keyword_info(kw_name)
    if info is None:
        return []

    if info.enum_values:
        return list(info.enum_values)
    elif info.keyword_type.value == "boolean":
        return [".TRUE.", ".FALSE."]
    elif info.units:
        return [f"<{info.keyword_type.value}> [{u}]" for u in info.units]
    else:
        return [f"<{info.keyword_type.value}>"]
