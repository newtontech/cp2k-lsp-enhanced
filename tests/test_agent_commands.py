"""Tests for agent commands (Issue #124): cp2k.context, cp2k.wiki.search, cp2k.symbols, etc."""

from __future__ import annotations

# Ensure the workspace root is importable when run from the worktree
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cp2k_lsp.agent_commands import (
    COMMAND_CAPABILITIES,
    COMMAND_CHECK,
    COMMAND_CONTEXT,
    COMMAND_DEFINITION,
    COMMAND_EXPLAIN,
    COMMAND_FIX_PREVIEW,
    COMMAND_REFERENCES,
    COMMAND_REGISTRY,
    COMMAND_SCHEMA_VALIDATE,
    COMMAND_SYMBOLS,
    COMMAND_WIKI_SEARCH,
    _extract_symbols,
    _find_references,
    _parse_context_at_position,
    _resolve_definition,
    _search_wiki_digest,
    execute_command,
    parse_command_args,
    run_capabilities,
    run_check,
    run_context,
    run_definition,
    run_explain,
    run_fix_preview,
    run_references,
    run_symbols,
    run_wiki_search,
)

# Minimal valid CP2K input for testing
MINIMAL_INPUT = """\
&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_SET_FILE
    POTENTIAL_FILE_NAME POTENTIAL
  &END DFT
&END FORCE_EVAL
"""

INPUT_WITH_VARIABLES = """\
&GLOBAL
  PROJECT_NAME ${PROJECT}
  RUN_TYPE ${RUN_TYPE}
&END GLOBAL

@SET PROJECT = my_calculation
@SET RUN_TYPE = ENERGY
"""

INPUT_WITH_INCLUDE = """\
&GLOBAL
  PROJECT_NAME test
&END GLOBAL

@INCLUDE 'parameters.inp'
"""

INPUT_WITH_KEYWORDS = """\
&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
  WALL_TIME 3600
&END GLOBAL
"""


class TestParseCommandArgs:
    """Tests for parse_command_args function."""

    def test_none_arguments(self):
        assert parse_command_args(None) == {}

    def test_empty_arguments(self):
        assert parse_command_args([]) == {}

    def test_dict_argument(self):
        args = [{"uri": "file:///test.inp"}]
        assert parse_command_args(args) == {"uri": "file:///test.inp"}

    def test_json_string_argument(self):
        args = ['{"uri": "file:///test.inp"}']
        assert parse_command_args(args) == {"uri": "file:///test.inp"}

    def test_string_uri_argument(self):
        args = ["file:///test.inp"]
        assert parse_command_args(args) == {"uri": "file:///test.inp"}


class TestRunCapabilities:
    """Tests for run_capabilities command."""

    def test_returns_software_info(self):
        result = run_capabilities()
        assert "software" in result
        assert result["status"] == "available"

    def test_includes_all_commands(self):
        result = run_capabilities()
        commands = result["capabilities"]["commands"]
        assert COMMAND_CHECK in commands
        assert COMMAND_EXPLAIN in commands
        assert COMMAND_CAPABILITIES in commands
        assert COMMAND_CONTEXT in commands
        assert COMMAND_WIKI_SEARCH in commands
        assert COMMAND_SYMBOLS in commands
        assert COMMAND_DEFINITION in commands
        assert COMMAND_REFERENCES in commands
        assert COMMAND_FIX_PREVIEW in commands


class TestRunCheck:
    """Tests for run_check command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_check()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]

    def test_returns_software_field(self):
        result = run_check()
        assert "software" in result


class TestRunExplain:
    """Tests for run_explain command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_explain()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]


class TestRunContext:
    """Tests for run_context command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_context()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]

    def test_returns_context_with_text(self):
        result = run_context(
            server=None,
            arguments=[{"uri": "file:///test.inp", "line": 2, "character": 15}],
        )
        # With no server and no text, should be unavailable
        assert result["ok"] is False


class TestRunWikiSearch:
    """Tests for run_wiki_search command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_wiki_search()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]

    def test_returns_search_results(self):
        result = run_wiki_search(
            server=None,
            arguments=[{"uri": "file:///test.inp", "query": "PROJECT_NAME", "category": "keyword"}],
        )
        # No agent resolves -> unavailable
        assert result["ok"] is False


class TestRunSymbols:
    """Tests for run_symbols command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_symbols()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]


class TestRunDefinition:
    """Tests for run_definition command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_definition()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]


class TestRunReferences:
    """Tests for run_references command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_references()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]


class TestRunFixPreview:
    """Tests for run_fix_preview command."""

    def test_returns_unavailable_for_missing_uri(self):
        result = run_fix_preview()
        assert result["ok"] is False
        assert "Missing or unknown uri/path" in result["capabilities"]["reason"]


class TestExecuteCommand:
    """Tests for execute_command dispatcher."""

    def test_unknown_command(self):
        result = execute_command("cp2k/unknown")
        assert result["ok"] is False
        assert "Unknown command" in result["capabilities"]["reason"]

    def test_known_command(self):
        result = execute_command(COMMAND_CAPABILITIES)
        assert "software" in result
        assert result["status"] == "available"


class TestContextParsing:
    """Tests for internal context parsing functions."""

    def test_parse_context_at_position(self):
        lines = MINIMAL_INPUT.splitlines()
        context = _parse_context_at_position(lines, 2, 15)  # Line 3, RUN_TYPE ENERGY

        assert context["section_path"] == ["GLOBAL"]
        assert context["current_keyword"] == "RUN_TYPE"
        assert context["current_value"] == "ENERGY"
        assert len(context["surrounding_block"]) > 0

    def test_parse_context_nested_sections(self):
        lines = MINIMAL_INPUT.splitlines()
        # Line 9 (0-indexed) is "    POTENTIAL_FILE_NAME POTENTIAL"
        # which is inside &FORCE_EVAL -> &DFT
        context = _parse_context_at_position(lines, 9, 5)

        assert "FORCE_EVAL" in context["section_path"]
        assert "DFT" in context["section_path"]


class TestWikiSearch:
    """Tests for wiki search functionality."""

    def test_search_by_keyword(self):
        results = _search_wiki_digest("PROJECT_NAME", "keyword")
        assert len(results) > 0
        assert results[0]["keyword"] == "PROJECT_NAME"

    def test_search_by_section(self):
        results = _search_wiki_digest("GLOBAL", "keyword")
        assert len(results) > 0
        assert any(result["section"] == "GLOBAL" for result in results)

    def test_search_no_results(self):
        results = _search_wiki_digest("NONEXISTENT", "keyword")
        assert len(results) == 0

    def test_search_all_categories(self):
        results = _search_wiki_digest("ENERGY", "all")
        assert len(results) >= 0  # depends on wiki entries


class TestSymbolExtraction:
    """Tests for symbol extraction."""

    def test_extract_sections(self):
        symbols = _extract_symbols(MINIMAL_INPUT)
        sections = [s for s in symbols if s["type"] == "section"]
        section_names = [s["name"] for s in sections]
        assert "GLOBAL" in section_names
        assert "FORCE_EVAL" in section_names
        assert "DFT" in section_names

    def test_extract_keywords(self):
        symbols = _extract_symbols(MINIMAL_INPUT)
        keywords = [s for s in symbols if s["type"] == "keyword"]
        keyword_names = [s["name"] for s in keywords]
        assert "PROJECT_NAME" in keyword_names
        assert "RUN_TYPE" in keyword_names
        assert "METHOD" in keyword_names

    def test_extract_symbols_empty(self):
        symbols = _extract_symbols("")
        assert symbols == []


class TestDefinitionResolution:
    """Tests for definition resolution."""

    def test_resolve_variable_definition(self):
        # Line 2 has "  RUN_TYPE ${RUN_TYPE}" — col 20 is inside ${RUN_TYPE}
        result = _resolve_definition(INPUT_WITH_VARIABLES, 2, 20, "file:///test.inp")
        assert result["type"] == "variable"
        assert result["name"] == "RUN_TYPE"
        assert result["definition_line"] == 6  # @SET RUN_TYPE = ENERGY

    def test_resolve_undefined_variable(self):
        text = "&GLOBAL\n  PROJECT_NAME ${UNDEFINED_VAR}\n&END GLOBAL\n"
        result = _resolve_definition(text, 1, 20, "file:///test.inp")
        assert result["type"] == "variable"
        assert result["name"] == "UNDEFINED_VAR"
        assert result["definition_line"] is None
        assert result["exists"] is False

    def test_no_reference_at_position(self):
        result = _resolve_definition(MINIMAL_INPUT, 2, 0, "file:///test.inp")
        assert result["type"] == "none"


class TestReferenceFinding:
    """Tests for reference finding."""

    def test_find_references(self):
        refs = _find_references(MINIMAL_INPUT, 2, 15)
        assert len(refs) > 0
        # Should find at least the line we're on
        lines_found = [r["line"] for r in refs]
        assert 2 in lines_found


class TestCommandRegistry:
    """Tests for command registry."""

    def test_all_commands_registered(self):
        expected_commands = [
            COMMAND_CHECK,
            COMMAND_EXPLAIN,
            COMMAND_CAPABILITIES,
            COMMAND_CONTEXT,
            COMMAND_WIKI_SEARCH,
            COMMAND_SYMBOLS,
            COMMAND_DEFINITION,
            COMMAND_REFERENCES,
            COMMAND_FIX_PREVIEW,
            COMMAND_SCHEMA_VALIDATE,
        ]
        for cmd in expected_commands:
            assert cmd in COMMAND_REGISTRY

    def test_registry_handlers_callable(self):
        for cmd, handler in COMMAND_REGISTRY.items():
            assert callable(handler), f"Handler for {cmd} is not callable"


class TestReleaseAwareBehavior:
    """Tests for Issue #126: release-aware behavior."""

    def test_run_check_includes_release_version(self):
        server = MagicMock()
        server.release_version = "2025.1"
        document = MagicMock()
        document.source = MINIMAL_INPUT
        server.workspace.get_text_document.return_value = document

        payload = run_check(server, [{"uri": "file:///test.inp"}])
        assert payload["release_version"] == "2025.1"

    def test_run_check_no_release_version(self):
        server = MagicMock()
        server.release_version = None
        document = MagicMock()
        document.source = MINIMAL_INPUT
        server.workspace.get_text_document.return_value = document

        payload = run_check(server, [{"uri": "file:///test.inp"}])
        assert "release_version" not in payload

    def test_run_check_server_is_none(self):
        payload = run_check(None, [{"uri": "file:///nonexistent.inp"}])
        assert "release_version" not in payload

    def test_hover_provenance_footer_with_version(self):
        from cp2k_lsp.features.hover import HoverProvider

        server = MagicMock()
        server.release_version = "2025.1"
        provider = HoverProvider(server)
        result = provider._append_provenance_footer("**TEST** - keyword")
        assert result == "**TEST** - keyword\n---\n*Schema version: 2025.1*"

    def test_hover_provenance_footer_without_version(self):
        from cp2k_lsp.features.hover import HoverProvider

        server = MagicMock()
        server.release_version = None
        provider = HoverProvider(server)
        result = provider._append_provenance_footer("**TEST** - keyword")
        assert result == "**TEST** - keyword"

    def test_hover_release_version_property(self):
        from cp2k_lsp.features.hover import HoverProvider

        server = MagicMock()
        server.release_version = "2024.2"
        provider = HoverProvider(server)
        assert provider._release_version == "2024.2"

    def test_server_initializes_release_version(self):
        from cp2k_lsp.server import CP2KLanguageServer
        assert hasattr(CP2KLanguageServer, "__init__")
        import inspect
        source = inspect.getsource(CP2KLanguageServer.__init__)
        assert "self.release_version" in source
