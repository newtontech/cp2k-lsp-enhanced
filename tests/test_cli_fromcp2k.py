"""Tests for fromcp2k CLI tool."""
import json
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.fromcp2k import fromcp2k, Trafos


@pytest.fixture
def sample_input():
    return """&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
"""


@pytest.fixture
def parsed_tree():
    return {
        "global": {"project_name": "test", "run_type": "ENERGY"},
    }


class TestFromcp2k:
    def test_json_output(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(fromcp2k, ["-"], input=sample_input)

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["global"]["project_name"] == "test"

    def test_yaml_output(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserSimplified") as MockParser, \
             patch("ruamel.yaml.YAML") as MockYAML:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(fromcp2k, ["--format", "yaml", "-"], input=sample_input)

            assert result.exit_code == 0

    def test_canonical_mode(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParser") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(fromcp2k, ["--canonical", "-"], input=sample_input)

            assert result.exit_code == 0
            MockParser.assert_called_once()

    def test_trafo_options(self, sample_input, parsed_tree):
        runner = CliRunner()

        for trafo in ["auto", "lower", "upper"]:
            with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserSimplified") as MockParser:
                mock_parser = MagicMock()
                mock_parser.parse.return_value = parsed_tree
                MockParser.return_value = mock_parser

                result = runner.invoke(fromcp2k, ["--trafo", trafo, "-"], input=sample_input)

                assert result.exit_code == 0

    def test_aiida_cp2k_calc_format(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserAiiDA") as MockParser, \
             patch("jinja2.Environment") as MockJinja2:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_template = MagicMock()
            mock_template.render.return_value = "# AiiDA script"
            mock_env = MagicMock()
            mock_env.get_template.return_value = mock_template
            MockJinja2.return_value = mock_env

            result = runner.invoke(fromcp2k, ["--format", "aiida-cp2k-calc", "-"], input=sample_input)

            assert result.exit_code == 0
            assert "# AiiDA script" in result.output

    def test_aiida_warnings(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserAiiDA") as MockParser, \
             patch("jinja2.Environment") as MockJinja2:

            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            mock_template = MagicMock()
            mock_template.render.return_value = "# AiiDA script"
            mock_env = MagicMock()
            mock_env.get_template.return_value = mock_template
            MockJinja2.return_value = mock_env

            result = runner.invoke(fromcp2k, ["--format", "aiida-cp2k-calc", "--canonical", "--trafo", "upper", "-"], input=sample_input)

            assert result.exit_code == 0
            assert "ignored" in result.output.lower() or "The" in result.output

    def test_with_var_values(self, sample_input, parsed_tree):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(fromcp2k, ["-", "-E", "VAR1=value1"], input=sample_input)

            assert result.exit_code == 0

    def test_with_base_dir(self, sample_input, parsed_tree, tmp_path):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.fromcp2k.CP2KInputParserSimplified") as MockParser:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = parsed_tree
            MockParser.return_value = mock_parser

            result = runner.invoke(fromcp2k, ["-", "-b", str(tmp_path)], input=sample_input)

            assert result.exit_code == 0


class TestTrafos:
    def test_key_trafo_short_strings(self):
        assert Trafos.auto.value("ab") == "AB"
        assert Trafos.auto.value("abc") == "ABC"

    def test_key_trafo_long_strings(self):
        assert Trafos.auto.value("abcd") == "abcd"
        assert Trafos.auto.value("GLOBAL") == "global"

    def test_lower_trafo(self):
        assert Trafos.lower.value("GLOBAL") == "global"
        assert Trafos.lower.value("Test") == "test"

    def test_upper_trafo(self):
        assert Trafos.upper.value("global") == "GLOBAL"
        assert Trafos.upper.value("Test") == "TEST"
