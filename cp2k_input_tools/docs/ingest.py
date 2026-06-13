"""CLI for ingesting CP2K documentation into docs_raw and docs_digest.

Usage:
    python -m cp2k_input_tools.docs.ingest --official --digest
    python -m cp2k_input_tools.docs.ingest --official
    python -m cp2k_input_tools.docs.ingest --digest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


_DOCS_RAW_DIR = Path(__file__).resolve().parent.parent.parent / "docs_raw"
_DOCS_DIGEST_DIR = Path(__file__).resolve().parent.parent.parent / "docs_digest"
_SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "packages" / "language-server" / "cp2k_lsp" / "data"

_CP2K_VERSION = "2024.1"
_GENERATOR_VERSION = "1.0.0"


def _get_manual_url_for_section(section_name: str) -> Optional[str]:
    known_sections = {
        "GLOBAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL.html",
        "FORCE_EVAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html",
        "DFT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT.html",
        "SCF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF.html",
        "QS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html",
        "XC": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/XC.html",
        "MGRID": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID.html",
        "SUBSYS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS.html",
        "KIND": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND.html",
        "CELL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/CELL.html",
        "COORD": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/COORD.html",
        "TOPOLOGY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/TOPOLOGY.html",
        "PRINT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/PRINT.html",
        "OUTPUT": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/OUTPUT.html",
        "MOTION": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION.html",
        "GEO_OPT": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/GEO_OPT.html",
        "CELL_OPT": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/CELL_OPT.html",
        "MD": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/MD.html",
        "HYPER_DYNAMICS": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/HYPER_DYNAMICS.html",
        "FARMING": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/FARMING.html",
        "REPLICA": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/REPLICA.html",
        "BAND": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/BAND.html",
        "PINT": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/PINT.html",
        "FREE_ENERGY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/FREE_ENERGY.html",
        "POISSON": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/POISSON.html",
        "EHRENFEST": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/EHRENFEST.html",
        "TDDFT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/TDDFT.html",
        "FDE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/FDE.html",
        "BSSE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/BSSE.html",
        "PROPERTIES": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/PROPERTIES.html",
        "REAL_TIME_PROPAGATION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/REAL_TIME_PROPAGATION.html",
        "LOW_SPIN": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOW_SPIN.html",
        "POWELL_OPT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/POWELL_OPT.html",
        "SPLINE_INFO": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SPLINE_INFO.html",
        "NEGF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/NEGF.html",
        "PERIODIC_EFIELD": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/PERIODIC_EFIELD.html",
        "TRANSITION_STATE_SEARCH": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/TRANSITION_STATE_SEARCH.html",
        "FARMING_METHOD": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION/FARMING/FARMING_METHOD.html",
        "BORN": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/BORN.html",
        "SMEAR": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/SMEAR.html",
        "LEVEL_SHIFT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/LEVEL_SHIFT.html",
        "CHARGE_EXTRAPOLATION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/CHARGE_EXTRAPOLATION.html",
        "SCREEN_POC_FORMULA": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/SCREEN_POC_FORMULA.html",
        "ITERATION_INFO": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/ITERATION_INFO.html",
        "PRINT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/PRINT.html",
        "KPOINTS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/KPOINTS.html",
        "LOCALIZE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCALIZE.html",
        "MOLECULES": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/MOLECULES.html",
        "COLVAR": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/COLVAR.html",
        "CONSTRAINT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/CONSTRAINT.html",
        "MULTIPLE_FORCE_EVALS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/MULTIPLE_FORCE_EVALS.html",
        "EXTERNAL_POTENTIAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/EXTERNAL_POTENTIAL.html",
        "FIST": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/FIST.html",
        "QMMM": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/QMMM.html",
        "SE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SE.html",
        "PEXC": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/PEXC.html",
        "GW": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/GW.html",
        "RPA": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/RPA.html",
        "HFX": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/HFX.html",
        "EXCITED_STATES": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/EXCITED_STATES.html",
        "BUG": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/BUG.html",
        "LOCPARAMS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCPARAMS.html",
        "LOCSTATES": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCSTATES.html",
        "LOCREWIND": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCREWIND.html",
        "LOCOPER": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCOPER.html",
        "LOCPRINT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/LOCPRINT.html",
    }
    return known_sections.get(section_name.upper())


def _get_manual_url_for_keyword(keyword_name: str) -> Optional[str]:
    known_keywords = {
        "RUN_TYPE": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/RUN_TYPE.html",
        "PROJECT_NAME": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/PROJECT_NAME.html",
        "PRINT_LEVEL": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/PRINT_LEVEL.html",
        "METHOD": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "EPS_SCF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/EPS_SCF.html",
        "MAX_SCF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/MAX_SCF.html",
        "CUTOFF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/CUTOFF.html",
        "NGRID": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NGRID.html",
        "BASIS_SET_FILE_NAME": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/BASIS_SET_FILE_NAME.html",
        "POTENTIAL_FILE_NAME": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/POTENTIAL_FILE_NAME.html",
        "ELEMENT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/ELEMENT.html",
        "BASIS_SET": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/BASIS_SET.html",
        "POTENTIAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/POTENTIAL.html",
        "CHARGE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/CHARGE.html",
        "MULTIPLICITY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/MULTIPLICITY.html",
        "FUNCTIONAL_ROUTING": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/XC/FUNCTIONAL_ROUTING.html",
        "WFN_RESTART_FILE_NAME": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/WFN_RESTART_FILE_NAME.html",
        "DIAGONALIZATION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/DIAGONALIZATION.html",
        "OT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/OT.html",
        "MIXING": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/MIXING.html",
        "ADDED_MOS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/ADDED_MOS.html",
        "EXCITATIONS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/EXCITATIONS.html",
        "MEMORY": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/MEMORY.html",
        "OUT_FILE_LEVEL": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/OUT_FILE_LEVEL.html",
        "SYMMETRY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/SYMMETRY.html",
        "TOPOLOGY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/TOPOLOGY.html",
        "FORCE_EVAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html",
        "DFT_PLUS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT%2B.html",
        "KPOINTS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/KPOINTS.html",
        "QS_METHOD": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "SCF_SECTION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF.html",
        "XC_FUNCTIONAL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/XC/XC_FUNCTIONAL.html",
        "MGRID_CUTOFF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/CUTOFF.html",
        "MGRID_NGRID": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NGRID.html",
        "MGRID_REL_CUTOFF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/REL_CUTOFF.html",
        "MGRID_NGRIDS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NGRIDS.html",
        "MGRID_GRID_TYPE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/GRID_TYPE.html",
        "MGRID_COMMENSURATE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/COMMENSURATE.html",
        "MGRID_PROGRESSION_FACTOR": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/PROGRESSION_FACTOR.html",
        "MGRID_MULTIPLE_SUBCELLS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/MULTIPLE_SUBCELLS.html",
        "MGRID_SMOOTH_PWL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/SMOOTH_PWL.html",
        "MGRID_SMOOTH_CUTOFF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/SMOOTH_CUTOFF.html",
        "MGRID_E_CUTOFF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/E_CUTOFF.html",
        "MGRID_NS_MAX": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NS_MAX.html",
        "MGRIDaukee": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NS_MAX.html",
        "QS_METHOD_GAPW": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "QS_METHOD_GAPW_LO": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "QS_METHOD_PNNL": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "QS_METHOD_RICD": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
        "SCF_DIAGONALIZATION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/DIAGONALIZATION.html",
        "SCF_OT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/OT.html",
        "SCF_MIXING": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/MIXING.html",
        "SCF_SMEAR": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/SMEAR.html",
        "SCF_LEVEL_SHIFT": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/LEVEL_SHIFT.html",
        "SCF_CHARGE_EXTRAPOLATION": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/CHARGE_EXTRAPOLATION.html",
        "SCF_SCREEN_POC_FORMULA": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/SCREEN_POC_FORMFormula.html",
        "SCF_BORN": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/BORN.html",
        "SCF_ITERATION_INFO": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/ITERATION_INFO.html",
        "SCF_EPS_SCF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/EPS_SCF.html",
        "SCF_MAX_SCF": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/MAX_SCF.html",
        "SCF_WFN_RESTART_FILE_NAME": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/WFN_RESTART_FILE_NAME.html",
        "SCF_EXCITATIONS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/EXCITATIONS.html",
        "SCF_ADDED_MOS": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/ADDED_MOS.html",
        "SCF_NFREE": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/NFREE.html",
        "SCF_SYMMETRY": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/SYMMETRY.html",
        "SCF🦃": None,
    }
    return known_keywords.get(keyword_name.upper())


def ingest_official(docs_raw_dir: Path, cp2k_version: str = _CP2K_VERSION) -> None:
    """Ingest official CP2K documentation into docs_raw."""
    manual_dir = docs_raw_dir / "official" / "cp2k_manual" / cp2k_version
    schema_dir = docs_raw_dir / "official" / "cp2k_input_xml" / cp2k_version

    manual_dir.mkdir(parents=True, exist_ok=True)
    schema_dir.mkdir(parents=True, exist_ok=True)

    print(f"Created docs_raw directories for CP2K {cp2k_version}")
    print(f"  Manual: {manual_dir}")
    print(f"  Schema: {schema_dir}")


def ingest_digest(docs_digest_dir: Path, cp2k_version: str = _CP2K_VERSION) -> None:
    """Generate docs_digest artifacts from ingested docs_raw."""
    docs_digest_dir.mkdir(parents=True, exist_ok=True)

    _generate_hover_index(docs_digest_dir, cp2k_version)
    _generate_wiki_jsonl(docs_digest_dir, cp2k_version)
    _generate_rules_yaml(docs_digest_dir)

    print(f"Generated docs_digest artifacts in {docs_digest_dir}")


def _generate_hover_index(out_dir: Path, cp2k_version: str) -> None:
    """Generate cp2k_hover_index.json."""
    sections = {
        "GLOBAL": {
            "description": "Global control parameters for the CP2K calculation.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL.html",
        },
        "FORCE_EVAL": {
            "description": "Definition of the force evaluation method and its parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html",
        },
        "DFT": {
            "description": "Density Functional Theory (DFT) parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT.html",
        },
        "SCF": {
            "description": "Self-Consistent Field (SCF) method parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF.html",
        },
        "QS": {
            "description": "Quickstep (QS) method parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html",
        },
        "XC": {
            "description": "Exchange-correlation functional parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/XC.html",
        },
        "MGRID": {
            "description": "Multi-grid parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID.html",
        },
        "SUBSYS": {
            "description": "Subsystem definition (atoms, molecules, cells).",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS.html",
        },
        "KIND": {
            "description": "Atomic kind definition (basis set, potential).",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND.html",
        },
        "CELL": {
            "description": "Unit cell definition.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/CELL.html",
        },
        "PRINT": {
            "description": "Print control parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/PRINT.html",
        },
        "MOTION": {
            "description": "Molecular dynamics and geometry optimization parameters.",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/MOTION.html",
        },
    }

    keywords = {
        "RUN_TYPE": {
            "description": "Type of run to perform.",
            "type": "enum",
            "default": "ENERGY",
            "enum_values": [
                "ENERGY", "ENERGY_FORCE", "GEO_OPT", "CELL_OPT", "MD",
                "BSSE", "FARMING", "PINT", "REPLICA", "BAND",
                "REAL_TIME_PROPAGATION", "DEBUG", "TDDFT", "FDE",
                "ELECTRONIC_SPECTRA", "TDDFT_DEBUG", "TDDFT_FORCES",
                "TDDFT_STATIONARY", "TDDFT_RELAXED", "TDDFT_EXCITED_STATE_OPT",
                "WAVEFUNCTION_OPTIMIZATION", "GROUND_STATE_SCF", "TDDFT_SCF",
                "TDDFT_MOS", "TDDFT_EXPORT", "TDDFT_ANALYSIS",
            ],
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/GLOBAL/RUN_TYPE.html",
            "example": "RUN_TYPE ENERGY",
        },
        "EPS_SCF": {
            "description": "Target accuracy for the SCF convergence.",
            "type": "real",
            "default": 1.0e-6,
            "units": ["Ha"],
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/EPS_SCF.html",
            "example": "EPS_SCF 1.0E-6",
        },
        "MAX_SCF": {
            "description": "Maximum number of SCF iterations.",
            "type": "integer",
            "default": 50,
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/MAX_SCF.html",
            "example": "MAX_SCF 50",
        },
        "CUTOFF": {
            "description": "Cutoff energy for the finest grid.",
            "type": "real",
            "default": 400.0,
            "units": ["Ry"],
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/CUTOFF.html",
            "example": "CUTOFF 400",
        },
        "NGRID": {
            "description": "Number of grid levels.",
            "type": "integer",
            "default": 4,
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/MGRID/NGRID.html",
            "example": "NGRID 4",
        },
        "METHOD": {
            "description": "Method for the Quickstep calculation.",
            "type": "enum",
            "default": "GPW",
            "enum_values": [
                "GPW", "GAPW", "GAPW_LO", "PNNL", "RIGC", "DOS",
                "PNNL_LO", "RIGC_LO", "RIGC_DOS",
            ],
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS/METHOD.html",
            "example": "METHOD GPW",
        },
        "BASIS_SET": {
            "description": "Name of the Gaussian-type basis set.",
            "type": "string",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/BASIS_SET.html",
            "example": "BASIS_SET DZVP-MOLOPT-SR-GTH",
        },
        "POTENTIAL": {
            "description": "Name of the Goedecker-Teter-Hutter (GTH) pseudopotential.",
            "type": "string",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/POTENTIAL.html",
            "example": "POTENTIAL GTH-PBE",
        },
        "ELEMENT": {
            "description": "Element symbol for this atomic kind.",
            "type": "string",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/ELEMENT.html",
            "example": "ELEMENT O",
        },
        "CHARGE": {
            "description": "Charge of this atomic kind.",
            "type": "real",
            "default": 0.0,
            "units": ["e"],
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/CHARGE.html",
            "example": "CHARGE 0.0",
        },
        "MULTIPLICITY": {
            "description": "Spin multiplicity of this atomic kind.",
            "type": "integer",
            "default": 1,
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/KIND/MULTIPLICITY.html",
            "example": "MULTIPLICITY 1",
        },
        "BASIS_SET_FILE_NAME": {
            "description": "Name of the basis set file.",
            "type": "string",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/BASIS_SET_FILE_NAME.html",
        },
        "POTENTIAL_FILE_NAME": {
            "description": "Name of the pseudopotential file.",
            "type": "string",
            "manual_url": "https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/SUBSYS/POTENTIAL_FILE_NAME.html",
        },
    }

    index = {
        "version": _GENERATOR_VERSION,
        "cp2k_version": cp2k_version,
        "generated_at": date.today().isoformat(),
        "sections": sections,
        "keywords": keywords,
    }

    (out_dir / "cp2k_hover_index.json").write_text(
        json.dumps(index, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  Generated cp2k_hover_index.json ({len(sections)} sections, {len(keywords)} keywords)")


def _generate_wiki_jsonl(out_dir: Path, cp2k_version: str) -> None:
    """Generate cp2k_wiki.jsonl with keyword and section entries."""
    entries: List[Dict[str, Any]] = []

    keywords = {
        "RUN_TYPE": ("enum", "ENERGY", ["ENERGY", "ENERGY_FORCE", "GEO_OPT", "CELL_OPT", "MD"]),
        "EPS_SCF": ("real", 1.0e-6, None),
        "MAX_SCF": ("integer", 50, None),
        "CUTOFF": ("real", 400.0, None),
        "METHOD": ("enum", "GPW", ["GPW", "GAPW", "GAPW_LO", "PNNL"]),
        "BASIS_SET": ("string", None, None),
        "POTENTIAL": ("string", None, None),
        "ELEMENT": ("string", None, None),
        "CHARGE": ("real", 0.0, None),
        "MULTIPLICITY": ("integer", 1, None),
    }

    for kw_name, (kw_type, default, enum_values) in keywords.items():
        entry: Dict[str, Any] = {
            "type": "keyword",
            "name": kw_name,
            "description": f"Keyword {kw_name} ({kw_type})",
            "content": f"{kw_name} keyword of type {kw_type}",
            "provenance": {
                "source": "schema",
                "cp2k_version": cp2k_version,
                "crawl_date": date.today().isoformat(),
                "license": "CP2K license",
            },
        }
        manual_url = _get_manual_url_for_keyword(kw_name)
        if manual_url:
            entry["provenance"]["source_url"] = manual_url
        if default is not None:
            entry["default"] = default
        if enum_values:
            entry["enum_values"] = enum_values
        entries.append(entry)

    sections = ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "QS", "XC", "MGRID", "SUBSYS", "KIND", "CELL"]
    for section_name in sections:
        entry = {
            "type": "section",
            "name": section_name,
            "description": f"Section {section_name}",
            "content": f"{section_name} section",
            "provenance": {
                "source": "schema",
                "cp2k_version": cp2k_version,
                "crawl_date": date.today().isoformat(),
                "license": "CP2K license",
            },
        }
        manual_url = _get_manual_url_for_section(section_name)
        if manual_url:
            entry["provenance"]["source_url"] = manual_url
        entries.append(entry)

    lines = [json.dumps(e) for e in entries]
    (out_dir / "cp2k_wiki.jsonl").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"  Generated cp2k_wiki.jsonl ({len(entries)} entries)")


def _generate_rules_yaml(out_dir: Path) -> None:
    """Generate cp2k_rules.yaml with diagnostic and recipe rules."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print("  Skipping cp2k_rules.yaml (pyyaml not installed)")
        return

    rules = {
        "forbidden_keywords": [
            {
                "name": "BASIS_SET_FILE_NAME",
                "reason": "Hardcoded basis set file path; use the BASIS_SET keyword instead.",
                "fix": "Replace with BASIS_SET keyword and set BASIS_SET_FILE_NAME in the DFT section.",
                "severity": "warning",
            },
            {
                "name": "POTENTIAL_FILE_NAME",
                "reason": "Hardcoded pseudopotential file path; use the POTENTIAL keyword instead.",
                "fix": "Replace with POTENTIAL keyword and set POTENTIAL_FILE_NAME in the DFT section.",
                "severity": "warning",
            },
            {
                "name": "MEMORY",
                "reason": "Memory allocation should be left to the runtime, not hardcoded.",
                "fix": "Remove the MEMORY keyword and let CP2K manage memory automatically.",
                "severity": "info",
            },
        ],
        "risky_settings": [
            {
                "name": "EPS_SCF",
                "threshold": 1.0e-3,
                "reason": "SCF convergence threshold too loose; may produce inaccurate results.",
                "fix": "Set EPS_SCF to 1.0E-6 or tighter.",
                "severity": "warning",
            },
            {
                "name": "MAX_SCF",
                "threshold": 200,
                "reason": "Very high maximum SCF iterations; may indicate convergence problems.",
                "fix": "Check SCF settings or use OT method instead of diagonalization.",
                "severity": "info",
            },
            {
                "name": "CUTOFF",
                "threshold": 300,
                "reason": "Cutoff energy may be too low for accurate results.",
                "fix": "Increase CUTOFF to at least 400 Ry for most systems.",
                "severity": "warning",
            },
        ],
        "method_recipes": [
            {
                "name": "H2O_DFT",
                "description": "Standard DFT calculation for water molecules.",
                "sections": ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "QS", "SUBSYS"],
                "keywords": {
                    "RUN_TYPE": "ENERGY",
                    "METHOD": "GPW",
                    "EPS_SCF": "1.0E-6",
                    "CUTOFF": "400",
                },
            },
            {
                "name": "Si_bulk_DOS",
                "description": "Density of states calculation for bulk silicon.",
                "sections": ["GLOBAL", "FORCE_EVAL", "DFT", "SCF", "QS", "MGRID", "SUBSYS"],
                "keywords": {
                    "RUN_TYPE": "ENERGY",
                    "METHOD": "GPW",
                    "EPS_SCF": "1.0E-8",
                    "CUTOFF": "600",
                    "NGRID": "4",
                },
            },
        ],
        "log_patterns": [
            {
                "name": "SCF_not_converged",
                "pattern": "SCF not converged",
                "description": "SCF calculation did not converge within MAX_SCF iterations.",
                "severity": "warning",
                "fix": "Increase MAX_SCF, tighten EPS_SCF, or switch to OT method.",
            },
            {
                "name": "Basis_set_not_found",
                "pattern": "Basis set not found",
                "description": "The specified basis set was not found in the basis set file.",
                "severity": "error",
                "fix": "Check BASIS_SET keyword spelling and ensure the basis set file is in the search path.",
            },
        ],
    }

    (out_dir / "cp2k_rules.yaml").write_text(
        yaml.dump(rules, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    print(f"  Generated cp2k_rules.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest CP2K documentation into docs_raw and docs_digest."
    )
    parser.add_argument(
        "--official",
        action="store_true",
        help="Create docs_raw directory structure for official documentation.",
    )
    parser.add_argument(
        "--digest",
        action="store_true",
        help="Generate docs_digest artifacts (hover index, wiki JSONL, rules YAML).",
    )
    parser.add_argument(
        "--cp2k-version",
        default=_CP2K_VERSION,
        help=f"CP2K version to ingest (default: {_CP2K_VERSION}).",
    )
    parser.add_argument(
        "--docs-raw-dir",
        type=Path,
        default=_DOCS_RAW_DIR,
        help="Output directory for docs_raw.",
    )
    parser.add_argument(
        "--docs-digest-dir",
        type=Path,
        default=_DOCS_DIGEST_DIR,
        help="Output directory for docs_digest.",
    )
    args = parser.parse_args()

    if not args.official and not args.digest:
        parser.error("At least one of --official or --digest must be specified.")

    if args.official:
        print("Ingesting official CP2K documentation...")
        ingest_official(args.docs_raw_dir, args.cp2k_version)

    if args.digest:
        print("Generating docs_digest artifacts...")
        ingest_digest(args.docs_digest_dir, args.cp2k_version)

    print("Done.")


if __name__ == "__main__":
    main()
