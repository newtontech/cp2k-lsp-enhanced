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
    TEXT_DOCUMENT_HOVER,
    CompletionParams,
    DidOpenTextDocumentParams,
    HoverParams,
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

    assert len(server.lsp.workspace.text_documents) == 1
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
        len(server.lsp.workspace.text_documents) == 1
    ), f"More than one document open: {', '.join(server.lsp.workspace.text_documents.keys())}"
    assert "Validating CP2K input..." in client.msgs[0].message
    assert "Syntax error: unterminated string detected" in client.diagnostics[0].message


def _open_document(client, path, content):
    with open(path, "w", encoding="utf-8") as fhandle:
        fhandle.write(content)

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(text_document=TextDocumentItem(uri=str(path), language_id="cp2k", version=1, text=content)),
    )
    sleep(CALL_TIMEOUT)


def _completion_items(result):
    return result.items if hasattr(result, "items") else result


def _hover_text(hover):
    contents = hover.contents
    if hasattr(contents, "value"):
        return contents.value
    if isinstance(contents, list):
        return "\n".join(c.value if hasattr(c, "value") else str(c) for c in contents)
    return str(contents)


def test_completion_and_hover(client_server, tmp_path):
    client, _ = client_server
    doc_path = tmp_path / "completion_hover.inp"
    content = (
        "&F\n"
        "&GLOBAL\n"
        "  RUN_\n"
        "  RUN_TYPE \n"
        "&END GLOBAL\n"
    )
    _open_document(client, doc_path, content)

    section_result = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(uri=str(doc_path)),
            position=Position(line=0, character=2),
        ),
    ).result(timeout=CALL_TIMEOUT)
    section_items = _completion_items(section_result)
    assert any(item.label == "&FORCE_EVAL" for item in section_items)

    keyword_result = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(uri=str(doc_path)),
            position=Position(line=2, character=7),
        ),
    ).result(timeout=CALL_TIMEOUT)
    keyword_items = _completion_items(keyword_result)
    assert any(item.label == "RUN_TYPE" for item in keyword_items)

    value_result = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        CompletionParams(
            text_document=TextDocumentIdentifier(uri=str(doc_path)),
            position=Position(line=3, character=11),
        ),
    ).result(timeout=CALL_TIMEOUT)
    value_items = _completion_items(value_result)
    assert any(item.label == "ENERGY" for item in value_items)

    hover = client.lsp.send_request(
        TEXT_DOCUMENT_HOVER,
        HoverParams(
            text_document=TextDocumentIdentifier(uri=str(doc_path)),
            position=Position(line=3, character=4),
        ),
    ).result(timeout=CALL_TIMEOUT)

    assert hover is not None
    assert "RUN_TYPE" in _hover_text(hover)


@pytest.mark.script_launch_mode("subprocess")
def test_cli(script_runner):
    """Simply check whether the server reacts to an exist notification"""
    stdin = io.StringIO('Content-Length: 45\r\n\r\n{"method":"exit","jsonrpc":"2.0","params":{}}')

    ret = script_runner.run("cp2k-language-server", stdin=stdin)

    assert ret.stderr == ""
    assert ret.success
