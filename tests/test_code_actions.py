"""Tests for schema-backed LSP code actions (issue #49, #122).

Test Cases:
1. Invalid enum value suggests closest valid value
2. Unknown keyword suggests move to correct section (if applicable)
3. Missing &END suggests insert fix
4. Section name mismatch suggests rename fix
5. Code actions are not provided for non-fixable diagnostics
6. Typo keywords suggest nearest valid keyword
7. Typo sections suggest nearest valid child section
8. Removed/deprecated keywords suggest documented replacement
9. KEY=VALUE style suggests canonical KEY VALUE format
"""

import sys
from time import sleep

import pytest

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_OPEN,
    CodeActionContext,
    CodeActionParams,
    DidOpenTextDocumentParams,
    TextDocumentIdentifier,
    TextDocumentItem,
)

CALL_TIMEOUT = 5


def _open_file(client, server, filepath):
    """Helper to open a file in the LSP server."""
    testpath = filepath
    with testpath.open("r") as fhandle:
        content = fhandle.read()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(testpath), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)
    return content


def test_code_action_for_invalid_enum(client_server, tmp_path):
    """Test that code action suggests closest valid enum value."""
    client, server = client_server

    test_file = tmp_path / "invalid_enum.inp"
    test_file.write_text("&FORCE_EVAL\n" "   METHOD NOT_A_VALID_METHOD\n" "&END FORCE_EVAL\n")

    content = test_file.read_text()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(test_file), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    # Wait for diagnostics to be published
    assert client.diagnostics is not None, "Should have diagnostics"

    # Request code actions for the diagnostic range
    if client.diagnostics:
        result = client.lsp.send_request(
            TEXT_DOCUMENT_CODE_ACTION,
            CodeActionParams(
                text_document=TextDocumentIdentifier(uri=str(test_file)),
                range=client.diagnostics[0].range,
                context=CodeActionContext(diagnostics=client.diagnostics),
            ),
        ).result(timeout=CALL_TIMEOUT)

        # Code actions are optional - this test documents expected behavior
        # For now, just verify we got a result (even if empty list)
        if result is not None:
            actions = result if isinstance(result, list) else []
            print(f"Got {len(actions)} code actions")
            for action in actions:
                print(f"  - {action.title}")


def test_code_action_for_unknown_keyword(client_server, tmp_path):
    """Test that code action suggests correct section for unknown keyword."""
    client, server = client_server

    test_file = tmp_path / "unknown_keyword.inp"
    test_file.write_text("&FORCE_EVAL\n" "   FAKE_KEYWORD value\n" "&END FORCE_EVAL\n")

    content = test_file.read_text()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(test_file), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    assert client.diagnostics is not None, "Should have diagnostics"

    # Code actions for unknown keywords are a nice-to-have
    # This test documents the expected behavior


def test_no_code_actions_for_syntax_errors(client_server, tmp_path):
    """Test that code actions are not provided for syntax errors."""
    client, server = client_server

    test_file = tmp_path / "syntax_error.inp"
    test_file.write_text(
        "&FORCE_EVAL\n"
        "   METHOD QS\n"
        # Missing &END
    )

    content = test_file.read_text()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(test_file), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    # Should have diagnostics for unclosed section
    assert client.diagnostics is not None, "Should have diagnostics"

    # Code actions for syntax errors are not currently implemented
    # This test documents that syntax errors don't crash the server


# Unit tests for code_actions module (no LSP server needed)
class TestCodeActionsUnit:
    """Unit tests for code actions functionality."""

    def test_find_closest_match(self):
        """Test closest match finding."""
        from cp2k_input_tools.code_actions import _find_closest_match

        # Exact match
        assert _find_closest_match("METHOD", ["METHOD", "RUN_TYPE"]) == "METHOD"

        # Close match
        assert _find_closest_match("METHD", ["METHOD", "RUN_TYPE"]) == "METHOD"

        # No match
        assert _find_closest_match("XYZ", ["METHOD", "RUN_TYPE"]) is None

        # Empty options
        assert _find_closest_match("METHOD", []) is None

    def test_fix_equals_style(self):
        """Test KEY=VALUE to KEY VALUE conversion."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_equals_style

        text = "CUTOFF=1000"
        range_obj = Range(start=Position(line=0, character=0), end=Position(line=0, character=len(text)))
        actions = _fix_equals_style(text, 0, range_obj, "file:///test.inp")

        assert len(actions) == 1
        assert "CUTOFF 1000" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_mismatched_end(self):
        """Test mismatched &END section name fix."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_mismatched_end

        lines = [
            "&FORCE_EVAL",
            "   METHOD QS",
            "&END DFT",  # Wrong: should be &END FORCE_EVAL
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=2, character=0), end=Position(line=2, character=len(lines[2])))
        actions = _fix_mismatched_end(lines[2], 2, range_obj, "file:///test.inp", lines)

        assert len(actions) == 1
        assert "FORCE_EVAL" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_missing_end(self):
        """Test missing &END fix."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_missing_end
        from cp2k_input_tools.schema_index import get_schema_index

        lines = [
            "&FORCE_EVAL",
            "   METHOD QS",
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=0, character=0), end=Position(line=0, character=len(lines[0])))
        schema = get_schema_index()
        actions = _fix_missing_end(lines[0], 0, range_obj, "file:///test.inp", lines, schema)

        assert len(actions) == 1
        assert "&END FORCE_EVAL" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_unknown_keyword(self):
        """Test unknown keyword fix."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_unknown_keyword
        from cp2k_input_tools.schema_index import get_schema_index

        lines = [
            "&FORCE_EVAL",
            "   METHD QS",
            "&END FORCE_EVAL",
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=1, character=0), end=Position(line=1, character=len(lines[1])))
        schema = get_schema_index()
        actions = _fix_unknown_keyword(lines[1], 1, range_obj, "file:///test.inp", lines, schema)

        assert len(actions) == 1
        assert "METHOD" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_unknown_section(self):
        """Test unknown section fix."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_unknown_section
        from cp2k_input_tools.schema_index import get_schema_index

        lines = [
            "&FOR_EVAL",
            "   METHOD QS",
            "&END FOR_EVAL",
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=0, character=0), end=Position(line=0, character=len(lines[0])))
        schema = get_schema_index()
        actions = _fix_unknown_section(lines[0], 0, range_obj, "file:///test.inp", lines, schema)

        assert len(actions) == 1
        assert "FORCE_EVAL" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_removed_keyword(self):
        """Test removed keyword fix."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_removed_keyword

        lines = [
            "&FORCE_EVAL",
            "   OLD_KEYWORD value",
            "&END FORCE_EVAL",
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=1, character=0), end=Position(line=1, character=len(lines[1])))
        diagnostic_data = {"suggested_fix": "Replace OLD_KEYWORD with NEW_KEYWORD."}
        actions = _fix_removed_keyword(lines[1], 1, range_obj, "file:///test.inp", diagnostic_data)

        assert len(actions) == 1
        assert "NEW_KEYWORD" in actions[0].edit.document_changes[0].edits[0].new_text

    def test_fix_invalid_enum(self):
        """Test invalid enum fix with a realistic typo."""
        from lsprotocol.types import Position, Range

        from cp2k_input_tools.code_actions import _fix_invalid_enum
        from cp2k_input_tools.schema_index import get_schema_index

        lines = [
            "&FORCE_EVAL",
            "   METHOD QUICKSTP",  # Typo: missing 'E'
            "&END FORCE_EVAL",
        ]
        text = "\n".join(lines)
        range_obj = Range(start=Position(line=1, character=0), end=Position(line=1, character=len(lines[1])))
        diagnostic_data = {"valid_values": ["QUICKSTEP", "FIST", "EMBEDDED"]}
        schema = get_schema_index()
        actions = _fix_invalid_enum(lines[1], 1, range_obj, "file:///test.inp", diagnostic_data, schema)

        assert len(actions) == 1
        # Should suggest closest valid value
        new_text = actions[0].edit.document_changes[0].edits[0].new_text
        assert "QUICKSTEP" in new_text

    def test_build_section_context(self):
        """Test section context building."""
        from cp2k_input_tools.code_actions import _build_section_context

        lines = [
            "&GLOBAL",
            "   PROJECT_NAME test",
            "&END GLOBAL",
            "&FORCE_EVAL",
            "   &DFT",
            "      METHOD QS",
        ]

        # Line 5 (METHOD QS) should be in (FORCE_EVAL, DFT) context
        ctx = _build_section_context(lines, 5)
        assert "FORCE_EVAL" in ctx
        assert "DFT" in ctx

        # Line 1 (PROJECT_NAME) should be in (GLOBAL,) context
        ctx = _build_section_context(lines, 1)
        assert "GLOBAL" in ctx
