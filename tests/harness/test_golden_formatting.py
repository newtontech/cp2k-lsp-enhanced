"""Golden tests for LSP formatting."""

import pathlib
from time import sleep

import pytest

from tests.harness.golden import FIXTURES_DIR, assert_golden, normalize_diagnostics, normalize_text_edits

pytest.importorskip("pygls")

from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_FORMATTING,
    DidOpenTextDocumentParams,
    DocumentFormattingParams,
    TextDocumentIdentifier,
    TextDocumentItem,
)

CALL_TIMEOUT = 3


def _get_formatting_edits(client_server, fixture_name: str):
    """Open a fixture file and request formatting edits."""
    client, server = client_server
    fixture_path = FIXTURES_DIR / f"{fixture_name}.inp"
    content = fixture_path.read_text()

    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                uri=str(fixture_path),
                language_id="cp2k",
                version=1,
                text=content,
            )
        ),
    )
    sleep(CALL_TIMEOUT)

    result = client.lsp.send_request(
        TEXT_DOCUMENT_FORMATTING,
        DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri=str(fixture_path)),
            options={},
        ),
    ).result(timeout=CALL_TIMEOUT)

    return list(result) if result else []


def test_golden_messy_formatting_edits(client_server):
    """Formatting messy input should produce deterministic TextEdits."""
    edits = _get_formatting_edits(client_server, "messy_formatting")
    assert len(edits) > 0, "Expected formatting edits for messy input"
    assert_golden("messy_formatting_edits", edits)
