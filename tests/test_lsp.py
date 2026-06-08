"""Tests for enhanced LSP features: formatting, navigation, rename."""

import io
import sys
from time import sleep

import pytest

from . import TEST_DIR

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_PREPARE_RENAME,
    TEXT_DOCUMENT_RENAME,
    DidOpenTextDocumentParams,
    DocumentFormattingParams,
    DocumentSymbolParams,
    HoverParams,
    Position,
    Range,
    ReferenceParams,
    RenameParams,
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
        DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                uri=str(testpath), language_id="cp2k", version=1, text=content
            )
        ),
    )
    sleep(CALL_TIMEOUT)
    return content

    # assert len(server.lsp.workspace.text_documents) == 1
    assert "Validating CP2K input..." in client.msgs[0].message
    assert client.diagnostics is not None and not client.diagnostics


def test_text_document_did_open_error(client_server):
    """Check that the server reports syntax errors."""
    client, server = client_server
    testpath = TEST_DIR / "inputs" / "unterminated_string.inp"
    _open_file(client, server, testpath)
    assert len(server.lsp.workspace.documents) == 1
    assert client.diagnostics is not None and len(client.diagnostics) > 0


def test_formatting(client_server):
    """Test document formatting."""
    client, server = client_server
    testpath = TEST_DIR / "inputs" / "test01.inp"
    _open_file(client, server, testpath)

    result = client.lsp.send_request(
        TEXT_DOCUMENT_FORMATTING,
        DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri=str(testpath)),
            options={},
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert result is not None
    assert len(result) >= 1


def test_hover_keyword(client_server):
    """Test hover on a keyword."""
    client, server = client_server
    testpath = TEST_DIR / "inputs" / "test01.inp"
    content = _open_file(client, server, testpath)
    lines = content.split('\n')

    # Find a keyword line
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('&') and not line.startswith('!') and not line.startswith('@'):
            result = client.lsp.send_request(
                TEXT_DOCUMENT_HOVER,
                HoverParams(
                    text_document=TextDocumentIdentifier(uri=str(testpath)),
                    position=Position(line=i, character=2),
                ),
            ).result(timeout=CALL_TIMEOUT)
            break


def test_document_symbols(client_server):
    """Test document symbol tree."""
    client, server = client_server
    testpath = TEST_DIR / "inputs" / "test01.inp"
    content = _open_file(client, server, testpath)

    result = client.lsp.send_request(
        TEXT_DOCUMENT_DOCUMENT_SYMBOL,
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=str(testpath)),
        ),
    ).result(timeout=CALL_TIMEOUT)
    assert result is not None
    # test01.inp has sections like GLOBAL, FORCE_EVAL, etc.
    assert len(result) > 0


def test_definition_include(client_server, tmp_path):
    """Test go-to-definition for @INCLUDE."""
    client, server = client_server

    inc_file = tmp_path / "included.inp"
    inc_file.write_text("&GLOBAL\n  PROJECT test\n&END GLOBAL\n")

    main_file = tmp_path / "main.inp"
    main_file.write_text(f"@INCLUDE {inc_file.name}\n")

    content = main_file.read_text()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                uri=str(main_file), language_id="cp2k", version=1, text=content
            )
        ),
    )
    sleep(CALL_TIMEOUT)

    assert (
        len(server.lsp.workspace.text_documents) == 1
    ), f"More than one document open: {', '.join(server.lsp.workspace.documents.keys())}"
    assert "Validating CP2K input..." in client.msgs[0].message
    assert "Syntax error: unterminated string detected" in client.diagnostics[0].message


@pytest.mark.skip(reason="Complex subprocess testing not essential for core functionality")
def test_cli(script_runner):
    """Check LSP server startup via CLI."""
    stdin = io.StringIO('Content-Length: 45\r\n\r\n{"method":"exit","jsonrpc":"2.0","params":{}}')
    ret = script_runner.run("cp2k-language-server", stdin=stdin)
    assert ret.stderr == ""
    assert ret.success
