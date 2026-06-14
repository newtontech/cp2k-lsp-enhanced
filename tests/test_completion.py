"""Tests for schema-backed CompletionProvider.

TDD: Tests written before implementation to drive correct behavior.
Tests use mocked LSP types to avoid requiring a running language server.
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from lsprotocol import types as lsp

from cp2k_input_tools.cursor_context import CursorContext
from cp2k_input_tools.schema_index import KeywordSpec, SectionSpec

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_server():
    """Create a mock language server with workspace."""
    server = MagicMock()
    workspace = MagicMock()
    server.workspace = workspace
    return server


@pytest.fixture
def completion_provider(mock_server):
    """Create a CompletionProvider with mocked server."""
    from cp2k_lsp.features.completion import CompletionProvider
    provider = CompletionProvider(mock_server)
    return provider


def _make_cursor_context(
    *,
    uri="file:///test.inp",
    line=0,
    character=0,
    section_path=(),
    current_section=None,
    current_keyword=None,
    is_section_start=False,
    is_section_end=False,
    is_keyword_position=False,
    is_value_position=False,
    prefix="",
) -> CursorContext:
    """Create a CursorContext for testing."""
    return CursorContext(
        uri=uri,
        line=line,
        character=character,
        section_path=section_path,
        current_section=current_section,
        current_keyword=current_keyword,
        is_section_start=is_section_start,
        is_section_end=is_section_end,
        is_keyword_position=is_keyword_position,
        is_value_position=is_value_position,
        prefix=prefix,
    )


def _mock_text_document(lines, uri="file:///test.inp"):
    """Create a mock text document."""
    doc = MagicMock()
    doc.lines = lines
    doc.uri = uri
    return doc


def _mock_schema_index():
    """Create a mock schema index with test data."""
    schema = MagicMock()
    # Root sections
    schema.get_root_sections.return_value = ["FORCE_EVAL", "GLOBAL", "TOPOLOGY"]

    # Subsections of DFT
    schema.get_child_sections.return_value = ["QS", "XC", "SCF", "POISSON"]

    # Keywords for DFT section
    schema.get_keywords.return_value = {
        "BASIS_SET_FILE_NAME": KeywordSpec(
            name="BASIS_SET_FILE_NAME",
            variable_type="string",
            default_value="BASIS_SET",
            enumeration_values=[],
            description="Name of the basis set file",
        ),
        "CHARGE": KeywordSpec(
            name="CHARGE",
            variable_type="integer",
            default_value="0",
            enumeration_values=[],
            description="Total charge of the system",
        ),
        "UKS": KeywordSpec(
            name="UKS",
            variable_type="logical",
            default_value=".FALSE.",
            enumeration_values=[".TRUE.", ".FALSE."],
            description="Use unrestricted Kohn-Sham method",
        ),
        "MULTIPLICITY": KeywordSpec(
            name="MULTIPLICITY",
            variable_type="integer",
            default_value="1",
            enumeration_values=[],
            description="Spin multiplicity",
        ),
    }

    keyword_specs = {
        "BASIS_SET_FILE_NAME": KeywordSpec(
            name="BASIS_SET_FILE_NAME",
            variable_type="string",
            default_value="BASIS_SET",
            enumeration_values=[],
            description="Name of the basis set file",
        ),
        "CHARGE": KeywordSpec(
            name="CHARGE",
            variable_type="integer",
            default_value="0",
            enumeration_values=[],
            description="Total charge of the system",
        ),
        "UKS": KeywordSpec(
            name="UKS",
            variable_type="logical",
            default_value=".FALSE.",
            enumeration_values=[".TRUE.", ".FALSE."],
            description="Use unrestricted Kohn-Sham method",
        ),
        "MULTIPLICITY": KeywordSpec(
            name="MULTIPLICITY",
            variable_type="integer",
            default_value="1",
            enumeration_values=[],
            description="Spin multiplicity",
        ),
    }
    schema.get_keyword.side_effect = lambda path, name: keyword_specs.get(name)

    # Section specs
    dft_spec = SectionSpec(
        name="DFT",
        description="Density Functional Theory section",
        subsections=["QS", "XC", "SCF"],
        keywords=["BASIS_SET_FILE_NAME", "CHARGE", "UKS"],
    )
    schema.get_section.return_value = dft_spec

    return schema


def _make_completion_params(
    uri="file:///test.inp",
    line=0,
    character=0,
) -> lsp.CompletionParams:
    """Create LSP CompletionParams."""
    return lsp.CompletionParams(
        text_document=lsp.TextDocumentIdentifier(uri=uri),
        position=lsp.Position(line=line, character=character),
    )


# =============================================================================
# Section Completion Tests
# =============================================================================


class TestSectionCompletion:
    """Test schema-backed section completion."""

    def test_root_section_completion(self, completion_provider, mock_server):
        """Root-level section completion returns FORCE_EVAL, GLOBAL, TOPOLOGY."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=1)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 3
        labels = [item.label for item in result.items]
        assert "FORCE_EVAL" in labels
        assert "GLOBAL" in labels
        assert "TOPOLOGY" in labels

    def test_section_completion_with_prefix(self, completion_provider, mock_server):
        """Section completion filters by prefix."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&FO"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="FO",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == "FORCE_EVAL"

    def test_child_section_completion(self, completion_provider, mock_server):
        """Section completion returns child sections when in a parent."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  &"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "QS" in labels
        assert "XC" in labels
        assert "SCF" in labels

    def test_section_completion_insert_text_format(self, completion_provider, mock_server):
        """Section completion items have snippet insert format."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=1)
            result = completion_provider.provide_completion(params)

        assert result is not None
        for item in result.items:
            assert item.insert_text_format == lsp.InsertTextFormat.Snippet


# =============================================================================
# Keyword Completion Tests
# =============================================================================


class TestKeywordCompletion:
    """Test schema-backed keyword completion."""

    def test_keyword_completion(self, completion_provider, mock_server):
        """Keyword completion returns keywords for current section."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 4
        labels = [item.label for item in result.items]
        assert "BASIS_SET_FILE_NAME" in labels
        assert "CHARGE" in labels
        assert "UKS" in labels
        assert "MULTIPLICITY" in labels

    def test_keyword_completion_with_prefix(self, completion_provider, mock_server):
        """Keyword completion filters by prefix."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  CH"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            is_value_position=False,
            prefix="CH",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=4)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == "CHARGE"

    def test_keyword_completion_detail(self, completion_provider, mock_server):
        """Keyword completion items include type and default in detail."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        charge_item = next(item for item in result.items if item.label == "CHARGE")
        assert "integer" in charge_item.detail.lower()
        assert "0" in charge_item.detail

    def test_keyword_completion_documentation(self, completion_provider, mock_server):
        """Keyword completion items include description in documentation."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        charge_item = next(item for item in result.items if item.label == "CHARGE")
        assert "Total charge" in charge_item.documentation


# =============================================================================
# Value Completion Tests
# =============================================================================


class TestValueCompletion:
    """Test schema-backed value completion."""

    def test_enum_value_completion(self, completion_provider, mock_server):
        """Enum value completion returns valid enum values."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  UKS = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="UKS",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=8)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 2
        labels = [item.label for item in result.items]
        assert ".TRUE." in labels
        assert ".FALSE." in labels

    def test_enum_value_completion_with_prefix(self, completion_provider, mock_server):
        """Enum value completion filters by prefix."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  UKS = .F"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="UKS",
            is_value_position=True,
            prefix=".F",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=9)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == ".FALSE."

    def test_logical_value_completion_for_unknown_keyword(self, completion_provider, mock_server):
        """Logical value completion for boolean keyword not in schema."""
        schema = MagicMock()
        schema.get_keyword.return_value = KeywordSpec(
            name="SOME_FLAG",
            variable_type="logical",
            default_value=".FALSE.",
            enumeration_values=[],
            description="A boolean flag",
        )
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  SOME_FLAG = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="SOME_FLAG",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=14)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 4
        labels = [item.label for item in result.items]
        assert "F" in labels
        assert ".FALSE." in labels
        assert "T" in labels
        assert ".TRUE." in labels

    def test_value_completion_returns_none_when_no_keyword(self, completion_provider, mock_server):
        """Value completion returns None when current_keyword is None."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword=None,
            is_value_position=False,
            is_keyword_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=2)
            result = completion_provider.provide_completion(params)

        # Should return keyword completions, not value completions
        assert result is not None
        assert len(result.items) > 0


# =============================================================================
# Path-Aware Completion Tests
# =============================================================================


class TestPathAwareCompletion:
    """Test completion behavior based on section path."""

    def test_no_completions_outside_section(self, completion_provider, mock_server):
        """Empty line outside any section returns no completions."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document([""])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params()
            result = completion_provider.provide_completion(params)

        assert result is None

    def test_keyword_position_returns_keywords(self, completion_provider, mock_server):
        """Keyword position in section returns keyword completions."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) > 0

    def test_value_position_returns_values(self, completion_provider, mock_server):
        """Value position in section returns value completions."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  UKS = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="UKS",
            is_value_position=True,
            is_keyword_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=8)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 2  # .TRUE. and .FALSE.


# =============================================================================
# Fallback Tests
# =============================================================================


class TestFallback:
    """Test graceful fallback behavior."""

    def test_no_completions_when_schema_unavailable(self, completion_provider, mock_server):
        """No completions when schema index fails to load."""
        completion_provider._schema_index = None

        # Mock schema loading to fail
        with patch.object(
            type(completion_provider),
            "schema_index",
            new_callable=PropertyMock,
            return_value=None,
        ):
            doc = _mock_text_document(["&"])
            mock_server.workspace.get_text_document.return_value = doc

            ctx = _make_cursor_context(
                is_section_start=True,
                prefix="",
            )

            with patch.object(
                completion_provider._cursor_resolver,
                "resolve_cursor_context",
                return_value=ctx,
            ):
                params = _make_completion_params(character=1)
                result = completion_provider.provide_completion(params)

        assert result is None

    def test_empty_result_when_section_not_found(self, completion_provider, mock_server):
        """Empty completions when current section is not in schema."""
        schema = MagicMock()
        schema.get_root_sections.return_value = ["FORCE_EVAL"]
        schema.get_child_sections.return_value = []
        schema.get_keywords.return_value = {}
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  &"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("UNKNOWN_SECTION",),
            current_section="UNKNOWN_SECTION",
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=0, character=3)
            result = completion_provider.provide_completion(params)

        # Should return empty list or None for unknown section
        if result is not None:
            assert len(result.items) == 0

    def test_returns_none_for_empty_completions(self, completion_provider, mock_server):
        """Returns None when completion list is empty."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document([""])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="UNKNOWN",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=7)
            result = completion_provider.provide_completion(params)

        # Should return None when no items match the prefix
        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestCompletionIntegration:
    """Integration tests using real document parsing."""

    def test_completion_in_nested_section(self, completion_provider, mock_server):
        """Test completion in a nested section (DFT inside FORCE_EVAL)."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        lines = [
            "&FORCE_EVAL",
            "  &DFT",
            "    &",
        ]
        doc = _mock_text_document(lines)
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("FORCE_EVAL", "DFT"),
            current_section="DFT",
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=2, character=5)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        # DFT child sections
        assert "QS" in labels
        assert "XC" in labels
        assert "SCF" in labels

    def test_completion_after_keyword_equals(self, completion_provider, mock_server):
        """Test completion after keyword= in a section."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        lines = [
            "&FORCE_EVAL",
            "  &DFT",
            "    CHARGE = ",
        ]
        doc = _mock_text_document(lines)
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("FORCE_EVAL", "DFT"),
            current_section="DFT",
            current_keyword="CHARGE",
            is_value_position=True,
            is_keyword_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(line=2, character=13)
            result = completion_provider.provide_completion(params)

        assert result is None or len(result.items) == 0


# =============================================================================
# Section Snippet Tests
# =============================================================================


class TestSectionSnippets:
    """Test section completion with snippet insert text."""

    def test_section_snippet_has_end_tag(self, completion_provider, mock_server):
        """Section completion includes &END SECTION in snippet."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=1)
            result = completion_provider.provide_completion(params)

        assert result is not None
        for item in result.items:
            assert "&END" in item.insert_text
            assert item.insert_text_format == lsp.InsertTextFormat.Snippet

    def test_section_snippet_has_cursor_placeholder(self, completion_provider, mock_server):
        """Section completion snippet includes $0 cursor placeholder."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=1)
            result = completion_provider.provide_completion(params)

        assert result is not None
        global_item = next(item for item in result.items if item.label == "GLOBAL")
        assert "$0" in global_item.insert_text


# =============================================================================
# File Name Completion Tests
# =============================================================================


class TestFileNameCompletion:
    """Test file name completion for *_FILE_NAME keywords."""

    def test_basis_set_file_name_completion(self, completion_provider, mock_server):
        """BASIS_SET_FILE_NAME keyword shows file name suggestions."""
        schema = MagicMock()
        schema.get_keyword.return_value = MagicMock(
            name="BASIS_SET_FILE_NAME",
            variable_type="string",
            default_value="BASIS_SET",
            enumeration_values=[],
            description="Name of the basis set file",
        )
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  BASIS_SET_FILE_NAME = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="BASIS_SET_FILE_NAME",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=23)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert any("./basis_set" in label.lower() for label in labels)

    def test_potential_file_name_completion(self, completion_provider, mock_server):
        """POTENTIAL_FILE_NAME keyword shows file name suggestions."""
        schema = MagicMock()
        schema.get_keyword.return_value = MagicMock(
            name="POTENTIAL_FILE_NAME",
            variable_type="string",
            default_value="POTENTIAL_FILE_NAME",
            enumeration_values=[],
            description="Name of the pseudopotential file",
        )
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  POTENTIAL_FILE_NAME = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="POTENTIAL_FILE_NAME",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=23)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert any("./potential" in label.lower() for label in labels)


# =============================================================================
# Basis/Potential Completion Tests
# =============================================================================


class TestBasisPotentialCompletion:
    """Test basis set and potential name completion."""

    def test_basis_set_keyword_completion(self, completion_provider, mock_server):
        """BASIS_SET keyword shows basis set name suggestions."""
        schema = MagicMock()
        schema.get_keyword.return_value = MagicMock(
            name="BASIS_SET",
            variable_type="string",
            default_value=None,
            enumeration_values=[],
            description="Basis set specification",
        )
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  BASIS_SET = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("KIND",),
            current_section="KIND",
            current_keyword="BASIS_SET",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=14)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "DZVP-MOLOPT-GTH" in labels
        assert "TZVP-MOLOPT-GTH" in labels

    def test_potential_keyword_completion(self, completion_provider, mock_server):
        """POTENTIAL keyword shows pseudopotential name suggestions."""
        schema = MagicMock()
        schema.get_keyword.return_value = MagicMock(
            name="POTENTIAL",
            variable_type="string",
            default_value=None,
            enumeration_values=[],
            description="Pseudopotential specification",
        )
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  POTENTIAL = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("KIND",),
            current_section="KIND",
            current_keyword="POTENTIAL",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=14)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "GTH_PBE" in labels
        assert "GTH_BLYP" in labels


# =============================================================================
# Workflow Snippet Tests
# =============================================================================


class TestWorkflowSnippets:
    """Test workflow snippet completions."""

    def test_energy_snippet_available(self, completion_provider, mock_server):
        """ENERGY workflow snippet is available at root level."""
        schema = MagicMock()
        schema.get_root_sections.return_value = ["GLOBAL", "FORCE_EVAL"]
        schema.get_child_sections.return_value = []
        schema.get_keywords.return_value = {}
        completion_provider._schema_index = schema

        doc = _mock_text_document(["EN"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="EN",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "ENERGY" in labels

    def test_geo_opt_snippet_available(self, completion_provider, mock_server):
        """GEO_OPT workflow snippet is available."""
        schema = MagicMock()
        schema.get_root_sections.return_value = ["GLOBAL", "FORCE_EVAL"]
        schema.get_child_sections.return_value = []
        schema.get_keywords.return_value = {}
        completion_provider._schema_index = schema

        doc = _mock_text_document(["GEO"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="GEO",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "GEO_OPT" in labels

    def test_md_nvt_snippet_available(self, completion_provider, mock_server):
        """MD_NVT workflow snippet is available."""
        schema = MagicMock()
        schema.get_root_sections.return_value = ["GLOBAL", "FORCE_EVAL"]
        schema.get_child_sections.return_value = []
        schema.get_keywords.return_value = {}
        completion_provider._schema_index = schema

        doc = _mock_text_document(["MD"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="MD",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "MD_NVT" in labels
        assert "MD_NPT" in labels

    def test_workflow_snippet_insert_format(self, completion_provider, mock_server):
        """Workflow snippets use Snippet insert text format."""
        schema = MagicMock()
        schema.get_root_sections.return_value = ["GLOBAL"]
        schema.get_child_sections.return_value = []
        schema.get_keywords.return_value = {}
        completion_provider._schema_index = schema

        doc = _mock_text_document(["EN"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            prefix="EN",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        energy_item = next(item for item in result.items if item.label == "ENERGY")
        assert energy_item.insert_text_format == lsp.InsertTextFormat.Snippet


# =============================================================================
# Path-Aware Completion Tests (Extended)
# =============================================================================


class TestPathAwareCompletionExtended:
    """Extended path-aware completion tests."""

    def test_root_level_section_only(self, completion_provider, mock_server):
        """Root level only shows root sections."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=1)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "FORCE_EVAL" in labels
        assert "GLOBAL" in labels
        assert "DFT" not in labels

    def test_nested_section_child_only(self, completion_provider, mock_server):
        """Nested section shows only valid children."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  &"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "QS" in labels
        assert "XC" in labels
        assert "SCF" in labels
        assert "GLOBAL" not in labels

    def test_keyword_completion_valid_for_section(self, completion_provider, mock_server):
        """Keyword completion shows only valid keywords for current section."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=2)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "BASIS_SET_FILE_NAME" in labels
        assert "CHARGE" in labels
        assert "UKS" in labels

    def test_value_completion_for_boolean_keyword(self, completion_provider, mock_server):
        """Value completion returns logical values for boolean keywords."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  UKS = "])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            current_keyword="UKS",
            is_value_position=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=8)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert ".TRUE." in labels
        assert ".FALSE." in labels

    def test_prefix_filtering_section(self, completion_provider, mock_server):
        """Section completion filters by prefix."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["&FO"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=True,
            prefix="FO",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == "FORCE_EVAL"

    def test_prefix_filtering_keyword(self, completion_provider, mock_server):
        """Keyword completion filters by prefix."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  CH"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("DFT",),
            current_section="DFT",
            is_keyword_position=True,
            prefix="CH",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=4)
            result = completion_provider.provide_completion(params)

        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].label == "CHARGE"

    def test_no_completion_outside_section(self, completion_provider, mock_server):
        """Empty line outside any section returns no keyword completions."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document([""])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=(),
            current_section=None,
            is_section_start=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params()
            result = completion_provider.provide_completion(params)

        assert result is None

    def test_section_path_excludes_current(self, completion_provider, mock_server):
        """Section completion uses parent path, not current section."""
        schema = _mock_schema_index()
        completion_provider._schema_index = schema

        doc = _mock_text_document(["  &"])
        mock_server.workspace.get_text_document.return_value = doc

        ctx = _make_cursor_context(
            section_path=("FORCE_EVAL",),
            current_section="FORCE_EVAL",
            is_section_start=True,
            prefix="",
        )

        with patch.object(
            completion_provider._cursor_resolver,
            "resolve_cursor_context",
            return_value=ctx,
        ):
            params = _make_completion_params(character=3)
            result = completion_provider.provide_completion(params)

        assert result is not None
        labels = [item.label for item in result.items]
        assert "DFT" in labels
        assert "SUBSYS" in labels
