import importlib
import sys
from unittest import mock

from click.testing import CliRunner


def test_lsp_cli_module_import_without_lsp_extra():
    """The CLI module should be importable even when the optional LSP extra is absent."""
    sys.modules.pop("cp2k_input_tools.cli.lsp", None)

    real_import = __import__

    def import_without_pygls(name, *args, **kwargs):
        if name == "pygls" or name.startswith("pygls."):
            raise ImportError("pygls intentionally hidden for import smoke test")
        return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=import_without_pygls):
        module = importlib.import_module("cp2k_input_tools.cli.lsp")

    assert module.cp2k_language_server is not None


def test_lsp_cli_help_without_lsp_extra():
    """The command help should not import optional LSP dependencies."""
    from cp2k_input_tools.cli.lsp import cp2k_language_server

    runner = CliRunner()

    with mock.patch("builtins.__import__", side_effect=_hide_pygls_import):
        result = runner.invoke(cp2k_language_server, ["--help"])

    assert result.exit_code == 0
    assert "Language Server Protocol" in result.output


def test_lsp_cli_run_without_lsp_extra_reports_install_hint():
    """Running the server without the LSP extra should fail with the install hint."""
    from cp2k_input_tools.cli.lsp import LSP_EXTRA_ERROR, cp2k_language_server

    runner = CliRunner()

    with mock.patch("builtins.__import__", side_effect=_hide_pygls_import):
        result = runner.invoke(cp2k_language_server, [])

    assert result.exit_code == 1
    assert LSP_EXTRA_ERROR in result.output


def _hide_pygls_import(name, *args, **kwargs):
    if name == "pygls" or name.startswith("pygls."):
        raise ImportError("pygls intentionally hidden for import smoke test")
    return _REAL_IMPORT(name, *args, **kwargs)


_REAL_IMPORT = __import__
