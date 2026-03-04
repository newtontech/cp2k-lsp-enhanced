"""Tests for datafile_lint CLI tool."""
import pathlib
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

from cp2k_input_tools.cli.datafile_lint import cp2k_datafile_lint


class TestDatafileLint:
    def test_basis_cp2k_format(self):
        runner = CliRunner()

        basis_content = """H DZVP-GTH
  2
  1 0 0 4 1
  9.485716001014e+00  1.0
  ...
"""

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetData") as MockBasisSetData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data=basis_content)):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = ["H DZVP-GTH", "  2", "  1 0 0 4 1"]
            MockBasisSetData.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["basis", "-"])

            assert result.exit_code == 0

    def test_basis_cp2k_format_alias(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetData") as MockBasisSetData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = []
            MockBasisSetData.datafile_iter.return_value = []

            for alias in ["basis", "basisset", "basissets"]:
                result = runner.invoke(cp2k_datafile_lint, [alias, "-"])
                assert result.exit_code == 0

    def test_pseudo_cp2k_format(self):
        runner = CliRunner()

        pseudo_content = """H GTH-PBE-q1
    1
    1  0  0  0
    ...
"""

        with patch("cp2k_input_tools.cli.datafile_lint.PseudopotentialData") as MockPseudoData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data=pseudo_content)):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = ["H GTH-PBE-q1", "    1", "    1  0  0  0"]
            MockPseudoData.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["pseudo", "-"])

            assert result.exit_code == 0

    def test_pseudo_aliases(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.PseudopotentialData") as MockPseudoData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = []
            MockPseudoData.datafile_iter.return_value = []

            for alias in ["pseudo", "pseudos", "pseudopotential", "pseudopotentials", "potentials"]:
                result = runner.invoke(cp2k_datafile_lint, [alias, "-"])
                assert result.exit_code == 0

    def test_in_place_edit(self, tmp_path):
        runner = CliRunner()

        test_file = tmp_path / "test.basis"
        test_file.write_text("H DZVP-GTH\n")

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetData") as MockBasisSetData:
            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = ["H DZVP-GTH"]
            MockBasisSetData.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["basis", str(test_file), "--inplace"])

            assert result.exit_code == 0

    def test_in_place_edit_from_stdin_error(self):
        runner = CliRunner()

        result = runner.invoke(cp2k_datafile_lint, ["basis", "-", "--inplace"])

        assert result.exit_code != 0
        assert "Replacing file content does not work when reading from stdin" in str(result.exception) or \
               "Replacing file content does not work" in result.output

    def test_basis_crystal_format(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetDataCrystal") as MockCrystalBasis, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = []
            MockCrystalBasis.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["basis", "-", "--input-basis-format", "crystal"])

            assert result.exit_code == 0

    def test_basis_format_conversion_error(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):
            result = runner.invoke(cp2k_datafile_lint, ["basis", "-", "--output-basis-format", "crystal"])

            assert result.exit_code != 0
            assert "Basis set format conversion" in str(result.exception) or "conversion" in result.output.lower()

    def test_with_identifier(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetData") as MockBasisSetData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = []
            MockBasisSetData.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["basis", "-", "--identifier", "CUSTOM"])

            assert result.exit_code == 0

    def test_emit_comments(self):
        runner = CliRunner()

        basis_content = """# Comment line
H DZVP-GTH
  2
"""

        with patch("cp2k_input_tools.cli.datafile_lint.BasisSetData") as MockBasisSetData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data=basis_content)):

            mock_instance = MagicMock()
            mock_instance.cp2k_format_line_iter.return_value = ["H DZVP-GTH", "  2"]
            MockBasisSetData.datafile_iter.return_value = ["# Comment line", mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["basis", "-"])

            assert result.exit_code == 0

    def test_nwchem_ecp_output_format(self):
        runner = CliRunner()

        with patch("cp2k_input_tools.cli.datafile_lint.PseudopotentialData") as MockPseudoData, \
             patch("cp2k_input_tools.cli.datafile_lint.smart_open", mock_open(read_data="")):

            mock_instance = MagicMock()
            mock_instance.nwchem_ecp_format_line_iter.return_value = ["H GTH-PBE"]
            MockPseudoData.datafile_iter.return_value = [mock_instance]

            result = runner.invoke(cp2k_datafile_lint, ["pseudo", "-", "--output-basis-format", "nwchem-ecp"])

            assert result.exit_code == 0
