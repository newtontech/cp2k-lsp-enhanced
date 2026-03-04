"""Comprehensive tests for CLI modules."""

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.cp2kgen import cp2kgen
from cp2k_input_tools.cli.cp2kget import cp2kget
from cp2k_input_tools.cli.tocp2k import tocp2k
from cp2k_input_tools.cli.fromcp2k import fromcp2k
from cp2k_input_tools.cli.lint import cp2klint
from cp2k_input_tools.cli.lsp import cp2k_language_server
from cp2k_input_tools.cli import smart_open, click_validate_kv


class TestSmartOpen:
    """Tests for smart_open utility."""

    def test_smart_open_read_file(self, tmp_path):
        """Test reading from a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        with smart_open(str(test_file), "r") as f:
            content = f.read()
        assert content == "test content"

    def test_smart_open_write_file(self, tmp_path):
        """Test writing to a file."""
        test_file = tmp_path / "test.txt"
        
        with smart_open(str(test_file), "w") as f:
            f.write("test content")
        
        assert test_file.read_text() == "test content"

    def test_smart_open_stdin_mode(self):
        """Test smart_open with stdin."""
        with smart_open("-", "r") as f:
            assert f is sys.stdin

    def test_smart_open_stdout_mode(self):
        """Test smart_open with stdout."""
        with smart_open("-", "w") as f:
            assert f is sys.stdout


class TestClickValidateKv:
    """Tests for click_validate_kv."""

    def test_valid_key_value(self):
        """Test valid key=value format."""
        result = click_validate_kv(None, None, ["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_empty_list(self):
        """Test empty list."""
        result = click_validate_kv(None, None, [])
        assert result == {}

    def test_already_dict(self):
        """Test when input is already a dict."""
        input_dict = {"key": "value"}
        result = click_validate_kv(None, None, input_dict)
        assert result == input_dict

    def test_invalid_format(self):
        """Test invalid key-value format raises error."""
        with pytest.raises(Exception):  # click.BadParameter
            click_validate_kv(None, None, ["invalid"])


class TestCp2kgen:
    """Tests for cp2kgen CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_input(self):
        return """&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
"""

    def test_cp2kgen_help(self, runner):
        """Test cp2kgen help."""
        result = runner.invoke(cp2kgen, ["--help"])
        assert result.exit_code == 0
        assert "Generates variations" in result.output

    def test_cp2kgen_simple(self, runner, sample_input, tmp_path):
        """Test basic cp2kgen functionality."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(cp2kgen, [str(input_file)])
        assert result.exit_code == 0

    def test_cp2kgen_with_expression(self, runner, sample_input, tmp_path):
        """Test cp2kgen with expression."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(cp2kgen, [str(input_file), "global/project_name=test_gen"])
        assert result.exit_code == 0


class TestCp2kget:
    """Tests for cp2kget CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_input(self):
        return """&GLOBAL
  PROJECT_NAME test_project
  RUN_TYPE ENERGY
&END GLOBAL
"""

    def test_cp2kget_help(self, runner):
        """Test cp2kget help."""
        result = runner.invoke(cp2kget, ["--help"])
        assert result.exit_code == 0
        assert "Get values" in result.output

    def test_cp2kget_simple(self, runner, sample_input, tmp_path):
        """Test basic cp2kget functionality."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(cp2kget, [str(input_file), "global/project_name"])
        assert result.exit_code == 0
        assert "test_project" in result.output

    def test_cp2kget_canonical(self, runner, sample_input, tmp_path):
        """Test cp2kget with canonical option."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(cp2kget, ["--canonical", str(input_file), "+global/project_name"])
        assert result.exit_code == 0


class TestTocp2k:
    """Tests for tocp2k CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_json(self):
        return json.dumps({
            "GLOBAL": {
                "PROJECT_NAME": "test",
                "RUN_TYPE": "ENERGY"
            }
        })

    def test_tocp2k_help(self, runner):
        """Test tocp2k help."""
        result = runner.invoke(tocp2k, ["--help"])
        assert result.exit_code == 0
        assert "Generate a CP2K" in result.output

    def test_tocp2k_json(self, runner, sample_json, tmp_path):
        """Test tocp2k with JSON input."""
        input_file = tmp_path / "input.json"
        input_file.write_text(sample_json)
        
        result = runner.invoke(tocp2k, [str(input_file)])
        assert result.exit_code == 0
        assert "&GLOBAL" in result.output


class TestFromcp2k:
    """Tests for fromcp2k CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_input(self):
        return """&GLOBAL
  PROJECT_NAME test_project
  RUN_TYPE ENERGY
&END GLOBAL
"""

    def test_fromcp2k_help(self, runner):
        """Test fromcp2k help."""
        result = runner.invoke(fromcp2k, ["--help"])
        assert result.exit_code == 0
        assert "Convert CP2K input" in result.output

    def test_fromcp2k_json(self, runner, sample_input, tmp_path):
        """Test fromcp2k with JSON output."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(fromcp2k, ["--format", "json", str(input_file)])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "global" in output or "+global" in output

    def test_fromcp2k_canonical(self, runner, sample_input, tmp_path):
        """Test fromcp2k with canonical option."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(sample_input)
        
        result = runner.invoke(fromcp2k, ["--canonical", str(input_file)])
        assert result.exit_code == 0

    def test_fromcp2k_var_values(self, runner, tmp_path):
        """Test fromcp2k with variable values."""
        input_content = """&GLOBAL
  PROJECT_NAME $PROJECT
&END GLOBAL
"""
        input_file = tmp_path / "input.inp"
        input_file.write_text(input_content)
        
        result = runner.invoke(fromcp2k, ["--set", "PROJECT=test_project", str(input_file)])
        assert result.exit_code == 0


class TestCp2klint:
    """Tests for cp2klint CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def valid_input(self):
        return """&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
"""

    @pytest.fixture
    def invalid_input(self):
        return """&GLOBAL
  PROJECT_NAME test
  INVALID_KEYWORD xyz
&END GLOBAL
"""

    def test_cp2klint_help(self, runner):
        """Test cp2klint help."""
        result = runner.invoke(cp2klint, ["--help"])
        assert result.exit_code == 0
        assert "Check the passed" in result.output

    def test_cp2klint_valid(self, runner, valid_input, tmp_path):
        """Test cp2klint with valid input."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(valid_input)
        
        result = runner.invoke(cp2klint, [str(input_file)])
        assert result.exit_code == 0
        assert "All done" in result.output

    def test_cp2klint_with_base_dir(self, runner, valid_input, tmp_path):
        """Test cp2klint with base directory option."""
        input_file = tmp_path / "input.inp"
        input_file.write_text(valid_input)
        
        result = runner.invoke(cp2klint, ["--base-dir", str(tmp_path), str(input_file)])
        assert result.exit_code == 0


class TestCp2kLanguageServer:
    """Tests for cp2k-language-server CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_lsp_help(self, runner):
        """Test LSP server help."""
        result = runner.invoke(cp2k_language_server, ["--help"])
        assert result.exit_code == 0
        assert "Language Server" in result.output

    def test_lsp_tcp_option(self, runner):
        """Test LSP server with TCP option."""
        result = runner.invoke(cp2k_language_server, ["--tcp", "--help"])
        assert result.exit_code == 0

    def test_lsp_debug_option(self, runner):
        """Test LSP server with debug option."""
        result = runner.invoke(cp2k_language_server, ["--debug", "--help"])
        assert result.exit_code == 0


class TestCLIOptions:
    """Tests for various CLI options."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_base_dir_option(self, runner, tmp_path):
        """Test base directory option."""
        input_file = tmp_path / "input.inp"
        input_file.write_text("&GLOBAL\n&END GLOBAL")
        
        result = runner.invoke(fromcp2k, ["--base-dir", str(tmp_path), str(input_file)])
        assert result.exit_code == 0

    def test_trafo_option(self, runner, tmp_path):
        """Test transformation option."""
        input_file = tmp_path / "input.inp"
        input_file.write_text("&GLOBAL\n&END GLOBAL")
        
        result = runner.invoke(fromcp2k, ["--trafo", "lower", str(input_file)])
        assert result.exit_code == 0
