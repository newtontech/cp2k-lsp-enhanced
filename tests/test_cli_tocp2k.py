"""Tests for tocp2k CLI tool."""
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.tocp2k import tocp2k


class TestTocp2k:
    def test_json_input(self):
        runner = CliRunner()

        input_tree = {
            "global": {
                "project_name": "test",
                "run_type": "ENERGY"
            }
        }

        with patch("cp2k_input_tools.cli.tocp2k.CP2KInputGenerator") as MockGenerator:
            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "  RUN_TYPE ENERGY", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(tocp2k, ["-"], input=json.dumps(input_tree))

            assert result.exit_code == 0
            assert "&GLOBAL" in result.output

    def test_yaml_input(self):
        runner = CliRunner()
        yaml_content = """
global:
  project_name: test
  run_type: ENERGY
"""

        with patch("cp2k_input_tools.cli.tocp2k.CP2KInputGenerator") as MockGenerator, \
             patch("ruamel.yaml.YAML") as MockYAML:

            mock_yaml = MagicMock()
            mock_yaml.load.return_value = {"global": {"project_name": "test", "run_type": "ENERGY"}}
            MockYAML.return_value = mock_yaml

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "  RUN_TYPE ENERGY", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(tocp2k, ["--yaml", "-"], input=yaml_content)

            assert result.exit_code == 0

    def test_empty_tree(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.tocp2k.CP2KInputGenerator") as MockGenerator:
            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = []
            MockGenerator.return_value = mock_gen

            result = runner.invoke(tocp2k, ["-"], input="{}")

            assert result.exit_code == 0

    def test_complex_tree(self):
        runner = CliRunner()

        input_tree = {
            "global": {"project_name": "complex_test"},
            "force_eval": {
                "method": "Quickstep",
                "dft": {
                    "basis_set_file_name": "BASIS_SETS"
                }
            }
        }

        with patch("cp2k_input_tools.cli.tocp2k.CP2KInputGenerator") as MockGenerator:
            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = [
                "&GLOBAL",
                "  PROJECT_NAME complex_test",
                "&END GLOBAL",
                "&FORCE_EVAL",
                "  METHOD Quickstep",
                "  &DFT",
                "    BASIS_SET_FILE_NAME BASIS_SETS",
                "  &END DFT",
                "&END FORCE_EVAL"
            ]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(tocp2k, ["-"], input=json.dumps(input_tree))

            assert result.exit_code == 0
