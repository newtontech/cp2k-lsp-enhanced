"""Tests for the validate CLI command."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.validate import cp2k_validate


# Minimal valid CP2K input
VALID_INPUT = """\
&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    &QS
      EPS_DEFAULT 1.0E-10
    &END QS
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &COORD
      O 0.0 0.0 0.0
      H 0.757 0.586 0.0
      H -0.757 0.586 0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def valid_inp_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(VALID_INPUT)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def broken_inp_file():
    content = """\
&GLOBAL
  PROJECT test
&END GLOBAL

&FORCE_EVAL
  &DFT
    UNKNOWN_KEYWORD value
  &END DFT
&END FORCE_EVAL
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


def test_validate_human_output(valid_inp_file, runner):
    result = runner.invoke(cp2k_validate, [valid_inp_file])
    assert result.exit_code == 0
    assert "File:" in result.output
    assert "Parser valid:" in result.output


def test_validate_json_output(valid_inp_file, runner):
    result = runner.invoke(cp2k_validate, [valid_inp_file, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "file" in data
    assert "parser_valid" in data
    assert "diagnostics" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert data["parser_valid"] is True
    assert data["error_count"] == 0


def test_validate_broken_file(broken_inp_file, runner):
    result = runner.invoke(cp2k_validate, [broken_inp_file, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["parser_valid"] is False
    assert data["error_count"] > 0


def test_validate_fail_on_error(broken_inp_file, runner):
    result = runner.invoke(cp2k_validate, [broken_inp_file, "--fail-on-error"])
    assert result.exit_code != 0


def test_validate_dry_run_warning(valid_inp_file, runner):
    """Dry-run should warn about missing CP2K binary."""
    result = runner.invoke(cp2k_validate, [valid_inp_file, "--dry-run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Should have a warning about CP2K not found
    sources = [d["source"] for d in data["diagnostics"]]
    assert "cp2k-dryrun" in sources


def test_validate_json_diagnostics_schema(valid_inp_file, runner):
    """Verify diagnostics have consistent JSON schema."""
    result = runner.invoke(cp2k_validate, [valid_inp_file, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)

    for diag in data["diagnostics"]:
        assert "severity" in diag
        assert "source" in diag
        assert "code" in diag
        assert "message" in diag
        assert "range" in diag
        rng = diag["range"]
        assert "start_line" in rng
        assert "start_col" in rng
        assert "end_line" in rng
        assert "end_col" in rng
