import io
import sys
from time import sleep

import pytest

from . import TEST_DIR

if hasattr(sys, "pypy_version_info"):
    # the LSP implementation seems to behave completely different on pypy
    pytest.skip("pypy is currently not supported", allow_module_level=True)


pygls = pytest.importorskip("pygls")


from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_OPEN,
    CompletionParams,
    DidOpenTextDocumentParams,
    Position,
    TextDocumentIdentifier,
    TextDocumentItem,
)

CALL_TIMEOUT = 5


def test_text_document_did_open(client_server):
    """Check that the server opens an input file"""
    client, server = client_server

    testpath = TEST_DIR / "inputs" / "test01.inp"
    with testpath.open("r") as fhandle:
        content = fhandle.read()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(testpath), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    assert len(server.lsp.workspace.documents) == 1
    assert "Validating CP2K input..." in client.msgs[0].message
    assert client.diagnostics is not None and not client.diagnostics, "Diagnostics is not empty as expected"


def test_text_document_did_open_error(client_server):
    """Check that the server opens an input file with a syntax error"""
    client, server = client_server

    testpath = TEST_DIR / "inputs" / "unterminated_string.inp"
    with testpath.open("r") as fhandle:
        content = fhandle.read()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(testpath), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    assert (
        len(server.lsp.workspace.documents) == 1
    ), f"More than one document open: {', '.join(server.lsp.workspace.documents.keys())}"
    assert "Validating CP2K input..." in client.msgs[0].message
    assert "Syntax error: unterminated string detected" in client.diagnostics[0].message


@pytest.mark.script_launch_mode("subprocess")
def test_cli(script_runner):
    """Simply check whether the server reacts to an exist notification"""
    stdin = io.StringIO('Content-Length: 45\r\n\r\n{"method":"exit","jsonrpc":"2.0","params":{}}')

    ret = script_runner.run("cp2k-language-server", stdin=stdin)

    assert ret.stderr == ""
    assert ret.success


def test_completion_sections(client_server):
    """Check that completion returns sections when typing &"""
    client, server = client_server

    testpath = TEST_DIR / "inputs" / "test01.inp"
    with testpath.open("r") as fhandle:
        content = fhandle.read()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(testpath), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    # Request completion at the start of the file (should give root-level sections)
    result = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(uri=str(testpath)),
            position=Position(line=0, character=1),
        ),
    ).result(timeout=CALL_TIMEOUT)

    # Should return a completion list
    assert result is not None
    items = result.items if hasattr(result, "items") else result
    assert len(items) > 0, "Expected completion items for root section"


def test_completion_keywords(client_server):
    """Check that completion returns keywords within a section"""
    client, server = client_server

    # Create a simple input with a FORCE_EVAL section
    content = "&FORCE_EVAL\n\n&END FORCE_EVAL\n"

    testpath = TEST_DIR / "inputs" / "completion_test.inp"
    with open(testpath, "w") as f:
        f.write(content)

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(testpath), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)

    # Request completion inside FORCE_EVAL section (line 1, empty line)
    result = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(uri=str(testpath)),
            position=Position(line=1, character=0),
        ),
    ).result(timeout=CALL_TIMEOUT)

    assert result is not None
    items = result.items if hasattr(result, "items") else result
    # Should have keywords available in FORCE_EVAL section
    assert len(items) > 0, "Expected completion items inside FORCE_EVAL"
