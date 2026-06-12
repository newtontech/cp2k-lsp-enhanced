"""Tests for the unified tool wrapper CLI (cp2k-lsp tool).

Following TDD principles - these tests define the expected behavior of the tool CLI.
"""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

# Valid CP2K input for testing
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

# Input with @SET variable for testing references
INPUT_WITH_VARIABLE = """\
@SET MY_VAR 42
&GLOBAL
  PROJECT $MY_VAR
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &SUBSYS
    &COORD
      O 0.0 0.0 0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""

# Input with syntax error for diagnostics testing
INPUT_WITH_ERROR = """\
&GLOBAL
  PROJECT test
  INVALID_KEYWORD_HERE
&END GLOBAL
"""


@pytest.fixture
def runner():
    """Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def valid_inp_file():
    """Valid CP2K input file fixture."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(VALID_INPUT)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def variable_inp_file():
    """CP2K input file with @SET variable fixture."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(INPUT_WITH_VARIABLE)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def error_inp_file():
    """CP2K input file with syntax error fixture."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
        f.write(INPUT_WITH_ERROR)
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestToolCheck:
    """Tests for 'cp2k-lsp tool check' command (diagnostics)."""

    def test_check_valid_file(self, runner, valid_inp_file):
        """Check command should succeed on valid file."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["check", valid_inp_file])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "file" in data
        assert "diagnostics" in data
        assert isinstance(data["diagnostics"], list)
        assert "error_count" in data
        assert "warning_count" in data

    def test_check_error_file(self, runner, error_inp_file):
        """Check command should report errors on invalid file."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["check", error_inp_file])
        # Should still exit 0 but include error diagnostics
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["error_count"] >= 1

    def test_check_json_format(self, runner, valid_inp_file):
        """Check command output should be valid JSON with correct schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["check", valid_inp_file])
        data = json.loads(result.output)

        # Verify schema
        assert "file" in data
        assert "diagnostics" in data
        assert "error_count" in data
        assert "warning_count" in data

        for diag in data["diagnostics"]:
            assert "severity" in diag
            assert "source" in diag
            assert "message" in diag
            assert diag["severity"] in ("error", "warning", "info")

    def test_check_nonexistent_file(self, runner):
        """Check command should fail gracefully on nonexistent file."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["check", "/nonexistent/file.inp"])
        assert result.exit_code != 0


class TestToolContext:
    """Tests for 'cp2k-lsp tool context' command."""

    def test_context_requires_position(self, runner, valid_inp_file):
        """Context command should require line and character options."""
        from cp2k_input_tools.cli.tool import tool_cli

        # Missing --line and --char
        result = runner.invoke(tool_cli, ["context", valid_inp_file])
        assert result.exit_code != 0

    def test_context_with_position(self, runner, valid_inp_file):
        """Context command should return context pack for position."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["context", valid_inp_file, "--line", "3", "--char", "10"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "file" in data
        assert "position" in data
        assert "line" in data["position"]
        assert "character" in data["position"]
        assert "context" in data

    def test_context_json_format(self, runner, valid_inp_file):
        """Context command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["context", valid_inp_file, "--line", "5", "--char", "2"])
        data = json.loads(result.output)

        assert "file" in data
        assert "position" in data
        assert "context" in data
        assert isinstance(data["context"], dict)


class TestToolComplete:
    """Tests for 'cp2k-lsp tool complete' command."""

    def test_complete_requires_position(self, runner, valid_inp_file):
        """Complete command should require line and character options."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["complete", valid_inp_file])
        assert result.exit_code != 0

    def test_complete_returns_items(self, runner, valid_inp_file):
        """Complete command should return completion items."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["complete", valid_inp_file, "--line", "5", "--char", "2"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "is_incomplete" in data

    def test_complete_json_format(self, runner, valid_inp_file):
        """Complete command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["complete", valid_inp_file, "--line", "3", "--char", "10"])
        data = json.loads(result.output)

        assert "items" in data
        assert "is_incomplete" in data

        # Each item should have label and kind
        for item in data["items"]:
            assert "label" in item
            assert "kind" in item


class TestToolHover:
    """Tests for 'cp2k-lsp tool hover' command."""

    def test_hover_requires_position(self, runner, valid_inp_file):
        """Hover command should require line and character options."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["hover", valid_inp_file])
        assert result.exit_code != 0

    def test_hover_returns_info(self, runner, valid_inp_file):
        """Hover command should return hover information."""
        from cp2k_input_tools.cli.tool import tool_cli

        # Hover over a known keyword (PROJECT on line 2)
        result = runner.invoke(tool_cli, ["hover", valid_inp_file, "--line", "2", "--char", "5"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "contents" in data
        assert isinstance(data["contents"], str)

    def test_hover_json_format(self, runner, valid_inp_file):
        """Hover command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["hover", valid_inp_file, "--line", "2", "--char", "10"])
        data = json.loads(result.output)

        assert "contents" in data


class TestToolSymbols:
    """Tests for 'cp2k-lsp tool symbols' command."""

    def test_symbols_returns_list(self, runner, valid_inp_file):
        """Symbols command should return document symbols."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["symbols", valid_inp_file])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "symbols" in data
        assert isinstance(data["symbols"], list)

    def test_symbols_json_format(self, runner, valid_inp_file):
        """Symbols command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["symbols", valid_inp_file])
        data = json.loads(result.output)

        assert "symbols" in data

        # Each symbol should have name, kind, and range
        for symbol in data["symbols"]:
            assert "name" in symbol
            assert "kind" in symbol
            assert "range" in symbol


class TestToolDefinition:
    """Tests for 'cp2k-lsp tool definition' command."""

    def test_definition_requires_position(self, runner, variable_inp_file):
        """Definition command should require line and character options."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["definition", variable_inp_file])
        assert result.exit_code != 0

    def test_definition_for_variable(self, runner, variable_inp_file):
        """Definition command should find @SET variable definitions."""
        from cp2k_input_tools.cli.tool import tool_cli

        # Line 3 contains $MY_VAR, should jump to @SET on line 1
        result = runner.invoke(tool_cli, ["definition", variable_inp_file, "--line", "3", "--char", "10"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "locations" in data
        assert isinstance(data["locations"], list)

    def test_definition_json_format(self, runner, variable_inp_file):
        """Definition command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["definition", variable_inp_file, "--line", "3", "--char", "10"])
        data = json.loads(result.output)

        assert "locations" in data

        # Each location should have uri and range
        for loc in data["locations"]:
            assert "uri" in loc
            assert "range" in loc


class TestToolReferences:
    """Tests for 'cp2k-lsp tool references' command."""

    def test_references_requires_position(self, runner, variable_inp_file):
        """References command should require line and character options."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["references", variable_inp_file])
        assert result.exit_code != 0

    def test_references_finds_usages(self, runner, variable_inp_file):
        """References command should find all variable usages."""
        from cp2k_input_tools.cli.tool import tool_cli

        # Line 1 is @SET MY_VAR
        result = runner.invoke(tool_cli, ["references", variable_inp_file, "--line", "1", "--char", "6"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "references" in data
        assert isinstance(data["references"], list)
        # Should find at least the definition and the usage
        assert len(data["references"]) >= 2

    def test_references_json_format(self, runner, variable_inp_file):
        """References command output should have correct JSON schema."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["references", variable_inp_file, "--line", "3", "--char", "10"])
        data = json.loads(result.output)

        assert "references" in data

        # Each reference should have uri and range
        for ref in data["references"]:
            assert "uri" in ref
            assert "range" in ref


class TestToolHelp:
    """Tests for help messages."""

    def test_tool_help(self, runner):
        """Tool command should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "context" in result.output
        assert "complete" in result.output
        assert "hover" in result.output
        assert "symbols" in result.output
        assert "definition" in result.output
        assert "references" in result.output

    def test_check_help(self, runner):
        """Check subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "diagnostics" in result.output.lower()

    def test_context_help(self, runner):
        """Context subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["context", "--help"])
        assert result.exit_code == 0

    def test_complete_help(self, runner):
        """Complete subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["complete", "--help"])
        assert result.exit_code == 0

    def test_hover_help(self, runner):
        """Hover subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["hover", "--help"])
        assert result.exit_code == 0

    def test_symbols_help(self, runner):
        """Symbols subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["symbols", "--help"])
        assert result.exit_code == 0

    def test_definition_help(self, runner):
        """Definition subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["definition", "--help"])
        assert result.exit_code == 0

    def test_references_help(self, runner):
        """References subcommand should show help."""
        from cp2k_input_tools.cli.tool import tool_cli

        result = runner.invoke(tool_cli, ["references", "--help"])
        assert result.exit_code == 0


class TestToolEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_complete_no_context(self, runner):
        """Complete command should handle positions outside section context."""
        from cp2k_input_tools.cli.tool import tool_cli

        # Create a file with content outside any section
        content = "RANDOM_TEXT_OUTSIDE_SECTION\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["complete", f.name, "--line", "1", "--char", "5"])
            # Should succeed even with no context
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "items" in data
        os.unlink(f.name)

    def test_hover_no_keyword(self, runner):
        """Hover command should handle positions with no keyword."""
        from cp2k_input_tools.cli.tool import tool_cli

        content = "   \n   \n"  # Empty lines
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["hover", f.name, "--line", "1", "--char", "2"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "contents" in data
        os.unlink(f.name)

    def test_definition_no_variable(self, runner):
        """Definition command should handle positions with no variable."""
        from cp2k_input_tools.cli.tool import tool_cli

        content = "&GLOBAL\n  PROJECT test\n&END GLOBAL\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["definition", f.name, "--line", "2", "--char", "5"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "locations" in data
            assert data["locations"] == []
        os.unlink(f.name)

    def test_references_no_variable(self, runner):
        """References command should handle positions with no variable."""
        from cp2k_input_tools.cli.tool import tool_cli

        content = "&GLOBAL\n  PROJECT test\n&END GLOBAL\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["references", f.name, "--line", "2", "--char", "5"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "references" in data
            assert data["references"] == []
        os.unlink(f.name)

    def test_symbols_empty_file(self, runner):
        """Symbols command should handle empty files."""
        from cp2k_input_tools.cli.tool import tool_cli

        content = ""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["symbols", f.name])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "symbols" in data
            assert data["symbols"] == []
        os.unlink(f.name)

    def test_context_empty_file(self, runner):
        """Context command should handle empty files."""
        from cp2k_input_tools.cli.tool import tool_cli

        content = ""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".inp", delete=False) as f:
            f.write(content)
            f.flush()
            result = runner.invoke(tool_cli, ["context", f.name, "--line", "1", "--char", "0"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "context" in data
        os.unlink(f.name)
