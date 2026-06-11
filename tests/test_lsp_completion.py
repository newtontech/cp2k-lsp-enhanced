"""Tests for lightweight CP2K LSP completion behavior."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("lsprotocol")


def _load_completion_module():
    module_path = Path(__file__).resolve().parents[1] / "packages" / "language-server" / "cp2k_lsp" / "features" / "completion.py"
    spec = importlib.util.spec_from_file_location("cp2k_lsp_completion", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _completion_labels(items):
    return {item.label for item in items}


def test_qs_method_value_completion_includes_gpw_values():
    completion = _load_completion_module().CompletionProvider(server=None)

    labels = _completion_labels(completion._get_value_completions("      METHOD "))

    assert "GPW" in labels
    assert "GAPW" in labels
    assert "XTB" in labels
    assert ".TRUE." not in labels


def test_keyword_completion_includes_method_keyword():
    completion = _load_completion_module().CompletionProvider(server=None)

    labels = _completion_labels(completion._get_keyword_completions())

    assert "METHOD" in labels
