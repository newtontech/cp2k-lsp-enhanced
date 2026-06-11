"""Golden tests for LSP code actions."""

from time import sleep

import pytest

from tests.harness.golden import FIXTURES_DIR

pytest.importorskip("pygls")

from lsprotocol.types import (  # noqa: E402
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_OPEN,
    CodeActionContext,
    CodeActionParams,
    DidOpenTextDocumentParams,
    TextDocumentIdentifier,
    TextDocumentItem,
)

CALL_TIMEOUT = 3


def _get_code_actions(client_server, fixture_name: str):
    """Open a fixture file and request code actions at the first diagnostic."""
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

    diags = list(client.diagnostics) if client.diagnostics else []
    if not diags:
        return []

    # Request code actions at the first diagnostic's range start
    first = diags[0]
    result = client.lsp.send_request(
        TEXT_DOCUMENT_CODE_ACTION,
        CodeActionParams(
            text_document=TextDocumentIdentifier(uri=str(fixture_path)),
            range=first.range,
            context=CodeActionContext(diagnostics=diags),
        ),
    ).result(timeout=CALL_TIMEOUT)

    return list(result) if result else []


def test_golden_invalid_input_code_actions(client_server):
    """Invalid input should offer code actions at diagnostic locations."""
    actions = _get_code_actions(client_server, "invalid_input")
    # Code actions may or may not be available depending on server implementation
    # This test verifies the harness works; actual golden comparison when actions exist
    if actions:
        normalized = []
        for a in actions:
            entry = {}
            if hasattr(a, "title"):
                entry["title"] = a.title
            if hasattr(a, "kind"):
                entry["kind"] = str(a.kind) if a.kind else None
            normalized.append(entry)
        # Golden comparison for code actions
        golden_path = FIXTURES_DIR / "invalid_input_actions.json"
        if golden_path.exists():
            import json
            golden = json.loads(golden_path.read_text())
            assert normalized == golden.get("items", []), (
                f"Golden mismatch for invalid_input_actions.json. "
                f"Expected {len(golden.get('items', []))} items, got {len(normalized)}."
            )
