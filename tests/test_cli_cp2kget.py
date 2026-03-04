"""Tests for cp2kget CLI tool."""
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.cp2kget import cp2kget


@pytest.fixture
def sample_input():
    return """&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD Quickstep
&END FORCE_EVAL
"""


@pytest.fixture
def parsed_tree():
    return {
        "global": {"project_name": "test", "run_type": "ENERGY"},
        "force_eval": [{"method": "Quickstep"}],
    }


class TestCp2kget:
    def test_basic_get(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "global/project_name"], input=sample_input)

            assert result.exit_code == 0
            assert "test" in result.output
            MockParser.assert_called_once()

    def test_get_multiple_paths(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "global/project_name", "global/run_type"], input=sample_input)

            assert result.exit_code == 0
            assert "test" in result.output
            assert "ENERGY" in result.output

    def test_get_list_value(self, sample_input, parsed_tree):
        runner = CliRunner()

        tree_with_list = {
            "global": {"project_name": "test", "run_type": "ENERGY"},
            "force_eval": [{"method": "Quickstep"}, {"method": "GPW"}],
        }

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = tree_with_list
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "force_eval"], input=sample_input)

            assert result.exit_code == 0
            assert "Quickstep" in result.output
            assert "GPW" in result.output

    def test_canonical_mode(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParser") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["--canonical", "-", "global/project_name"], input=sample_input)

            assert result.exit_code == 0
            MockParser.assert_called_once()

    def test_with_var_values(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "-E", "VAR1=value1", "global/project_name"], input=sample_input)

            assert result.exit_code == 0
            mock_parser.parse.assert_called_once()

    def test_with_base_dir(self, sample_input, parsed_tree, tmp_path):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "-b", str(tmp_path), "global/project_name"], input=sample_input)

            assert result.exit_code == 0

    def test_get_nested_path(self, sample_input, parsed_tree):
        runner = CliRunner()

        tree_nested = {
            "global": {"project_name": "test", "run_type": "ENERGY"},
            "force_eval": [
                {
                    "method": "Quickstep",
                    "dft": {
                        "basis_set_file_name": "BASIS_SETS"
                    }
                }
            ],
        }

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = tree_nested
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "force_eval/0/dft/basis_set_file_name"], input=sample_input)

            assert result.exit_code == 0
            assert "BASIS_SETS" in result.output

    def test_get_array_index(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kget.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(cp2kget, ["-", "force_eval/0/method"], input=sample_input)

            assert result.exit_code == 0
            assert "Quickstep" in result.output

    def test_no_paths_specified(self, sample_input):
        runner = CliRunner()

        result = runner.invoke(cp2kget, ["-"], input=sample_input)

        assert result.exit_code == 0
