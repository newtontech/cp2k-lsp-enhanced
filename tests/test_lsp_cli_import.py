import importlib
import sys
from unittest import mock


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
