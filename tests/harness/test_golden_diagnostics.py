"""Golden tests for LSP diagnostics."""

from time import sleep

import pytest

from tests.harness.golden import FIXTURES_DIR, assert_golden

pytest.importorskip("pygls")

from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_DID_OPEN,
    DidOpenTextDocumentParams,
    TextDocumentItem,
)

CALL_TIMEOUT = 3


def _get_diagnostics(client_server, fixture_name: str):
    """Open a fixture file and collect diagnostics from the LSP server."""
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

    diags = client.diagnostics if client.diagnostics else []
    return list(diags)


def test_golden_valid_input_diagnostics(client_server):
    """Valid CP2K input should produce zero diagnostics."""
    diags = _get_diagnostics(client_server, "valid_input")
    assert_golden("valid_input_diagnostics", diags)


def test_golden_invalid_input_diagnostics(client_server):
    """Invalid CP2K input should produce expected error diagnostics."""
    diags = _get_diagnostics(client_server, "invalid_input")
    # Verify we get at least one diagnostic
    assert len(diags) > 0, "Expected at least one diagnostic for invalid input"
    assert_golden("invalid_input_diagnostics", diags)
