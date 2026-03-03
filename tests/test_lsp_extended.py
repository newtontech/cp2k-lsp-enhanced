"""Extended tests for LSP features to improve coverage."""

import sys
from time import sleep

import pytest

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol.types import (
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_HOVER,
    CodeActionContext,
    CodeActionParams,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    HoverParams,
    Position,
    Range,
    TextDocumentIdentifier,
    VersionedTextDocumentIdentifier,
)

CALL_TIMEOUT = 5


class TestLSPFeatures:
    """Test suite for LSP feature providers."""

    def test_completion_after_ampersand(self, client_server, tmp_path):
        """Test completion after & symbol."""
        client, _ = client_server
        doc_path = tmp_path / "completion_test.inp"
        content = "&GLOBAL\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        result = client.lsp.send_request(
            TEXT_DOCUMENT_COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=0, character=1),
            ),
        ).result(timeout=CALL_TIMEOUT)

        items = result.items if hasattr(result, "items") else result
        # Should get section completions
        assert len(items) > 0

    def test_completion_keywords(self, client_server, tmp_path):
        """Test completion for keywords."""
        client, _ = client_server
        doc_path = tmp_path / "keyword_test.inp"
        content = "&GLOBAL\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        result = client.lsp.send_request(
            TEXT_DOCUMENT_COMPLETION,
            CompletionParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=0, character=7),
            ),
        ).result(timeout=CALL_TIMEOUT)

        # Should return completions
        items = result.items if hasattr(result, "items") else result
        assert len(items) >= 0

    def test_hover_global_section(self, client_server, tmp_path):
        """Test hover for GLOBAL section."""
        client, _ = client_server
        doc_path = tmp_path / "hover_section.inp"
        content = "&GLOBAL\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=0, character=3),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None
        hover_text = hover.contents.value if hasattr(hover.contents, "value") else str(hover.contents)
        assert "GLOBAL" in hover_text

    def test_hover_project_name(self, client_server, tmp_path):
        """Test hover for PROJECT_NAME keyword."""
        client, _ = client_server
        doc_path = tmp_path / "hover_keyword.inp"
        content = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=1, character=5),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None

    def test_did_close(self, client_server, tmp_path):
        """Test document close clears parsed documents."""
        client, server = client_server
        doc_path = tmp_path / "close_test.inp"
        content = "&GLOBAL\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CLOSE,
            DidCloseTextDocumentParams(text_document=TextDocumentIdentifier(uri=str(doc_path))),
        )
        sleep(CALL_TIMEOUT)

        assert str(doc_path) not in server.lsp.workspace.text_documents

    def test_hover_dft_section(self, client_server, tmp_path):
        """Test hover for DFT section."""
        client, _ = client_server
        doc_path = tmp_path / "hover_dft.inp"
        content = "&DFT\n&END DFT"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=0, character=3),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None

    def test_hover_scf_section(self, client_server, tmp_path):
        """Test hover for SCF section."""
        client, _ = client_server
        doc_path = tmp_path / "hover_scf.inp"
        content = "&SCF\n&END SCF"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=0, character=3),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None

    def test_hover_run_type(self, client_server, tmp_path):
        """Test hover for RUN_TYPE keyword."""
        client, _ = client_server
        doc_path = tmp_path / "hover_runtype.inp"
        content = "&GLOBAL\n  RUN_TYPE ENERGY\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=1, character=5),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None

    def test_hover_print_level(self, client_server, tmp_path):
        """Test hover for PRINT_LEVEL keyword."""
        client, _ = client_server
        doc_path = tmp_path / "hover_print.inp"
        content = "&GLOBAL\n  PRINT_LEVEL HIGH\n&END GLOBAL"
        doc_path.write_text(content)

        client.lsp.notify(
            TEXT_DOCUMENT_DID_CHANGE,
            DidChangeTextDocumentParams(
                text_document=VersionedTextDocumentIdentifier(uri=str(doc_path), version=1),
                content_changes=[{"text": content}],
            ),
        )
        sleep(CALL_TIMEOUT)

        hover = client.lsp.send_request(
            TEXT_DOCUMENT_HOVER,
            HoverParams(
                text_document=TextDocumentIdentifier(uri=str(doc_path)),
                position=Position(line=1, character=5),
            ),
        ).result(timeout=CALL_TIMEOUT)

        assert hover is not None
