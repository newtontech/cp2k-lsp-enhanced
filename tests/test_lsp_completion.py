"""Tests for lightweight CP2K LSP completion behavior."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lsprotocol import types as lsp

from cp2k_input_tools.cursor_context import CursorContext
from cp2k_input_tools.schema_index import KeywordSpec

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


def _make_completion_params(line=0, character=0):
    return lsp.CompletionParams(
        text_document=lsp.TextDocumentIdentifier(uri="file:///test.inp"),
        position=lsp.Position(line=line, character=character),
    )


def _mock_server(workspace_doc_lines):
    server = MagicMock()
    doc = MagicMock()
    doc.lines = workspace_doc_lines
    server.workspace.get_text_document.return_value = doc
    return server


def _mock_schema_index(**kwargs):
    schema = MagicMock()
    for key, value in kwargs.items():
        setattr(schema, key, value)
    return schema


def test_qs_method_value_completion_includes_gpw_values():
    CompletionProvider = _load_completion_module().CompletionProvider

    schema = _mock_schema_index(
        get_keyword=MagicMock(
            return_value=KeywordSpec(
                name="METHOD",
                variable_type="keyword",
                default_value="GPW",
                enumeration_values=["GPW", "GAPW", "LDP", "XTB", "AM1", "PM3", "PM6", "PM7", "MNDO"],
                description="Electronic structure method",
            )
        ),
    )

    server = _mock_server(["&METHOD GPW", "&END METHOD"])
    provider = CompletionProvider(server=server)
    provider._schema_index = schema

    ctx = CursorContext(
        uri="file:///test.inp",
        line=0,
        character=12,
        section_path=("FORCE_EVAL", "DFT", "QS"),
        current_section="QS",
        current_keyword="METHOD",
        is_section_start=False,
        is_section_end=False,
        is_keyword_position=False,
        is_value_position=True,
        prefix="",
    )

    with patch.object(provider._cursor_resolver, "resolve_cursor_context", return_value=ctx):
        params = _make_completion_params(line=0, character=12)
        result = provider.provide_completion(params)

    assert result is not None
    labels = _completion_labels(result.items)

    assert "GPW" in labels
    assert "GAPW" in labels
    assert "XTB" in labels
    assert ".TRUE." not in labels


def test_keyword_completion_includes_method_keyword():
    CompletionProvider = _load_completion_module().CompletionProvider

    schema = _mock_schema_index(
        get_keywords=MagicMock(
            return_value={
                "METHOD": KeywordSpec(
                    name="METHOD",
                    variable_type="keyword",
                    default_value="GPW",
                    enumeration_values=[],
                    description="Electronic structure method",
                ),
            }
        ),
    )

    server = _mock_server(["METHOD ", "&END QS"])
    provider = CompletionProvider(server=server)
    provider._schema_index = schema

    ctx = CursorContext(
        uri="file:///test.inp",
        line=0,
        character=0,
        section_path=("FORCE_EVAL", "DFT", "QS"),
        current_section="QS",
        current_keyword=None,
        is_section_start=False,
        is_section_end=False,
        is_keyword_position=True,
        is_value_position=False,
        prefix="",
    )

    with patch.object(provider._cursor_resolver, "resolve_cursor_context", return_value=ctx):
        params = _make_completion_params(line=0, character=0)
        result = provider.provide_completion(params)

    assert result is not None
    labels = _completion_labels(result.items)

    assert "METHOD" in labels
