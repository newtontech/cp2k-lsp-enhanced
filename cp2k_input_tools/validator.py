"""
Semantic validation engine for CP2K input files.

Provides validation rules that go beyond syntax/schema checking to catch
physically or logically inconsistent configurations.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy",
    "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
}

# CP2K 2024.1 removed/deprecated parameters
REMOVED_KEYWORDS = {
    "SINGLE_PRECISION_MATRICES",
    "BROYDEN_MIXING_NEW",
    "KP_RI_EXTENSION_FACTOR",
}

DEPRECATED_KEYWORDS = {
    "QUIP": "Use other machine-learning potentials instead.",
    "PEXSI": "PEXSI support is deprecated in CP2K 2024.1.",
}

# RUN_TYPE to required MOTION sections mapping
RUN_TYPE_MOTION_MAP = {
    "GEO_OPT": {"GEO_OPT"},
    "MD": {"MD"},
    "CELL_OPT": {"CELL_OPT"},
    "BAND": {"BAND"},
    "MC": {"MC"},
    "VIBRATIONAL_ANALYSIS": {"VIBRATIONAL_ANALYSIS"},
}

# RUN_TYPE that should NOT have motion sections
STATIC_RUN_TYPES = {"ENERGY", "ENERGY_FORCE", "WAVEFUNCTION", "ELECTRONIC_SPECTRA", "ELASTIC_CONSTANT"}

# Motion sections that are NOT valid for static calculations
FORBIDDEN_MOTION_FOR_STATIC = {"GEO_OPT", "MD", "CELL_OPT", "BAND", "MC", "VIBRATIONAL_ANALYSIS"}


@dataclass
class Diagnostic:
    """A single validation diagnostic."""

    severity: str  # "error", "warning", "info"
    source: str  # "cp2k-parser", "cp2k-schema", "cp2k-lint", "cp2k-semantics"
    code: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationResult:
    """Collection of diagnostics from a validation run."""

    diagnostics: List[Diagnostic] = field(default_factory=list)

    @property
    def errors(self):
        return [d for d in self.diagnostics if d.severity == "error"]

    @property
    def warnings(self):
        return [d for d in self.diagnostics if d.severity == "warning"]

    @property
    def has_errors(self):
        return len(self.errors) > 0

    def add_error(self, source, code, message, line=None, column=None, suggested_fix=None):
        self.diagnostics.append(Diagnostic(
            severity="error", source=source, code=code, message=message,
            line=line, column=column, suggested_fix=suggested_fix,
        ))

    def add_warning(self, source, code, message, line=None, column=None, suggested_fix=None):
        self.diagnostics.append(Diagnostic(
            severity="warning", source=source, code=code, message=message,
            line=line, column=column, suggested_fix=suggested_fix,
        ))


def _find_section(tree: dict, *path: str) -> Optional[dict]:
    """Navigate nested dict by section path, accounting for '+' prefix on sections."""
    current = tree
    for name in path:
        found = current.get(f"+{name.lower()}")
        if found is None:
            # try without prefix
            found = current.get(name.lower())
        if found is None:
            return None
        if isinstance(found, list):
            current = found[0]
        elif isinstance(found, dict):
            current = found
        else:
            return None
    return current


def _get_value(tree: dict, *path: str, default=None):
    """Get a keyword value from the nested dict."""
    current = tree
    for name in path[:-1]:
        found = current.get(f"+{name.lower()}")
        if found is None:
            found = current.get(name.lower())
        if found is None:
            return default
        if isinstance(found, list):
            current = found[0]
        elif isinstance(found, dict):
            current = found
        else:
            return default
    key = path[-1].lower()
    return current.get(key, default)


def validate_run_type_motion_consistency(tree: dict, result: ValidationResult):
    """Issue #3: Check RUN_TYPE vs MOTION section consistency."""
    global_section = _find_section(tree, "GLOBAL")
    if global_section is None:
        return

    run_type = global_section.get("run_type")
    if run_type is None:
        return

    if isinstance(run_type, list):
        run_type = run_type[0]
    run_type = str(run_type).upper()

    motion_section = _find_section(tree, "MOTION")

    if run_type in STATIC_RUN_TYPES:
        if motion_section is None:
            return
        for forbidden in FORBIDDEN_MOTION_FOR_STATIC:
            motion_key = f"+{forbidden.lower()}"
            if motion_key in motion_section:
                result.add_error(
                    source="cp2k-semantics",
                    code="RUN_TYPE_MOTION_MISMATCH",
                    message=f"RUN_TYPE={run_type} indicates a static calculation, but "
                            f"&{forbidden} section was found. Remove the &{forbidden} section "
                            f"or change RUN_TYPE to {forbidden}.",
                    suggested_fix=f"Remove &{forbidden} section or change RUN_TYPE to {forbidden}",
                )

    elif run_type in RUN_TYPE_MOTION_MAP:
        required_sections = RUN_TYPE_MOTION_MAP[run_type]
        if motion_section is None:
            result.add_error(
                source="cp2k-semantics",
                code="RUN_TYPE_MISSING_MOTION",
                message=f"RUN_TYPE={run_type} requires a &{required_sections} section under &MOTION.",
                suggested_fix=f"Add &{next(iter(required_sections))} section under &MOTION",
            )
        else:
            for required in required_sections:
                motion_key = f"+{required.lower()}"
                if motion_key not in motion_section:
                    result.add_warning(
                        source="cp2k-semantics",
                        code="RUN_TYPE_MISSING_MOTION_SECTION",
                        message=f"RUN_TYPE={run_type} but no &{required} section found under &MOTION.",
                        suggested_fix=f"Add &{required} section under &MOTION",
                    )


def validate_force_eval_method(tree: dict, result: ValidationResult):
    """Issue #1: Validate FORCE_EVAL METHOD compatibility."""
    force_evals = tree.get("+force_eval")
    if force_evals is None:
        return

    if not isinstance(force_evals, list):
        force_evals = [force_evals]

    for i, fe in enumerate(force_evals):
        method = fe.get("method")
        if method is None:
            continue
        if isinstance(method, list):
            method = method[0]
        method = str(method).upper()

        dft_section = fe.get("+dft")
        fist_section = fe.get("+fist")
        mm_section = fe.get("+mm")
        nnp_section = fe.get("+nnp")

        if method == "QS" or method == "QUICKSTEP":
            if fist_section is not None:
                result.add_error(
                    source="cp2k-semantics", code="METHOD_SECTION_CONFLICT",
                    message=f"METHOD=QS but &FIST section found. QS (Quickstep) and FIST (classical) are mutually exclusive.",
                    suggested_fix="Remove &FIST section or change METHOD to FIST",
                )
            if mm_section is not None:
                result.add_error(
                    source="cp2k-semantics", code="METHOD_SECTION_CONFLICT",
                    message=f"METHOD=QS but &MM section found. QS and MM are mutually exclusive.",
                )
        elif method == "FIST":
            if dft_section is not None:
                result.add_error(
                    source="cp2k-semantics", code="METHOD_SECTION_CONFLICT",
                    message=f"METHOD=FIST but &DFT section found. FIST and DFT are mutually exclusive.",
                    suggested_fix="Remove &DFT section or change METHOD to QS",
                )
        elif method == "NNP":
            if nnp_section is None:
                result.add_warning(
                    source="cp2k-semantics", code="METHOD_MISSING_SECTION",
                    message=f"METHOD=NNP but no &NNP section found.",
                    suggested_fix="Add &NNP section under &FORCE_EVAL",
                )
            if dft_section is not None:
                result.add_error(
                    source="cp2k-semantics", code="METHOD_SECTION_CONFLICT",
                    message=f"METHOD=NNP but &DFT section found. NNP and DFT are mutually exclusive.",
                )
        elif method == "EIP":
            if dft_section is not None:
                result.add_error(
                    source="cp2k-semantics", code="METHOD_SECTION_CONFLICT",
                    message=f"METHOD=EIP but &DFT section found.",
                )


def validate_dft_section(tree: dict, result: ValidationResult):
    """Issue #1 & #5: Validate DFT section for XC functional conflicts, SCF solver conflicts."""
    dft = _find_section(tree, "FORCE_EVAL", "DFT")
    if dft is None:
        return

    # Check for multiple XC functionals
    xc_section = dft.get("+xc")
    if xc_section is not None:
        xc_functional = xc_section.get("+xc_functional")
        if xc_functional is not None:
            if isinstance(xc_functional, dict):
                functional_names = list(xc_functional.keys())
            elif isinstance(xc_functional, list):
                functional_names = [list(f.keys())[0] if isinstance(f, dict) else str(f) for f in xc_functional]
            else:
                functional_names = []
            if len(functional_names) > 1:
                result.add_error(
                    source="cp2k-semantics", code="MULTIPLE_XC_FUNCTIONALS",
                    message=f"Multiple XC functionals defined: {', '.join(functional_names)}. "
                            "Only one XC functional should be specified.",
                    suggested_fix=f"Keep only one functional from: {', '.join(functional_names)}",
                )

    # Check for SCF solver conflicts (OT + DIAGONALIZATION)
    scf = dft.get("+scf")
    if scf is not None:
        ot = scf.get("+ot")
        diag = scf.get("+diagonalization")
        if ot is not None and diag is not None:
            result.add_error(
                source="cp2k-semantics", code="SCF_SOLVER_CONFLICT",
                message="Both &OT and &DIAGONALIZATION SCF solvers are specified. Choose one.",
                suggested_fix="Remove either &OT or &DIAGONALIZATION",
            )

        # SCF convergence warnings
        max_scf = scf.get("max_scf")
        if max_scf is not None:
            try:
                max_scf_val = int(str(max_scf).split()[0]) if isinstance(max_scf, (list, tuple)) else int(max_scf)
                if max_scf_val < 20:
                    result.add_warning(
                        source="cp2k-lint", code="LOW_MAX_SCF",
                        message=f"MAX_SCF={max_scf_val} is low and may cause convergence issues. Consider ≥ 20.",
                    )
            except (ValueError, TypeError):
                pass

        eps_scf = scf.get("eps_scf")
        if eps_scf is not None:
            try:
                eps_val = float(str(eps_scf).split()[0]) if isinstance(eps_scf, (list, tuple)) else float(eps_scf)
                if eps_val > 1.0e-5:
                    result.add_warning(
                        source="cp2k-lint", code="LOW_SCF_ACCURACY",
                        message=f"EPS_SCF={eps_val} is low accuracy. Consider ≤ 1.0E-5 for production runs.",
                    )
            except (ValueError, TypeError):
                pass

    # Check cutoff values
    mgrid = dft.get("+mgrid")
    if mgrid is not None:
        cutoff = mgrid.get("cutoff")
        if cutoff is not None:
            try:
                cutoff_val = float(str(cutoff).split()[0]) if isinstance(cutoff, (list, tuple)) else float(cutoff)
                if cutoff_val < 200:
                    result.add_error(
                        source="cp2k-semantics", code="CUTOFF_TOO_LOW",
                        message=f"CUTOFF={cutoff_val} Ry is too low. Minimum recommended is 200 Ry.",
                        suggested_fix="Increase CUTOFF to at least 200 Ry",
                    )
                elif cutoff_val < 300:
                    result.add_warning(
                        source="cp2k-lint", code="CUTOFF_LOW",
                        message=f"CUTOFF={cutoff_val} Ry is low. Recommended ≥ 300 Ry for accurate results.",
                        suggested_fix="Consider increasing CUTOFF to ≥ 300 Ry",
                    )
            except (ValueError, TypeError):
                pass

        rel_cutoff = mgrid.get("rel_cutoff")
        if rel_cutoff is not None:
            try:
                rel_val = float(str(rel_cutoff).split()[0]) if isinstance(rel_cutoff, (list, tuple)) else float(rel_cutoff)
                if rel_val < 30:
                    result.add_warning(
                        source="cp2k-lint", code="REL_CUTOFF_LOW",
                        message=f"REL_CUTOFF={rel_val} Ry is low. Recommended ≥ 30 Ry.",
                    )
            except (ValueError, TypeError):
                pass

    # Check KPOINTS for molecular (non-periodic) systems
    kpoints = dft.get("+kpoints")
    if kpoints is not None:
        poisson = dft.get("+poisson")
        periodic = None
        if poisson is not None:
            periodic = poisson.get("periodic")
            if isinstance(periodic, list):
                periodic = periodic[0]
        if periodic and str(periodic).upper() == "NONE":
            result.add_warning(
                source="cp2k-lint", code="KPOINTS_NON_PERIODIC",
                message="KPOINTS specified but POISSON PERIODIC=NONE. K-points are not useful for non-periodic systems.",
                suggested_fix="Remove &KPOINTS section or set POISSON PERIODIC appropriately",
            )


def validate_coordinates(tree: dict, result: ValidationResult):
    """Issue #5: Validate coordinate section for element symbols and basic structure."""
    subsys = _find_section(tree, "FORCE_EVAL", "SUBSYS")
    if subsys is None:
        return

    coord = subsys.get("+coord")
    if coord is None:
        return

    # Get coordinate lines (stored as "*" key)
    coord_lines = coord.get("*", [])
    if not isinstance(coord_lines, list):
        coord_lines = [coord_lines] if coord_lines else []

    atoms_found = set()
    for coordline in coord_lines:
        if isinstance(coordline, str):
            fields = coordline.split()
        elif hasattr(coordline, "split"):
            fields = str(coordline).split()
        else:
            fields = [str(coordline)] if coordline else []

        if len(fields) < 4:
            continue

        element = fields[0].rstrip("0123456789")
        if element not in ELEMENTS:
            # Check if it's a valid element with isotope number
            result.add_error(
                source="cp2k-semantics", code="INVALID_ELEMENT",
                message=f"Unknown element '{element}' in COORD section.",
                suggested_fix=f"Use a valid chemical element symbol",
            )
        atoms_found.add(element)

    # Check KIND definitions match coordinate atoms
    kinds = subsys.get("+kind")
    if kinds is not None:
        if isinstance(kinds, dict):
            kind_names = set(k.upper() for k in kinds.keys() if k != "_")
        elif isinstance(kinds, list):
            kind_names = set()
            for k in kinds:
                if isinstance(k, dict):
                    param = k.get("_")
                    if param:
                        kind_names.add(str(param).upper())
        else:
            kind_names = set()

        for atom in atoms_found:
            if atom.upper() not in kind_names:
                result.add_warning(
                    source="cp2k-semantics", code="MISSING_KIND",
                    message=f"No &KIND section defined for element '{atom}'. Default parameters will be used.",
                )


def validate_removed_deprecated_keywords(tree: dict, result: ValidationResult):
    """Issue #5: Detect removed and deprecated keywords."""

    def _scan_dict(d, path=""):
        if isinstance(d, dict):
            for key, val in d.items():
                clean_key = key.lstrip("+").upper()
                current_path = f"{path}/{clean_key}" if path else clean_key
                if clean_key in REMOVED_KEYWORDS:
                    result.add_error(
                        source="cp2k-semantics", code="REMOVED_KEYWORD",
                        message=f"Keyword '{clean_key}' has been removed in CP2K 2024.1.",
                        suggested_fix=f"Remove '{clean_key}' from input",
                    )
                if clean_key in DEPRECATED_KEYWORDS:
                    replacement = DEPRECATED_KEYWORDS[clean_key]
                    result.add_warning(
                        source="cp2k-lint", code="DEPRECATED_KEYWORD",
                        message=f"Keyword '{clean_key}' is deprecated. {replacement}",
                        suggested_fix=f"Consider replacing '{clean_key}'",
                    )
                _scan_dict(val, current_path)
        elif isinstance(d, list):
            for item in d:
                _scan_dict(item, path)

    _scan_dict(tree)


def validate_multipolespin(tree: dict, result: ValidationResult):
    """Issue #5: Check MULTIPLICITY vs UKS consistency."""
    dft = _find_section(tree, "FORCE_EVAL", "DFT")
    if dft is None:
        return

    mult = dft.get("multiplicity")
    uks = dft.get("uks")

    if mult is not None:
        try:
            mult_val = int(str(mult).split()[0]) if isinstance(mult, (list, tuple)) else int(mult)
            if mult_val > 1 and uks is not None:
                uks_val = str(uks).upper().split()[0] if isinstance(uks, (list, tuple)) else str(uks).upper()
                if uks_val in ("F", "FALSE", "FALS", "0"):
                    result.add_error(
                        source="cp2k-semantics", code="MULTIPLICITY_UKS_CONFLICT",
                        message=f"MULTIPLICITY={mult_val} requires open-shell (UKS=TRUE), but UKS=FALSE.",
                        suggested_fix="Set UKS TRUE or remove MULTIPLICITY",
                    )
        except (ValueError, TypeError):
            pass


def validate_md_parameters(tree: dict, result: ValidationResult):
    """Issue #5: Validate MD parameters."""
    md = _find_section(tree, "MOTION", "MD")
    if md is None:
        return

    ensemble = md.get("ensemble")
    if ensemble is None:
        return
    if isinstance(ensemble, list):
        ensemble = ensemble[0]
    ensemble = str(ensemble).upper()

    if "NPT" in ensemble:
        barostat = md.get("+barostat")
        if not barostat:
            result.add_warning(
                source="cp2k-lint", code="NPT_NO_BAROSTAT",
                message=f"ENSEMBLE={ensemble} but no &BAROSTAT section found.",
                suggested_fix="Add &BAROSTAT section under &MD",
            )

    if ensemble in ("NVT", "NPT", "NPT_I", "NPT_F"):
        thermostat = md.get("+thermostat")
        if not thermostat:
            result.add_warning(
                source="cp2k-lint", code="MD_NO_THERMOSTAT",
                message=f"ENSEMBLE={ensemble} but no &THERMOSTAT section found.",
                suggested_fix="Add &THERMOSTAT section under &MD",
            )

    timestep = md.get("timestep")
    if timestep is not None:
        try:
            ts_val = float(str(timestep).split()[0]) if isinstance(timestep, (list, tuple)) else float(timestep)
            if ts_val < 0.1 or ts_val > 2.0:
                result.add_warning(
                    source="cp2k-lint", code="TIMESTEP_OUT_OF_RANGE",
                    message=f"TIMESTEP={ts_val} fs is outside the typical range (0.1–2.0 fs).",
                )
        except (ValueError, TypeError):
            pass


def validate_geo_opt_parameters(tree: dict, result: ValidationResult):
    """Issue #5: Validate GEO_OPT parameters."""
    geo_opt = _find_section(tree, "MOTION", "GEO_OPT")
    if geo_opt is None:
        return

    max_iter = geo_opt.get("max_iter")
    if max_iter is not None:
        try:
            mi_val = int(str(max_iter).split()[0]) if isinstance(max_iter, (list, tuple)) else int(max_iter)
            if mi_val < 20:
                result.add_warning(
                    source="cp2k-lint", code="GEO_OPT_LOW_MAX_ITER",
                    message=f"GEO_OPT MAX_ITER={mi_val} is low. Convergence may not be reached.",
                    suggested_fix="Consider increasing MAX_ITER to ≥ 100",
                )
        except (ValueError, TypeError):
            pass

    optimizer = geo_opt.get("optimizer")
    if optimizer is not None:
        opt_val = str(optimizer).upper().split()[0] if isinstance(optimizer, (list, tuple)) else str(optimizer).upper()
        if opt_val == "BFGS":
            result.add_info = True  # informational, not actionable


def validate_cell_periodic(tree: dict, result: ValidationResult):
    """Issue #5: Check POISSON PERIODIC vs CELL PERIODIC consistency."""
    dft = _find_section(tree, "FORCE_EVAL", "DFT")
    if dft is None:
        return

    poisson = dft.get("+poisson")
    if poisson is None:
        return

    poisson_periodic = poisson.get("periodic")
    if poisson_periodic is None:
        return
    if isinstance(poisson_periodic, list):
        poisson_periodic = poisson_periodic[0]
    poisson_periodic = str(poisson_periodic).upper()

    subsys = _find_section(tree, "FORCE_EVAL", "SUBSYS")
    if subsys is None:
        return

    cell = subsys.get("+cell")
    if cell is None:
        return

    cell_periodic = cell.get("periodic")
    if cell_periodic is None:
        return
    if isinstance(cell_periodic, list):
        cell_periodic = cell_periodic[0]
    cell_periodic = str(cell_periodic).upper()

    if poisson_periodic != cell_periodic:
        result.add_warning(
            source="cp2k-semantics", code="PERIODIC_MISMATCH",
            message=f"POISSON PERIODIC={poisson_periodic} but CELL PERIODIC={cell_periodic}. "
                    "These should typically match.",
            suggested_fix=f"Set both to {cell_periodic} or {poisson_periodic}",
        )


def validate_file_references(tree: dict, result: ValidationResult):
    """Issue #5: Check if referenced files exist."""
    subsys = _find_section(tree, "FORCE_EVAL", "SUBSYS")
    if subsys is None:
        return

    for key in ("basis_set_file_name", "potential_file_name", "coord_file_name"):
        file_ref = subsys.get(key)
        if file_ref is None:
            continue
        if isinstance(file_ref, list):
            file_ref = file_ref[0]
        file_path = str(file_ref)
        # Skip if it looks like a placeholder or built-in name
        if not file_path.startswith("/") and not file_path.startswith("."):
            continue
        p = pathlib.Path(file_path)
        if not p.exists():
            result.add_warning(
                source="cp2k-lint", code="FILE_NOT_FOUND",
                message=f"Referenced file '{file_path}' ({key}) does not exist.",
            )


def validate(tree: dict) -> ValidationResult:
    """
    Run all semantic validation rules on a parsed CP2K input tree.

    :param tree: The nested dict produced by CP2KInputParser.parse()
    :return: ValidationResult with all diagnostics
    """
    result = ValidationResult()

    validate_removed_deprecated_keywords(tree, result)
    validate_run_type_motion_consistency(tree, result)
    validate_force_eval_method(tree, result)
    validate_dft_section(tree, result)
    validate_coordinates(tree, result)
    validate_multipolespin(tree, result)
    validate_md_parameters(tree, result)
    validate_geo_opt_parameters(tree, result)
    validate_cell_periodic(tree, result)
    validate_file_references(tree, result)

    return result
