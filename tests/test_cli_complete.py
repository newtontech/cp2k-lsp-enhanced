"""
Comprehensive unit tests for cp2k_input_tools CLI modules
Target: 100% code coverage
"""

import io
import sys
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import MagicMock, patch, mock_open

from cp2k_input_tools.cli.lint import cp2klint
from cp2k_input_tools.cli.lsp import cp2k_language_server
from cp2k_input_tools.cli.cp2kgen import cp2kgen
from cp2k_input_tools.cli.cp2kget import cp2kget
from cp2k_input_tools.cli.fromcp2k import fromcp2k
from cp2k_input_tools.cli.tocp2k import tocp2k
from cp2k_input_tools.cli.datafile_lint import cp2k_datafile_lint
from cp2k_input_tools.cli import (
    fhandle_argument,
    base_dir_option,
    var_values_option,
    canonical_option,
    yaml_option,
    validate_kv,
    smart_open,
)


class TestSmartOpen:
    """Test smart_open function"""
    
    def test_smart_open_read_file(self, tmp_path):
        """Test reading from file"""
        test_file = tmp_path / "test.inp"
        test_file.write_text("test content")
        
        with smart_open(test_file, "r") as f:
            content = f.read()
        
        assert content == "test content"
    
    def test_smart_open_write_file(self, tmp_path):
        """Test writing to file"""
        test_file = tmp_path / "test.out"
        
        with smart_open(test_file, "w") as f:
            f.write("output content")
        
        assert test_file.read_text() == "output content"
    
    def test_smart_open_read_stdin(self):
        """Test reading from stdin (dash)"""
        with patch('sys.stdin', io.StringIO("stdin content")):
            with smart_open("-", "r") as f:
                content = f.read()
        
        assert content == "stdin content"
    
    def test_smart_open_write_stdout(self):
        """Test writing to stdout (dash)"""
        mock_stdout = io.StringIO()
        with patch('sys.stdout', mock_stdout):
            with smart_open("-", "w") as f:
                f.write("stdout content")
        
        assert mock_stdout.getvalue() == "stdout content"
    
    def test_smart_open_invalid_mode(self):
        """Test with invalid mode"""
        with pytest.raises(ValueError, match="Invalid mode"):
            smart_open("test.txt", "invalid_mode")


class TestValidateKv:
    """Test validate_kv callback"""
    
    def test_validate_kv_empty(self):
        """Test with empty list"""
        result = validate_kv(None, None, [])
        assert result == {}
    
    def test_validate_kv_single_pair(self):
        """Test with single key-value pair"""
        result = validate_kv(None, None, ["key=value"])
        assert result == {"key": "value"}
    
    def test_validate_kv_multiple_pairs(self):
        """Test with multiple key-value pairs"""
        result = validate_kv(None, None, ["key1=value1", "key2=value2"])
        assert result == {"key1": "value1", "key2": "value2"}
    
    def test_validate_kv_already_dict(self):
        """Test when value is already a dict"""
        input_dict = {"key": "value"}
        result = validate_kv(None, None, input_dict)
        assert result is input_dict
    
    def test_validate_kv_invalid_format(self):
        """Test with invalid format"""
        with pytest.raises(ValueError, match="must be in format"):
            validate_kv(None, None, ["invalid_no_equals"])
    
    def test_validate_kv_with_equals_in_value(self):
        """Test with equals sign in value"""
        result = validate_kv(None, None, ["key=value=with=equals"])
        assert result == {"key": "value=with=equals"}


class TestCliLint:
    """Test cp2klint CLI"""
    
    def test_lint_valid_input(self, tmp_path):
        """Test lint with valid input"""
        test_file = tmp_path / "valid.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2klint, [str(test_file)])
        
        assert result.exit_code == 0
        assert "Happy calculating" in result.output
    
    def test_lint_invalid_input(self, tmp_path):
        """Test lint with invalid input"""
        test_file = tmp_path / "invalid.inp"
        test_file.write_text("""&GLOBAL
  invalid'
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2klint, [str(test_file)])
        
        assert result.exit_code == 1
        assert "Syntax error" in result.output
    
    def test_lint_with_var_values(self, tmp_path):
        """Test lint with variable values"""
        test_file = tmp_path / "test.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME ${MYVAR}
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2klint, ["-D", "MYVAR=testvalue", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_lint_with_base_dir(self, tmp_path):
        """Test lint with base directory"""
        test_file = tmp_path / "test.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2klint, ["-b", str(tmp_path), str(test_file)])
        
        assert result.exit_code == 0


class TestCliLsp:
    """Test cp2k_language_server CLI"""
    
    @patch('cp2k_input_tools.cli.lsp.cp2k_server')
    def test_lsp_stdio_mode(self, mock_server):
        """Test LSP server in stdio mode"""
        runner = CliRunner()
        result = runner.invoke(cp2k_language_server)
        
        assert result.exit_code == 0
        mock_server.start_io.assert_called_once()
    
    @patch('cp2k_input_tools.cli.lsp.cp2k_server')
    def test_lsp_tcp_mode(self, mock_server):
        """Test LSP server in TCP mode"""
        runner = CliRunner()
        result = runner.invoke(cp2k_language_server, ["--tcp", "--host", "127.0.0.1", "--port", "1234"])
        
        assert result.exit_code == 0
        mock_server.start_tcp.assert_called_once_with("127.0.0.1", 1234)
    
    @patch('cp2k_input_tools.cli.lsp.cp2k_server')
    def test_lsp_debug_mode(self, mock_server):
        """Test LSP server in debug mode"""
        runner = CliRunner()
        result = runner.invoke(cp2k_language_server, ["--debug"])
        
        assert result.exit_code == 0


class TestCliCp2kgen:
    """Test cp2kgen CLI"""
    
    def test_cp2kgen_basic(self, tmp_path):
        """Test basic cp2kgen functionality"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cp2kgen, [str(test_file), "global/project_name=modified"])
        
        # Should create output file
        assert any("modified" in f.name for f in tmp_path.iterdir() if f.is_file())
    
    def test_cp2kgen_with_multiple_values(self, tmp_path):
        """Test cp2kgen with multiple values"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kgen, [
            str(test_file),
            "global/project_name=[test1,test2]"
        ])
        
        assert result.exit_code == 0
    
    def test_cp2kgen_zip_mode(self, tmp_path):
        """Test cp2kgen with zip mode"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kgen, [
            "--zip",
            str(test_file),
            "global/project_name=[p1,p2]",
            "global/run_type=[ENERGY,MD]"
        ])
        
        assert result.exit_code == 0
    
    def test_cp2kgen_invalid_expression(self, tmp_path):
        """Test cp2kgen with invalid expression"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kgen, [str(test_file), "invalid_expression"])
        
        assert result.exit_code != 0
    
    def test_cp2kgen_canonical_mode(self, tmp_path):
        """Test cp2kgen in canonical mode"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kgen, ["--canonical", str(test_file), "global/project_name=new"])
        
        assert result.exit_code == 0


class TestCliCp2kget:
    """Test cp2kget CLI"""
    
    def test_cp2kget_basic(self, tmp_path):
        """Test basic cp2kget functionality"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test_value
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kget, [str(test_file), "global/project_name"])
        
        assert result.exit_code == 0
        assert "test_value" in result.output
    
    def test_cp2kget_multiple_paths(self, tmp_path):
        """Test cp2kget with multiple paths"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kget, [str(test_file), "global/project_name", "global/run_type"])
        
        assert result.exit_code == 0
    
    def test_cp2kget_canonical_mode(self, tmp_path):
        """Test cp2kget in canonical mode"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kget, ["--canonical", str(test_file), "global/project_name"])
        
        assert result.exit_code == 0
    
    def test_cp2kget_no_paths(self, tmp_path):
        """Test cp2kget with no paths specified"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(cp2kget, [str(test_file)])
        
        # Should show help or error
        assert result.exit_code != 0 or "Usage" in result.output


class TestCliFromcp2k:
    """Test fromcp2k CLI"""
    
    def test_fromcp2k_json_output(self, tmp_path):
        """Test fromcp2k with JSON output"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(fromcp2k, [str(test_file)])
        
        assert result.exit_code == 0
        assert '"' in result.output  # JSON should have quotes
    
    def test_fromcp2k_yaml_output(self, tmp_path):
        """Test fromcp2k with YAML output"""
        pytest.importorskip("ruamel.yaml")
        
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(fromcp2k, ["--yaml", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_fromcp2k_trafo_lower(self, tmp_path):
        """Test fromcp2k with lower transformation"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(fromcp2k, ["--trafo", "lower", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_fromcp2k_trafo_upper(self, tmp_path):
        """Test fromcp2k with upper transformation"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(fromcp2k, ["--trafo", "upper", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_fromcp2k_canonical_mode(self, tmp_path):
        """Test fromcp2k in canonical mode"""
        test_file = tmp_path / "input.inp"
        test_file.write_text("""&GLOBAL
  PROJECT_NAME test
&END GLOBAL
""")
        
        runner = CliRunner()
        result = runner.invoke(fromcp2k, ["--canonical", str(test_file)])
        
        assert result.exit_code == 0


class TestCliTocp2k:
    """Test tocp2k CLI"""
    
    def test_tocp2k_json_input(self, tmp_path):
        """Test tocp2k with JSON input"""
        test_file = tmp_path / "input.json"
        test_file.write_text('{"global": {"project_name": "test"}}')
        
        runner = CliRunner()
        result = runner.invoke(tocp2k, [str(test_file)])
        
        assert result.exit_code == 0
        assert "&GLOBAL" in result.output
    
    def test_tocp2k_yaml_input(self, tmp_path):
        """Test tocp2k with YAML input"""
        pytest.importorskip("ruamel.yaml")
        
        test_file = tmp_path / "input.yaml"
        test_file.write_text("global:\n  project_name: test\n")
        
        runner = CliRunner()
        result = runner.invoke(tocp2k, [str(test_file)])
        
        assert result.exit_code == 0
    
    def test_tocp2k_empty_tree(self, tmp_path):
        """Test tocp2k with empty tree"""
        test_file = tmp_path / "empty.json"
        test_file.write_text('{}')
        
        runner = CliRunner()
        result = runner.invoke(tocp2k, [str(test_file)])
        
        assert result.exit_code == 0


class TestCliDatafileLint:
    """Test cp2k_datafile_lint CLI"""
    
    def test_datafile_lint_basis_cp2k(self, tmp_path):
        """Test datafile_lint with CP2K basis format"""
        test_file = tmp_path / "basis.dat"
        test_file.write_text("H DZVP-MOLOPT-GTH\n  1\n  1  0  0  1  1\n    1.0  1.0\n")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--format", "basis:cp2k", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_datafile_lint_basis_crystal(self, tmp_path):
        """Test datafile_lint with CRYSTAL basis format"""
        test_file = tmp_path / "basis.dat"
        test_file.write_text("H DZVP\n1 0\n1.0 1.0\n")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--format", "basis:crystal", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_datafile_lint_pseudo_cp2k(self, tmp_path):
        """Test datafile_lint with CP2K pseudopotential format"""
        test_file = tmp_path / "pseudo.dat"
        test_file.write_text("H GTH-PBE\n  1\n  1  0  0  0\n    1.0  1.0\n")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--format", "pseudo:cp2k", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_datafile_lint_invalid_format(self, tmp_path):
        """Test datafile_lint with invalid format"""
        test_file = tmp_path / "test.dat"
        test_file.write_text("test content")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--format", "invalid:format", str(test_file)])
        
        assert result.exit_code != 0
    
    def test_datafile_lint_in_place(self, tmp_path):
        """Test datafile_lint in-place editing"""
        test_file = tmp_path / "basis.dat"
        test_file.write_text("H DZVP-MOLOPT-GTH\n  1\n  1  0  0  1  1\n    1.0  1.0\n")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--in-place", "--format", "basis:cp2k", str(test_file)])
        
        assert result.exit_code == 0
    
    def test_datafile_lint_emit_comments(self, tmp_path):
        """Test datafile_lint with emit comments"""
        test_file = tmp_path / "basis.dat"
        test_file.write_text("# Comment\nH DZVP-MOLOPT-GTH\n  1\n  1  0  0  1  1\n    1.0  1.0\n")
        
        runner = CliRunner()
        result = runner.invoke(cp2k_datafile_lint, ["--emit-comments", "--format", "basis:cp2k", str(test_file)])
        
        assert result.exit_code == 0


class TestCliDecorators:
    """Test CLI decorators"""
    
    def test_base_dir_option(self):
        """Test base_dir_option decorator exists"""
        # Just verify the decorator exists and is callable
        assert callable(base_dir_option)
    
    def test_var_values_option(self):
        """Test var_values_option decorator exists"""
        assert callable(var_values_option)
    
    def test_canonical_option(self):
        """Test canonical_option decorator exists"""
        assert callable(canonical_option)
    
    def test_yaml_option(self):
        """Test yaml_option decorator exists"""
        assert callable(yaml_option)
    
    def test_fhandle_argument(self):
        """Test fhandle_argument decorator exists"""
        assert callable(fhandle_argument)
