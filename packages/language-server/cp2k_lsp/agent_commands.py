"""Agent-facing LSP workspace/executeCommand handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cp2k_input_tools.agent_lsp import AgentLSP
from cp2k_input_tools.agent_operations import OPERATIONS, with_capabilities
from cp2k_input_tools.rich_diagnostics import agent_check_payload
from cp2k_input_tools.tool import SOFTWARE

COMMAND_CHECK = "cp2k/check"
COMMAND_EXPLAIN = "cp2k/explain"
COMMAND_CAPABILITIES = "cp2k/capabilities"
COMMAND_CONTEXT = "cp2k/context"
COMMAND_WIKI_SEARCH = "cp2k/wiki.search"
COMMAND_SYMBOLS = "cp2k/symbols"
COMMAND_DEFINITION = "cp2k/definition"
COMMAND_REFERENCES = "cp2k/references"
COMMAND_FIX_PREVIEW = "cp2k/fix.preview"
COMMAND_SCHEMA_VALIDATE = "cp2k/schema.validate"

AGENT_COMMANDS = (
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
)


def parse_command_args(arguments: list[Any] | None) -> dict[str, Any]:
    """Normalize LSP executeCommand arguments to a single kwargs dict."""
    if not arguments:
        return {}
    first = arguments[0]
    if isinstance(first, dict):
        return dict(first)
    if isinstance(first, str):
        try:
            parsed = json.loads(first)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"uri": first}
    return {}


def _resolve_uri(args: dict[str, Any]) -> str | None:
    uri = args.get("uri")
    if isinstance(uri, str) and uri.strip():
        return uri
    path = args.get("path")
    if isinstance(path, str) and path.strip():
        return Path(path).expanduser().resolve().as_uri()
    return None


def _agent_lsp_from_args(server: Any, args: dict[str, Any]) -> AgentLSP | None:
    uri = _resolve_uri(args)
    if uri is None:
        return None

    if server is not None:
        try:
            document = server.workspace.get_text_document(uri)
            return AgentLSP.from_text(document.source, uri=uri)
        except Exception:
            pass

    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path = Path(parsed.path)
        if path.is_file():
            return AgentLSP.from_path(path)
    return None


def _unavailable_payload(operation: str, reason: str) -> dict[str, Any]:
    payload = agent_check_payload(
        software=SOFTWARE,
        uri="",
        operation=operation,
        diagnostics=[],
    )
    payload["ok"] = False
    return with_capabilities(payload, operation, status="unavailable", reason=reason, source="cp2k-lsp")


def run_capabilities(_server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Return the fleet-standard capabilities contract for agent consumers."""
    del arguments
    return {
        "software": SOFTWARE,
        "status": "available",
        "capabilities": {
            "operations": list(OPERATIONS),
            "operation": "capabilities",
            "status": "available",
            "source": "cp2k-lsp",
            "commands": list(AGENT_COMMANDS),
        },
    }


def run_check(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Run Diagnostic Engine v1 check for a workspace document or file URI."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("check", "Missing or unknown uri/path for cp2k/check.")
    version = getattr(server, "release_version", None) if server is not None else None
    payload = agent.check()
    if version:
        payload["release_version"] = version
    return with_capabilities(payload, "check", source="cp2k-lsp")


def run_explain(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Explain diagnostics or documentation at a cursor position."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("explain", "Missing or unknown uri/path for cp2k/explain.")
    line = int(args.get("line", 0) or 0)
    character = int(args.get("character", 0) or 0)
    payload = agent.explain(line=line, character=character)
    if "capabilities" in payload:
        payload["capabilities"]["source"] = "cp2k-lsp"
        return payload
    return with_capabilities(payload, "explain", source="cp2k-lsp")


def run_context(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Get context information: section path, current keyword, current value, surrounding block."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("context", "Missing or unknown uri/path for cp2k/context.")

    line = int(args.get("line", 0) or 0)
    character = int(args.get("character", 0) or 0)

    # Get the document text
    text = ""
    if server is not None:
        try:
            document = server.workspace.get_text_document(_resolve_uri(args))
            text = document.source
        except Exception:
            pass
    elif agent.text is not None:
        text = agent.text
    else:
        # Try to read from file
        parsed = urlparse(agent.uri)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")

    # Parse the context
    lines = text.splitlines() if text else []
    context = _parse_context_at_position(lines, line, character)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="context")
    payload["context"] = context
    return with_capabilities(payload, "context", source="cp2k-lsp")


def run_wiki_search(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Query docs digest by section, keyword, rule, or log pattern."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("wiki.search", "Missing or unknown uri/path for cp2k/wiki.search.")

    query = args.get("query", "")
    category = args.get("category", "all")  # all, section, keyword, rule, log

    # Search the wiki digest
    results = _search_wiki_digest(query, category)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="wiki.search")
    payload["query"] = query
    payload["category"] = category
    payload["results"] = results
    return with_capabilities(payload, "wiki.search", source="cp2k-lsp")


def run_symbols(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Get AST/tree summary for the file."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("symbols", "Missing or unknown uri/path for cp2k/symbols.")

    # Get the document text
    text = ""
    if server is not None:
        try:
            document = server.workspace.get_text_document(_resolve_uri(args))
            text = document.source
        except Exception:
            pass
    elif agent.text is not None:
        text = agent.text
    else:
        parsed = urlparse(agent.uri)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")

    # Parse and extract symbols
    symbols = _extract_symbols(text)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="symbols")
    payload["symbols"] = symbols
    return with_capabilities(payload, "symbols", source="cp2k-lsp")


def run_definition(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Resolve include/datafile/variable targets."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("definition", "Missing or unknown uri/path for cp2k/definition.")

    line = int(args.get("line", 0) or 0)
    character = int(args.get("character", 0) or 0)

    # Get the document text
    text = ""
    if server is not None:
        try:
            document = server.workspace.get_text_document(_resolve_uri(args))
            text = document.source
        except Exception:
            pass
    elif agent.text is not None:
        text = agent.text
    else:
        parsed = urlparse(agent.uri)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")

    # Resolve definition
    definition = _resolve_definition(text, line, character, agent.uri)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="definition")
    payload["definition"] = definition
    return with_capabilities(payload, "definition", source="cp2k-lsp")


def run_references(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Get variable/include/KIND references."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("references", "Missing or unknown uri/path for cp2k/references.")

    line = int(args.get("line", 0) or 0)
    character = int(args.get("character", 0) or 0)

    # Get the document text
    text = ""
    if server is not None:
        try:
            document = server.workspace.get_text_document(_resolve_uri(args))
            text = document.source
        except Exception:
            pass
    elif agent.text is not None:
        text = agent.text
    else:
        parsed = urlparse(agent.uri)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")

    # Find references
    references = _find_references(text, line, character)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="references")
    payload["references"] = references
    return with_capabilities(payload, "references", source="cp2k-lsp")


def run_fix_preview(server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Show safe quick fixes without applying them."""
    args = parse_command_args(arguments)
    agent = _agent_lsp_from_args(server, args)
    if agent is None:
        return _unavailable_payload("fix.preview", "Missing or unknown uri/path for cp2k/fix.preview.")

    # Get the document text
    text = ""
    if server is not None:
        try:
            document = server.workspace.get_text_document(_resolve_uri(args))
            text = document.source
        except Exception:
            pass
    elif agent.text is not None:
        text = agent.text
    else:
        parsed = urlparse(agent.uri)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")

    # Get diagnostics and suggest fixes
    payload = agent.check()
    diagnostics = payload.get("diagnostics", [])

    fixes = []
    for diag in diagnostics:
        fix = _preview_fix_for_diagnostic(text, diag)
        if fix:
            fixes.append(fix)

    payload = agent_check_payload(software=SOFTWARE, uri=agent.uri, operation="fix.preview")
    payload["fixes"] = fixes
    return with_capabilities(payload, "fix.preview", source="cp2k-lsp")


def _parse_context_at_position(lines: list[str], line: int, character: int) -> dict[str, Any]:
    """Parse context at a specific position in the file."""
    import re

    section_stack: list[str] = []
    current_keyword = None
    current_value = None
    surrounding_block = []
    snapshot_at_line: list[str] = []

    section_start_re = re.compile(r"^\s*&([A-Za-z][A-Za-z0-9_\-]*)(?:\s+.*)?$", re.IGNORECASE)
    section_end_re = re.compile(r"^\s*&END(?:\s+([A-Za-z][A-Za-z0-9_\-]*))?\s*$", re.IGNORECASE)
    keyword_re = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_\-]*)\b(.*)$", re.IGNORECASE)

    for i, line_text in enumerate(lines):
        stripped = line_text.strip()
        if not stripped or stripped.startswith(("!", "#", "@")):
            # Snapshot at target line even for comments/blanks
            if i == line:
                snapshot_at_line = list(section_stack)
            continue

        # Track section stack
        end_match = section_end_re.match(stripped)
        if end_match:
            end_name = (end_match.group(1) or "").upper()
            if end_name:
                while section_stack:
                    name = section_stack.pop()
                    if name == end_name:
                        break
            elif section_stack:
                section_stack.pop()
            # Snapshot at target line after section close
            if i == line:
                snapshot_at_line = list(section_stack)
            continue

        sec_match = section_start_re.match(stripped)
        if sec_match:
            section_stack.append(sec_match.group(1).upper())
            # Snapshot at target line after section open
            if i == line:
                snapshot_at_line = list(section_stack)
            continue

        # At the target line, extract keyword and value
        if i == line:
            snapshot_at_line = list(section_stack)
            kw_match = keyword_re.match(stripped)
            if kw_match:
                current_keyword = kw_match.group(2).upper()
                current_value = kw_match.group(3).strip()

            # Get surrounding block (5 lines before and after)
            start = max(0, i - 5)
            end = min(len(lines), i + 6)
            surrounding_block = lines[start:end]

    return {
        "section_path": snapshot_at_line,
        "current_keyword": current_keyword,
        "current_value": current_value,
        "surrounding_block": surrounding_block,
    }


def _search_wiki_digest(query: str, category: str) -> list[dict[str, Any]]:
    """Search the wiki digest for matching entries."""
    from cp2k_input_tools.precomputed_index import load_docs_digest_entries

    results: list[dict[str, Any]] = []
    wiki_entries = load_docs_digest_entries()

    if not wiki_entries:
        wiki_entries = [
            {
                "section": "GLOBAL",
                "keyword": "PROJECT_NAME",
                "description": "The project name used for all output files.",
                "category": "keyword",
            },
            {
                "section": "GLOBAL",
                "keyword": "RUN_TYPE",
                "description": "The type of run to perform (ENERGY, FORCE_EVAL, etc.).",
                "category": "keyword",
            },
            {
                "section": "FORCE_EVAL",
                "keyword": "METHOD",
                "description": "The method to use for force evaluation.",
                "category": "keyword",
            },
            {
                "section": "DFT",
                "keyword": "BASIS_SET_FILE_NAME",
                "description": "Name of the file containing the basis set definitions.",
                "category": "keyword",
            },
        ]

    query_lower = query.lower()
    for entry in wiki_entries:
        if category != "all" and entry["category"] != category:
            continue
        section = entry.get("section", "").lower()
        keyword = entry.get("keyword", "").lower()
        description = entry.get("description", "").lower()
        if query_lower == section or query_lower == keyword:
            results.append({**entry, "_rank": 0})
        elif query_lower in section or query_lower in keyword or query_lower in description:
            results.append({**entry, "_rank": 1})

    results.sort(key=lambda item: (item.get("_rank", 1), item.get("section", ""), item.get("keyword", "")))
    for item in results:
        item.pop("_rank", None)
    return results


def _extract_symbols(text: str) -> list[dict[str, Any]]:
    """Extract symbols from CP2K input file."""
    import re

    symbols = []
    section_start_re = re.compile(r"^\s*&([A-Za-z][A-Za-z0-9_\-]*)(?:\s+(.*))?$", re.IGNORECASE)
    keyword_re = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_\-]*)\b(.*)$", re.IGNORECASE)

    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith(("!", "#", "@")):
            continue

        sec_match = section_start_re.match(stripped)
        if sec_match:
            symbols.append({
                "name": sec_match.group(1).upper(),
                "type": "section",
                "line": i,
                "parameter": sec_match.group(2).strip() if sec_match.group(2) else None,
            })
            continue

        kw_match = keyword_re.match(stripped)
        if kw_match:
            symbols.append({
                "name": kw_match.group(2).upper(),
                "type": "keyword",
                "line": i,
                "value": kw_match.group(3).strip(),
            })

    return symbols


def _resolve_definition(text: str, line: int, character: int, uri: str) -> dict[str, Any]:
    """Resolve include/datafile/variable targets."""
    import re

    lines = text.splitlines()
    if line >= len(lines):
        return {"type": "none", "reason": "Line out of range"}

    line_text = lines[line]

    # Check for @include directive
    include_match = re.search(r"@INCLUDE\s+['\"](.+?)['\"]", line_text, re.IGNORECASE)
    if include_match:
        filename = include_match.group(1)
        # Resolve relative to the file location
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            base_dir = Path(parsed.path).parent
            target_path = base_dir / filename
            if target_path.is_file():
                return {
                    "type": "include",
                    "target": str(target_path),
                    "exists": True,
                }
            return {
                "type": "include",
                "target": filename,
                "exists": False,
            }

    # Check for variable reference ${VAR}
    var_match = re.search(r"\$\{([A-Za-z][A-Za-z0-9_]*)\}", line_text)
    if var_match:
        var_name = var_match.group(1)
        # Search for @SET VAR = ... definition
        for i, l in enumerate(lines):
            set_match = re.search(rf"@SET\s+{var_name}\s*=\s*(.+)", l, re.IGNORECASE)
            if set_match:
                return {
                    "type": "variable",
                    "name": var_name,
                    "definition_line": i,
                    "value": set_match.group(1).strip(),
                }
        return {
            "type": "variable",
            "name": var_name,
            "definition_line": None,
            "exists": False,
        }

    return {"type": "none", "reason": "No resolvable reference at position"}


def _find_references(text: str, line: int, character: int) -> list[dict[str, Any]]:
    """Find variable/include/KIND references."""
    import re

    lines = text.splitlines()
    if line >= len(lines):
        return []

    line_text = lines[line]

    # Extract the symbol at the position
    # Simple approach: find the word at the character position
    words = re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", line_text)
    if not words:
        return []

    # Find which word contains the character position
    pos = 0
    target_word = None
    for word in words:
        start = line_text.find(word, pos)
        if start <= character < start + len(word):
            target_word = word.upper()
            break
        pos = start + len(word)

    if not target_word:
        return []

    # Find all references to this symbol
    references = []
    for i, l in enumerate(lines):
        if target_word in l.upper():
            references.append({
                "line": i,
                "text": l.strip(),
                "type": "reference",
            })

    return references


def _preview_fix_for_diagnostic(text: str, diagnostic: dict[str, Any]) -> dict[str, Any] | None:
    """Preview a fix for a diagnostic without applying it."""
    from cp2k_input_tools.code_actions import get_code_actions

    message = diagnostic.get("message", "")
    line = diagnostic.get("line", 0)
    column = diagnostic.get("column", 0)

    # Create a range for the diagnostic
    from lsprotocol.types import Position, Range

    range_obj = Range(
        start=Position(line=line, character=column),
        end=Position(line=line, character=column + 10),
    )

    # Get code actions
    actions = get_code_actions(
        text=text,
        diagnostic_range=range_obj,
        diagnostic_message=message,
        uri="file:///preview",
        diagnostic_code=diagnostic.get("code"),
        diagnostic_data=diagnostic.get("data"),
    )

    if not actions:
        return None

    # Return the first (preferred) action as a preview
    action = actions[0]
    edit = action.edit
    if edit and edit.document_changes:
        document_edit = edit.document_changes[0]
        if hasattr(document_edit, "edits") and document_edit.edits:
            text_edit = document_edit.edits[0]
            return {
                "title": action.title,
                "kind": str(action.kind) if action.kind else None,
                "is_preferred": action.is_preferred,
                "replacement": text_edit.new_text,
                "range": {
                    "start_line": text_edit.range.start.line,
                    "start_character": text_edit.range.start.character,
                    "end_line": text_edit.range.end.line,
                    "end_character": text_edit.range.end.character,
                },
            }

    return None


def run_schema_validate(_server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Return schema index health: staleness, section/keyword counts, file path."""
    from cp2k_input_tools.schema_index import get_schema_index

    args = parse_command_args(arguments)
    index = get_schema_index()

    stale = index.is_stale()
    section_count = len(index.get_root_sections()) if not stale else 0
    keyword_count = 0
    if not stale:
        for section_name in index.get_root_sections():
            keywords = index.get_keywords((section_name,))
            keyword_count += len(keywords)

    payload = {
        "ok": True,
        "stale": stale,
        "section_count": section_count,
        "keyword_count": keyword_count,
        "schema_path": str(index._xml_path),
        "release_version": index.release_version,
        "loaded_from_precomputed": index._loaded_from_precomputed,
    }
    return with_capabilities(payload, "schema.validate", source="cp2k-lsp")


# Command registry for dispatch
COMMAND_REGISTRY = {
    COMMAND_CHECK: run_check,
    COMMAND_EXPLAIN: run_explain,
    COMMAND_CAPABILITIES: run_capabilities,
    COMMAND_CONTEXT: run_context,
    COMMAND_WIKI_SEARCH: run_wiki_search,
    COMMAND_SYMBOLS: run_symbols,
    COMMAND_DEFINITION: run_definition,
    COMMAND_REFERENCES: run_references,
    COMMAND_FIX_PREVIEW: run_fix_preview,
    COMMAND_SCHEMA_VALIDATE: run_schema_validate,
}


def execute_command(command: str, server: Any = None, arguments: list[Any] | None = None) -> dict[str, Any]:
    """Execute a registered agent command."""
    handler = COMMAND_REGISTRY.get(command)
    if handler is None:
        return _unavailable_payload(command, f"Unknown command: {command}")
    return handler(server, arguments)
