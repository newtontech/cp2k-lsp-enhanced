"""Tests for the agent_inspect CLI commands."""

import json
import os
import pathlib
import tempfile

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.agent_inspect import cli as agent_cli


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
  METHOD QS
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


def test_inspect_diagnostics_valid(valid_inp_file, runner):
    result = runner.invoke(agent_cli, ["inspect", "diagnostics", valid_inp_file])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "file" in data
    assert "diagnostics" in data
    assert isinstance(data["diagnostics"], list)
    assert "error_count" in data
    assert "warning_count" in data


def test_inspect_diagnostics_broken(broken_inp_file, runner):
    result = runner.invoke(agent_cli, ["inspect", "diagnostics", broken_inp_file])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Broken file should have diagnostics
    assert isinstance(data["diagnostics"], list)


def test_inspect_diagnostics_fail_on_error(broken_inp_file, runner):
    result = runner.invoke(agent_cli, ["inspect", "diagnostics", broken_inp_file, "--fail-on-error"])
    # Should exit non-zero when errors found
    assert result.exit_code != 0


def test_inspect_diagnostics_json_schema(valid_inp_file, runner):
    """Verify the JSON schema is stable and contains expected fields."""
    result = runner.invoke(agent_cli, ["inspect", "diagnostics", valid_inp_file])
    assert result.exit_code == 0
    data = json.loads(result.output)

    # Top-level fields
    assert "file" in data
    assert "diagnostics" in data
    assert "error_count" in data
    assert "warning_count" in data

    for diag in data["diagnostics"]:
        assert "severity" in diag
        assert "source" in diag
        assert "code" in diag
        assert "message" in diag
        assert "range" in diag
        assert diag["severity"] in ("error", "warning", "info")


def test_inspect_format_preview(valid_inp_file, runner):
    result = runner.invoke(agent_cli, ["inspect", "format-preview", valid_inp_file])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "formatted" in data
    assert "file" in data
    assert len(data["formatted"]) > 0


def test_inspect_references_set_var(runner):
    content = """\
@SET MY_VAR 42
&GLOBAL
  PROJECT $MY_VAR
&END GLOBAL
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(content)
        f.flush()
        # Line 1: @SET MY_VAR 42
        result = runner.invoke(agent_cli, ["inspect", "references", f.name, "--line", "1", "--character", "6"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "references" in data
        assert data["count"] >= 2  # At least the SET line and the usage

    os.unlink(f.name)


def test_inspect_code_actions(runner):
    content = """\
&GLOBAL
  PROJECT test
&END GLOBAL
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(content)
        f.flush()
        result = runner.invoke(agent_cli, ["inspect", "code-actions", f.name, "--line", "3", "--character", "4"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "actions" in data
        assert "count" in data
        assert isinstance(data["actions"], list)

    os.unlink(f.name)


def test_diagnostics_delta(runner):
    before = {"file": "test.inp", "diagnostics": [{"message": "Error A"}, {"message": "Error B"}]}
    after = {"file": "test.inp", "diagnostics": [{"message": "Error A"}, {"message": "Error C"}]}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as bf:
        json.dump(before, bf)
        bf.flush()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as af:
            json.dump(after, af)
            af.flush()

            result = runner.invoke(agent_cli, ["inspect", "diagnostics-delta", bf.name, af.name])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["before_count"] == 2
            assert data["after_count"] == 2
            assert data["fixed_count"] == 1  # Error B was fixed
            assert data["new_count"] == 1  # Error C is new
            assert data["unchanged_count"] == 1  # Error A unchanged

        os.unlink(af.name)
    os.unlink(bf.name)
