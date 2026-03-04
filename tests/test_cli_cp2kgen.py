"""Tests for cp2kgen CLI tool."""
import io
import json
import pathlib
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.cp2kgen import cp2kgen


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


class TestCp2kgen:
    def test_basic_generation(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-"], input=sample_input)

            assert result.exit_code == 0
            MockParser.assert_called_once()
            mock_parser.parse.assert_called_once()

    def test_with_expressions_cartesian(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator, \
             patch("pathlib.Path.open", mock_open()) as mock_file:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "global/run_type=[ENERGY,GEO_OPT]"], input=sample_input)

            assert result.exit_code == 0
            assert "Writing" in result.output

    def test_with_expressions_zip(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator, \
             patch("pathlib.Path.open", mock_open()) as mock_file:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "--zip", "global/run_type=[ENERGY,GEO_OPT]"], input=sample_input)

            assert result.exit_code == 0

    def test_canonical_mode(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParser") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["--canonical", "-"], input=sample_input)

            assert result.exit_code == 0
            MockParser.assert_called_once()

    def test_invalid_expression_format(self, sample_input):
        runner = CliRunner()

        result = runner.invoke(cp2kgen, ["-", "invalid_expression"], input=sample_input)

        assert result.exit_code != 0
        assert "expression must be of the form" in str(result.exception) or "expression must be of the form" in result.output

    def test_with_var_values(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "-E", "VAR1=value1", "-E", "VAR2=value2"], input=sample_input)

            assert result.exit_code == 0
            mock_parser.parse.assert_called_once()

    def test_base_dir_option(self, sample_input, parsed_tree, tmp_path):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "-b", str(tmp_path)], input=sample_input)

            assert result.exit_code == 0

    def test_single_value_expression(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator, \
             patch("pathlib.Path.open", mock_open()) as mock_file:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "global/project_name=newname"], input=sample_input)

            assert result.exit_code == 0

    def test_nested_path_expression(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.cp2kgen.CP2KInputParserSimplified") as MockParser, \
             patch("cp2k_input_tools.cli.cp2kgen.CP2KInputGenerator") as MockGenerator, \
             patch("pathlib.Path.open", mock_open()) as mock_file:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_gen = MagicMock()
            mock_gen.line_iter.return_value = ["&GLOBAL", "  PROJECT_NAME test", "&END GLOBAL"]
            MockGenerator.return_value = mock_gen

            result = runner.invoke(cp2kgen, ["-", "force_eval/0/method=DFT"], input=sample_input)

            assert result.exit_code == 0
