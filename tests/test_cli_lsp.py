"""Tests for cp2k_input_tools/cli/lsp.py"""

import sys
import pytest

# Check if pygls is available
pygls = pytest.importorskip("pygls")


class TestCLILSP:
    """Test CLI LSP module."""

    def test_import_cli_lsp(self):
        """Test importing CLI LSP module."""
        from cp2k_input_tools.cli import lsp
        assert lsp is not None

    def test_cp2k_language_server_exists(self):
        """Test cp2k_language_server command exists."""
        from cp2k_input_tools.cli.lsp import cp2k_language_server
        assert cp2k_language_server is not None
        assert callable(cp2k_language_server)
