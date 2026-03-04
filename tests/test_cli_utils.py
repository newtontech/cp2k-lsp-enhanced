"""Tests for CLI utils module."""
import pathlib
import sys
from unittest.mock import mock_open, patch

import click
import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli import (
    base_dir_option,
    canonical_option,
    click_validate_kv,
    fhandle_argument,
    smart_open,
    var_values_option,
    yaml_option,
)


class TestSmartOpen:
    def test_read_from_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with smart_open(test_file, "r") as f:
            content = f.read()
            assert content == "test content"

    def test_read_from_stdin(self):
        with patch.object(sys, "stdin", mock_open(read_data="stdin content")()):
            with smart_open("-", "r") as f:
                content = f.read()
                assert content == "stdin content"

    def test_write_to_file(self, tmp_path):
        test_file = tmp_path / "test.txt"

        with smart_open(test_file, "w") as f:
            f.write("written content")

        assert test_file.read_text() == "written content"

    def test_write_to_stdout(self):
        with patch.object(sys, "stdout") as mock_stdout:
            with smart_open("-", "w") as f:
                f.write("stdout content")

    def test_write_exclusive_mode(self, tmp_path):
        test_file = tmp_path / "test.txt"

        with smart_open(test_file, "x") as f:
            f.write("exclusive content")

        assert test_file.read_text() == "exclusive content"

        # Should raise FileExistsError in exclusive mode
        with pytest.raises(FileExistsError):
            with smart_open(test_file, "x") as f:
                f.write("another content")

    def test_invalid_mode(self):
        with pytest.raises(AssertionError):
            with smart_open("test.txt", "a") as f:
                pass


class TestClickValidateKv:
    def test_valid_key_value_pairs(self):
        result = click_validate_kv(None, None, ["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_already_dict(self):
        input_dict = {"key": "value"}
        result = click_validate_kv(None, None, input_dict)
        assert result == input_dict

    def test_invalid_format(self):
        with pytest.raises(click.BadParameter):
            click_validate_kv(None, None, ["invalid_format"])

    def test_empty_list(self):
        result = click_validate_kv(None, None, [])
        assert result == {}

    def test_value_with_equals(self):
        result = click_validate_kv(None, None, ["key=value=with=equals"])
        assert result == {"key": "value=with=equals"}


class TestDecorators:
    def test_fhandle_argument(self):
        @click.command()
        @fhandle_argument
        def dummy_cmd(fhandle):
            return fhandle.read()

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, ["-"], input="test input")
        assert result.exit_code == 0
        assert "test input" in result.output

    def test_yaml_option(self):
        @click.command()
        @yaml_option
        def dummy_cmd(yaml):
            return str(yaml)

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, ["--yaml"])
        assert result.exit_code == 0
        assert "True" in result.output

    def test_canonical_option(self):
        @click.command()
        @canonical_option
        def dummy_cmd(canonical):
            return str(canonical)

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, ["--canonical"])
        assert result.exit_code == 0
        assert "True" in result.output

    def test_base_dir_option(self, tmp_path):
        @click.command()
        @base_dir_option
        def dummy_cmd(base_dir):
            return str(base_dir)

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, ["-b", str(tmp_path)])
        assert result.exit_code == 0
        assert str(tmp_path) in result.output

    def test_var_values_option(self):
        @click.command()
        @var_values_option
        def dummy_cmd(var_values):
            return str(var_values)

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, ["-E", "key1=value1", "-E", "key2=value2"])
        assert result.exit_code == 0
        assert "key1" in result.output
        assert "key2" in result.output


class TestDecoratorChaining:
    def test_multiple_decorators(self):
        @click.command()
        @fhandle_argument
        @canonical_option
        @base_dir_option
        @var_values_option
        def dummy_cmd(fhandle, canonical, base_dir, var_values):
            return f"canonical={canonical}, base_dir={base_dir}, var_values={var_values}"

        runner = CliRunner()
        result = runner.invoke(dummy_cmd, [
            "--canonical",
            "-b", ".",
            "-E", "key=value",
            "-"
        ], input="test")

        assert result.exit_code == 0
