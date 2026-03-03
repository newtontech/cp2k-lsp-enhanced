"""Comprehensive tests for cp2k_input_tools/cli/ to achieve 100% coverage."""

import pytest
import click
from click.testing import CliRunner
from io import StringIO
import sys

from cp2k_input_tools.cli import (
    smart_open,
    click_validate_kv,
    fhandle_argument,
    yaml_option,
    canonical_option,
    base_dir_option,
    var_values_option,
)


class TestSmartOpen:
    """Test smart_open context manager."""

    def test_smart_open_read_stdin(self):
        """Test reading from stdin."""
        with smart_open(None, "r") as f:
            assert f == sys.stdin

    def test_smart_open_write_stdout(self):
        """Test writing to stdout."""
        with smart_open(None, "w") as f:
            assert f == sys.stdout

    def test_smart_open_dash_stdin(self):
        """Test reading from stdin with dash."""
        with smart_open("-", "r") as f:
            assert f == sys.stdin

    def test_smart_open_dash_stdout(self):
        """Test writing to stdout with dash."""
        with smart_open("-", "w") as f:
            assert f == sys.stdout

    def test_smart_open_read_file(self, tmp_path):
        """Test reading from file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        with smart_open(str(test_file), "r") as f:
            content = f.read()
        assert content == "test content"

    def test_smart_open_write_file(self, tmp_path):
        """Test writing to file."""
        test_file = tmp_path / "test.txt"
        with smart_open(str(test_file), "w") as f:
            f.write("test content")
        assert test_file.read_text() == "test content"


class TestClickValidateKV:
    """Test click_validate_kv callback."""

    def test_validate_kv_single(self):
        """Test single key=value."""
        result = click_validate_kv(None, None, ["key=value"])
        assert result == {"key": "value"}

    def test_validate_kv_multiple(self):
        """Test multiple key=value pairs."""
        result = click_validate_kv(None, None, ["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_validate_kv_already_dict(self):
        """Test with already parsed dict."""
        result = click_validate_kv(None, None, {"key": "value"})
        assert result == {"key": "value"}

    def test_validate_kv_invalid_format(self):
        """Test invalid format raises error."""
        with pytest.raises(click.BadParameter):
            click_validate_kv(None, None, ["invalid"])

    def test_validate_kv_with_equals_in_value(self):
        """Test value containing equals sign."""
        result = click_validate_kv(None, None, ["key=value=with=equals"])
        assert result == {"key": "value=with=equals"}


class TestClickDecorators:
    """Test click decorator functions."""

    def test_yaml_option(self):
        """Test yaml_option decorator."""
        @yaml_option
        @click.command()
        def test_cmd(yaml):
            click.echo(f"yaml={yaml}")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--yaml"])
        assert result.exit_code == 0
        assert "yaml=True" in result.output

    def test_canonical_option(self):
        """Test canonical_option decorator."""
        @canonical_option
        @click.command()
        def test_cmd(canonical):
            click.echo(f"canonical={canonical}")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["-c"])
        assert result.exit_code == 0
        assert "canonical=True" in result.output

    def test_base_dir_option(self):
        """Test base_dir_option decorator."""
        @base_dir_option
        @click.command()
        def test_cmd(base_dir):
            click.echo(f"base_dir={base_dir}")

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(test_cmd, ["-b", "."])
            assert result.exit_code == 0

    def test_var_values_option(self):
        """Test var_values_option decorator."""
        @var_values_option
        @click.command()
        def test_cmd(var_values):
            click.echo(f"var_values={var_values}")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["-E", "key=value"])
        assert result.exit_code == 0
        assert "key" in result.output
