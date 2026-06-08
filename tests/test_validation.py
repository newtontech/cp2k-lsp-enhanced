"""Tests for semantic validation engine."""

import pathlib

import pytest

from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.validator import (
    ELEMENTS,
    ValidationResult,
    validate,
    validate_coordinates,
    validate_dft_section,
    validate_force_eval_method,
    validate_md_parameters,
    validate_removed_deprecated_keywords,
    validate_run_type_motion_consistency,
)

TEST_DIR = pathlib.Path(__file__).resolve().parent
INPUTS_DIR = TEST_DIR / "inputs"


def parse_input(filename):
    """Parse a test input file and return the tree."""
    parser = CP2KInputParser()
    with open(INPUTS_DIR / filename, "r") as f:
        return parser.parse(f)


def get_diagnostic_codes(result: ValidationResult):
    """Get set of diagnostic codes from a result."""
    return {d.code for d in result.diagnostics}


# --- Issue #3: RUN_TYPE/MOTION consistency ---

class TestRunTypeMotionConsistency:
    def test_energy_with_geo_opt_error(self):
        tree = parse_input("validation_energy_geo_opt.inp")
        result = validate(tree)
        codes = get_diagnostic_codes(result)
        assert "RUN_TYPE_MOTION_MISMATCH" in codes

    def test_md_without_geo_opt_no_error(self):
        """MD run type should not trigger GEO_OPT error."""
        tree = {
            "+global": {"run_type": "MD"},
            "+motion": {"+md": {"ensemble": "NVT"}},
        }
        result = ValidationResult()
        validate_run_type_motion_consistency(tree, result)
        error_codes = {d.code for d in result.errors}
        assert "RUN_TYPE_MOTION_MISMATCH" not in error_codes

    def test_static_run_type_with_md_error(self):
        """ENERGY run type with &MD section should error."""
        tree = {
            "+global": {"run_type": "ENERGY"},
            "+motion": {"+md": {"ensemble": "NVT"}},
        }
        result = ValidationResult()
        validate_run_type_motion_consistency(tree, result)
        error_codes = {d.code for d in result.errors}
        assert "RUN_TYPE_MOTION_MISMATCH" in error_codes


# --- Issue #1: FORCE_EVAL method conflicts ---

class TestForceEvalMethod:
    def test_qs_with_fist_error(self):
        """QS method with &FIST section should produce METHOD_SECTION_CONFLICT."""
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {"+xc": {"+xc_functional": {"pbe": {}}}},
                "+fist": {"+nonbonded": {}},
            }]
        }
        result = ValidationResult()
        validate_force_eval_method(tree, result)
        codes = get_diagnostic_codes(result)
        assert "METHOD_SECTION_CONFLICT" in codes

    def test_fist_with_dft_error(self):
        """FIST method with &DFT section should produce METHOD_SECTION_CONFLICT."""
        tree = {
            "+force_eval": [{
                "method": "FIST",
                "+dft": {"+xc": {"+xc_functional": {"pbe": {}}}},
                "+fist": {},
            }]
        }
        result = ValidationResult()
        validate_force_eval_method(tree, result)
        codes = get_diagnostic_codes(result)
        assert "METHOD_SECTION_CONFLICT" in codes

    def test_qs_no_conflict(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {},
            }]
        }
        result = ValidationResult()
        validate_force_eval_method(tree, result)
        assert not result.errors


# --- Issue #5: Removed/deprecated keywords ---

class TestRemovedDeprecatedKeywords:
    def test_removed_keyword_detected(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "single_precision_matrices": "TRUE",
            }]
        }
        result = ValidationResult()
        validate_removed_deprecated_keywords(tree, result)
        codes = get_diagnostic_codes(result)
        assert "REMOVED_KEYWORD" in codes

    def test_no_removed_keywords(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {"+xc": {"+xc_functional": {"pbe": {}}}},
            }]
        }
        result = ValidationResult()
        validate_removed_deprecated_keywords(tree, result)
        assert not result.diagnostics


# --- Issue #5: DFT section validation ---

class TestDftSection:
    def test_multiple_xc_functionals_error(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {
                    "+xc": {
                        "+xc_functional": {"pbe": {}, "b3lyp": {}},
                    },
                },
            }]
        }
        result = ValidationResult()
        validate_dft_section(tree, result)
        codes = get_diagnostic_codes(result)
        assert "MULTIPLE_XC_FUNCTIONALS" in codes

    def test_scf_solver_conflict(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {
                    "+scf": {
                        "+ot": {},
                        "+diagonalization": {},
                    },
                    "+xc": {"+xc_functional": {"pbe": {}}},
                },
            }]
        }
        result = ValidationResult()
        validate_dft_section(tree, result)
        codes = get_diagnostic_codes(result)
        assert "SCF_SOLVER_CONFLICT" in codes

    def test_low_cutoff_error(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {
                    "+mgrid": {"cutoff": 50},
                    "+xc": {"+xc_functional": {"pbe": {}}},
                },
            }]
        }
        result = ValidationResult()
        validate_dft_section(tree, result)
        codes = get_diagnostic_codes(result)
        assert "CUTOFF_TOO_LOW" in codes

    def test_low_max_scf_warning(self):
        tree = {
            "+force_eval": [{
                "method": "QS",
                "+dft": {
                    "+scf": {"max_scf": 10},
                    "+xc": {"+xc_functional": {"pbe": {}}},
                },
            }]
        }
        result = ValidationResult()
        validate_dft_section(tree, result)
        codes = get_diagnostic_codes(result)
        assert "LOW_MAX_SCF" in codes


# --- Issue #5: Coordinate validation ---

class TestCoordinateValidation:
    def test_invalid_element(self):
        tree = parse_input("validation_multi_errors.inp")
        result = validate(tree)
        codes = get_diagnostic_codes(result)
        assert "INVALID_ELEMENT" in codes

    def test_valid_elements(self):
        tree = {
            "+force_eval": [{
                "+subsys": {
                    "+coord": {
                        "*": ["O  0.0  0.0  0.0", "H  0.9  0.0  0.0"],
                    },
                },
            }]
        }
        result = ValidationResult()
        validate_coordinates(tree, result)
        error_codes = {d.code for d in result.errors}
        assert "INVALID_ELEMENT" not in error_codes


# --- Issue #5: MD parameter validation ---

class TestMdParameters:
    def test_nvt_no_thermostat_warning(self):
        tree = {
            "+motion": {
                "+md": {"ensemble": "NVT"},
            },
        }
        result = ValidationResult()
        validate_md_parameters(tree, result)
        codes = get_diagnostic_codes(result)
        assert "MD_NO_THERMOSTAT" in codes

    def test_npt_no_barostat_warning(self):
        tree = {
            "+motion": {
                "+md": {"ensemble": "NPT_I"},
            },
        }
        result = ValidationResult()
        validate_md_parameters(tree, result)
        codes = get_diagnostic_codes(result)
        assert "NPT_NO_BAROSTAT" in codes

    def test_bad_timestep_warning(self):
        tree = {
            "+motion": {
                "+md": {"ensemble": "NVT", "timestep": 5.0},
            },
        }
        result = ValidationResult()
        validate_md_parameters(tree, result)
        codes = get_diagnostic_codes(result)
        assert "TIMESTEP_OUT_OF_RANGE" in codes


# --- Integration tests ---

class TestFullValidation:
    def test_multi_error_file(self):
        tree = parse_input("validation_multi_errors.inp")
        result = validate(tree)
        codes = get_diagnostic_codes(result)
        # Should catch: multiple XC, SCF conflict, low cutoff, invalid element
        assert "MULTIPLE_XC_FUNCTIONALS" in codes
        assert "SCF_SOLVER_CONFLICT" in codes
        assert "CUTOFF_TOO_LOW" in codes
        assert "INVALID_ELEMENT" in codes

    def test_valid_file_no_errors(self):
        """A properly structured input should have minimal errors."""
        tree = {
            "+global": {"run_type": "ENERGY"},
            "+force_eval": [{
                "method": "QS",
                "+dft": {
                    "+xc": {"+xc_functional": {"pbe": {}}},
                    "+scf": {"max_scf": 50, "eps_scf": 1e-6},
                    "+mgrid": {"cutoff": 400, "rel_cutoff": 40},
                    "+subsys": {
                        "+coord": {"*": ["O  0.0  0.0  0.0"]},
                        "+kind": {"O": {"basis_set": "DZVP", "potential": "GTH-PBE"}},
                    },
                },
            }],
        }
        result = validate(tree)
        # Should have no errors (warnings are OK)
        assert not result.errors

    def test_removed_keyword_integration(self):
        tree = {
            "+global": {"run_type": "ENERGY"},
            "+force_eval": [{
                "method": "QS",
                "single_precision_matrices": "TRUE",
            }],
        }
        result = validate(tree)
        codes = get_diagnostic_codes(result)
        assert "REMOVED_KEYWORD" in codes
