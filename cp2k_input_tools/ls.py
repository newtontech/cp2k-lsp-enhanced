"""Enhanced LSP server with formatting, navigation, rename, and rich diagnostics."""

import pathlib
from typing import Dict, List, Optional, Union

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_RANGE_FORMATTING,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_PREPARE_RENAME,
    TEXT_DOCUMENT_RENAME,
    TEXT_DOCUMENT_CODE_ACTION,
    CodeAction,
    CodeActionKind,
    CodeActionParams,
    DefinitionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentFormattingParams,
    DocumentHighlight,
    DocumentHighlightKind,
    DocumentRangeFormattingParams,
    DocumentSymbol,
    DocumentSymbolParams,
    Hover,
    HoverParams,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    PrepareRenameParams,
    PrepareRenameResult,
    Range,
    ReferenceParams,
    RenameParams,
    SymbolKind,
    TextDocumentSyncKind,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer

from .formatter import format_document as _format_doc, format_range as _format_range
from .parser import CP2KInputParser
from .parser_errors import ParserError
from .preprocessor import CP2KPreprocessor
from .tokenizer import TokenizerError

import re
import xml.etree.ElementTree as ET

from . import DEFAULT_CP2K_INPUT_XML

# Regex patterns for variable detection
_VAR_SET_RE = re.compile(r"^\s*@SET\s+(\w+)\s+(.+)", re.IGNORECASE)
_VAR_REF_RE = re.compile(r"\$\{?(\w+)\}?")
_INCLUDE_RE = re.compile(r"^\s*@INCLUDE\s+(.+)", re.IGNORECASE)
_SECTION_RE = re.compile(r"^(\s*)&([\w\-_]+)\s*(.*)", re.IGNORECASE)
_END_RE = re.compile(r"^\s*&END\s+([\w\-_]+)", re.IGNORECASE)
_KEYWORD_RE = re.compile(r"^(\s*)([\w\-_]+)\s+(.*)")


def _find_variables(text: str) -> Dict[str, List[int]]:
    """Find all @SET variable definitions and return {var_name: [line_numbers]}."""
    defs: Dict[str, List[int]] = {}
    for i, line in enumerate(text.split('\n')):
        m = _VAR_SET_RE.match(line)
        if m:
            var_name = m.group(1).upper()
            defs.setdefault(var_name, []).append(i)
    return defs


def _find_variable_refs(text: str, var_name: str) -> List[int]:
    """Find all lines referencing $VAR or ${VAR}."""
    refs = []
    pattern = re.compile(rf"\$\{{?{re.escape(var_name)}\}}?", re.IGNORECASE)
    for i, line in enumerate(text.split('\n')):
        if pattern.search(line):
            refs.append(i)
    return refs


def _find_section_range(text: str, line_idx: int) -> Optional[tuple]:
    """Find the section containing the given line. Returns (start_line, end_line, name)."""
    lines = text.split('\n')
    current_section = None
    current_start = 0
    stack = []  # (name, start_line)

    for i, line in enumerate(lines):
        sec_match = _SECTION_RE.match(line)
        if sec_match and not _END_RE.match(line):
            name = sec_match.group(2).upper()
            if name == 'END':
                continue
            stack.append((name, i))
            if i <= line_idx:
                current_section = name
                current_start = i
        end_match = _END_RE.match(line)
        if end_match:
            end_name = end_match.group(1).upper()
            if stack and stack[-1][0] == end_name:
                stack.pop()

    if current_section:
        return (current_start, line_idx, current_section)
    return None


def _get_keyword_info(keyword_name: str, section_name: str = None) -> Optional[dict]:
    """Look up keyword info from the XML schema."""
    try:
        tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = tree.getroot()
    except Exception:
        return None

    kw_upper = keyword_name.upper()

    # Search for the keyword in the schema
    for kw_node in root.iter("KEYWORD"):
        name_node = kw_node.find("./NAME")
        if name_node is not None and name_node.text and name_node.text.upper() == kw_upper:
            info = {}
            info["name"] = kw_upper

            # Get data type
            data_type = kw_node.find("./DATA_TYPE")
            if data_type is not None:
                kind = data_type.get("kind", "")
                info["type"] = kind

            # Get default value
            default = kw_node.find("./DEFAULT_VALUE")
            if default is not None and default.text:
                info["default"] = default.text

            # Get default unit
            default_unit = kw_node.find("./DEFAULT_UNIT")
            if default_unit is not None and default_unit.text:
                info["unit"] = default_unit.text

            # Get description
            desc = kw_node.find("./DESCRIPTION")
            if desc is not None and desc.text:
                info["description"] = desc.text

            # Get usage
            usage = kw_node.find("./USAGE")
            if usage is not None and usage.text:
                info["usage"] = usage.text

            return info
    return None


def _get_section_info(section_name: str) -> Optional[dict]:
    """Look up section info from the XML schema."""
    try:
        tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = tree.getroot()
    except Exception:
        return None

    sec_upper = section_name.upper()

    for sec_node in root.iter("SECTION"):
        name_node = sec_node.find("./NAME")
        if name_node is not None and name_node.text and name_node.text.upper() == sec_upper:
            info = {}
            info["name"] = sec_upper

            desc = sec_node.find("./DESCRIPTION")
            if desc is not None and desc.text:
                info["description"] = desc.text

            return info
    return None


def _build_document_symbols(text: str) -> List[DocumentSymbol]:
    """Build a tree of document symbols from sections."""
    lines = text.split('\n')
    root_symbols = []
    stack = []  # (symbol, children_list)

    for i, line in enumerate(lines):
        end_match = _END_RE.match(line)
        if end_match:
            end_name = end_match.group(1).upper()
            if stack and stack[-1][0].name.upper() == end_name:
                stack.pop()
            continue

        sec_match = _SECTION_RE.match(line)
        if sec_match:
            name = sec_match.group(2).upper()
            if name == 'END':
                continue

            symbol = DocumentSymbol(
                name=name,
                kind=SymbolKind.Class,
                range=Range(
                    start=Position(line=i, character=0),
                    end=Position(line=i, character=len(line))
                ),
                selection_range=Range(
                    start=Position(line=i, character=0),
                    end=Position(line=i, character=len(line.strip()))
                )
            )

            if stack:
                stack[-1][1].append(symbol)
            else:
                root_symbols.append(symbol)

            stack.append((symbol, symbol.children if hasattr(symbol, 'children') else []))

    return root_symbols


_SECTION_MATCH = re.compile(r"&(?P<name>[\w\-_]+)\s*(?P<param>.*)")
_KEYWORD_MATCH = re.compile(r"(?P<name>[\w\-_]+)\s*(?P<value>.*)")


def _get_section_context(lines: List[str], up_to_line: int, parser: CP2KInputParser) -> Optional[Section]:
    """Parse lines up to the cursor position and return the current section context."""
    import xml.etree.ElementTree as ET

    spec = ET.parse(DEFAULT_CP2K_INPUT_XML)
    root_section = Section("/", node=spec.getroot())

    # Build a tree reference stack
    treerefs = [root_section]

    for i, line in enumerate(lines[:up_to_line]):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("!") or stripped.startswith("#"):
            continue

        # Handle section
        if stripped.startswith("&"):
            match = _SECTION_MATCH.match(stripped)
            if match:
                section_name = match.group("name").upper()
                if section_name == "END":
                    if len(treerefs) > 1:
                        treerefs.pop()
                    continue

                section_node = treerefs[-1].find_node_by_name("SECTION", section_name)
                if section_node is not None:
                    repeats = section_node.get("repeats") == "yes"
                    treerefs[-1].subsections += [Section(section_name, repeats=repeats, node=section_node)]
                    treerefs += [treerefs[-1].subsections[-1]]
        else:
            # It's a keyword - just consume it, don't validate strictly
            pass

    return treerefs[-1] if treerefs else None


def _get_completions_for_section(section: Section) -> List[CompletionItem]:
    """Get completion items for a given section context."""
    items = []

    # Add available keywords
    for name_node in section.node.iterfind("./KEYWORD/NAME"):
        if name_node.text:
            items.append(
                CompletionItem(
                    label=name_node.text,
                    kind=CompletionItemKind.Field,
                    detail="Keyword",
                )
            )

    # Add default keyword if present
    default_kw = section.node.find("./DEFAULT_KEYWORD/NAME")
    if default_kw is not None and default_kw.text:
        items.append(
            CompletionItem(
                label=default_kw.text,
                kind=CompletionItemKind.Field,
                detail="Default keyword",
            )
        )

    # Add available subsections
    for name_node in section.node.iterfind("./SECTION/NAME"):
        if name_node.text:
            items.append(
                CompletionItem(
                    label=f"&{name_node.text}",
                    kind=CompletionItemKind.Class,
                    detail="Section",
                )
            )

    return items


def _validate(ls, params: Union[DidChangeTextDocumentParams, DidCloseTextDocumentParams, DidOpenTextDocumentParams]):
    """Validate a CP2K input file and publish diagnostics."""
    ls.show_message_log("Validating CP2K input...")
    diagnostics = []

    text_doc = ls.workspace.get_document(params.text_document.uri)
    parser = CP2KInputParser()

    try:
        with open(text_doc.path, "r") as fhandle:
            parser.parse(fhandle)
    except (TokenizerError, ParserError) as exc:
        ctx = exc.args[1]
        line = ctx.line.rstrip()
        msg = f"Syntax error: {exc.args[0]} ({exc.__cause__})"
        linenr = ctx.linenr - 1
        colnr = ctx.colnr

        if colnr is not None:
            count = max(1, ctx.ref_colnr - ctx.colnr if ctx.ref_colnr else 0)
            erange = Range(
                start=Position(line=linenr, character=colnr + 1 - count),
                end=Position(line=linenr, character=colnr + 1)
            )
        else:
            erange = Range(start=Position(line=linenr, character=1), end=Position(line=linenr, character=len(line)))

        diagnostics.append(Diagnostic(range=erange, message=msg, source="cp2k-parser", severity=DiagnosticSeverity.Error))
    except FileNotFoundError:
        pass  # File not on disk yet

    ls.publish_diagnostics(text_doc.uri, diagnostics)


def setup_cp2k_ls_server(server):
    """Set up all LSP features for the CP2K language server."""

    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls, params: DidChangeTextDocumentParams):
        _validate(ls, params)

    @server.feature(TEXT_DOCUMENT_DID_CLOSE)
    def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
        ls.publish_diagnostics(params.text_document.uri, [])

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    async def did_open(ls, params: DidOpenTextDocumentParams):
        _validate(ls, params)

    # === Formatting (#14) ===

    @server.feature(TEXT_DOCUMENT_FORMATTING)
    def formatting(ls, params: DocumentFormattingParams):
        """Format entire document."""
        try:
            text_doc = ls.workspace.get_document(params.text_document.uri)
            return _format_doc(text_doc.source)
        except Exception as e:
            ls.show_message_log(f"Formatting error: {e}")
            return []

    @server.feature(TEXT_DOCUMENT_RANGE_FORMATTING)
    def range_formatting(ls, params: DocumentRangeFormattingParams):
        """Format a range of lines."""
        try:
            text_doc = ls.workspace.get_document(params.text_document.uri)
            start = params.range.start.line
            end = params.range.end.line
            return _format_range(text_doc.source, start, end)
        except Exception as e:
            ls.show_message_log(f"Range formatting error: {e}")
            return []

    # === Hover (#15) ===

    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(ls, params: HoverParams):
        """Provide hover information for keywords and sections."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        pos = params.position
        lines = text_doc.source.split('\n')

        if pos.line >= len(lines):
            return None

        line = lines[pos.line]

        # Check if on a keyword
        kw_match = _KEYWORD_RE.match(line)
        if kw_match:
            kw_name = kw_match.group(2)
            info = _get_keyword_info(kw_name)
            if info:
                parts = []
                if "type" in info:
                    parts.append(f"**Type:** `{info['type']}`")
                if "default" in info:
                    parts.append(f"**Default:** `{info['default']}`")
                if "unit" in info:
                    parts.append(f"**Unit:** `{info['unit']}`")
                if "usage" in info:
                    parts.append(f"**Usage:** `{info['usage']}`")
                if "description" in info:
                    parts.append(f"**Description:** {info['description']}")
                content = "\n\n".join(parts)
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=content)
                )

        # Check if on a section
        sec_match = _SECTION_RE.match(line)
        if sec_match and not _END_RE.match(line):
            sec_name = sec_match.group(2)
            info = _get_section_info(sec_name)
            if info:
                parts = []
                if "description" in info:
                    parts.append(f"**Description:** {info['description']}")
                content = "\n\n".join(parts)
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=content)
                )

        return None

    # === Go to Definition (#15) ===

    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def definition(ls, params: DefinitionParams):
        """Go to definition for @INCLUDE paths and @SET variables."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        pos = params.position
        lines = text_doc.source.split('\n')

        if pos.line >= len(lines):
            return None

        line = lines[pos.line]

        # Check @INCLUDE
        inc_match = _INCLUDE_RE.match(line)
        if inc_match:
            inc_path = inc_match.group(1).strip().strip('"').strip("'")
            file_uri = pathlib.Path(text_doc.path).parent / inc_path
            if file_uri.exists():
                return Location(
                    uri=file_uri.as_uri(),
                    range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0))
                )
            return None

        # Check variable reference $VAR
        var_match = _VAR_REF_RE.search(line)
        if var_match:
            var_name = var_match.group(1).upper()
            # Find the @SET definition
            for i, def_line in enumerate(lines):
                set_match = _VAR_SET_RE.match(def_line)
                if set_match and set_match.group(1).upper() == var_name:
                    return Location(
                        uri=text_doc.uri,
                        range=Range(
                            start=Position(line=i, character=0),
                            end=Position(line=i, character=len(def_line))
                        )
                    )
            return None

        return None

    # === Find References (#15) ===

    @server.feature(TEXT_DOCUMENT_REFERENCES)
    def references(ls, params: ReferenceParams):
        """Find all references to a variable."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        pos = params.position
        lines = text_doc.source.split('\n')

        if pos.line >= len(lines):
            return []

        line = lines[pos.line]

        # Check if cursor is on a variable definition or reference
        set_match = _VAR_SET_RE.match(line)
        if set_match:
            var_name = set_match.group(1).upper()
        else:
            var_match = _VAR_REF_RE.search(line)
            if var_match:
                var_name = var_match.group(1).upper()
            else:
                return []

        locations = []
        # Find all @SET definitions
        for i, def_line in enumerate(lines):
            m = _VAR_SET_RE.match(def_line)
            if m and m.group(1).upper() == var_name:
                locations.append(Location(
                    uri=text_doc.uri,
                    range=Range(
                        start=Position(line=i, character=0),
                        end=Position(line=i, character=len(def_line))
                    )
                ))

        # Find all $VAR references
        pattern = re.compile(rf"\$\{{?{re.escape(var_name)}\}}?", re.IGNORECASE)
        for i, ref_line in enumerate(lines):
            for m in pattern.finditer(ref_line):
                locations.append(Location(
                    uri=text_doc.uri,
                    range=Range(
                        start=Position(line=i, character=m.start()),
                        end=Position(line=i, character=m.end())
                    )
                ))

        return locations

    # === Document Symbols (#15) ===

    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(ls, params: DocumentSymbolParams):
        """Return document symbol tree."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        return _build_document_symbols(text_doc.source)

    # === Prepare Rename (#21) ===

    @server.feature(TEXT_DOCUMENT_PREPARE_RENAME)
    def prepare_rename(ls, params: PrepareRenameParams):
        """Check if position can be renamed."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        pos = params.position
        lines = text_doc.source.split('\n')

        if pos.line >= len(lines):
            return None

        line = lines[pos.line]

        # Check if on a @SET variable definition
        set_match = _VAR_SET_RE.match(line)
        if set_match:
            var_name = set_match.group(1)
            start = line.index(var_name)
            return PrepareRenameResult(
                range=Range(
                    start=Position(line=pos.line, character=start),
                    end=Position(line=pos.line, character=start + len(var_name))
                ),
                placeholder=var_name
            )

        # Check if on a $VAR reference
        for m in _VAR_REF_RE.finditer(line):
            if m.start() <= pos.character <= m.end():
                var_name = m.group(1)
                return PrepareRenameResult(
                    range=Range(
                        start=Position(line=pos.line, character=m.start()),
                        end=Position(line=pos.line, character=m.end())
                    ),
                    placeholder=var_name
                )

        return None

    # === Rename (#21) ===

    @server.feature(TEXT_DOCUMENT_RENAME)
    def rename(ls, params: RenameParams):
        """Rename a variable across all references."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        pos = params.position.position
        new_name = params.new_name
        lines = text_doc.source.split('\n')

        if pos.line >= len(lines):
            return None

        line = lines[pos.line]

        # Determine variable name
        set_match = _VAR_SET_RE.match(line)
        if set_match:
            var_name = set_match.group(1)
        else:
            var_match = _VAR_REF_RE.search(line)
            if var_match:
                var_name = var_match.group(1)
            else:
                return None

        edits = []
        # Replace @SET definitions
        for i, def_line in enumerate(lines):
            m = _VAR_SET_RE.match(def_line)
            if m and m.group(1).upper() == var_name.upper():
                start_col = def_line.index(m.group(1))
                edits.append(TextEdit(
                    range=Range(
                        start=Position(line=i, character=start_col),
                        end=Position(line=i, character=start_col + len(m.group(1)))
                    ),
                    new_text=new_name
                ))

        # Replace $VAR references
        pattern = re.compile(rf"\$\{{?{re.escape(var_name)}\}}?", re.IGNORECASE)
        for i, ref_line in enumerate(lines):
            for m in pattern.finditer(ref_line):
                edits.append(TextEdit(
                    range=Range(
                        start=Position(line=i, character=m.start()),
                        end=Position(line=i, character=m.end())
                    ),
                    new_text=f"${{{new_name}}}" if '{' in m.group() else f"${new_name}"
                ))

        if edits:
            return WorkspaceEdit(changes={text_doc.uri: edits})
        return None

    # === Code Actions (#19 stub for downstream worker) ===

    @server.feature(TEXT_DOCUMENT_CODE_ACTION)
    def code_action(ls, params: CodeActionParams):
        """Provide quick fixes for common errors."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        diagnostics = params.context.diagnostics
        actions = []

        for diag in diagnostics:
            if "invalid section" in diag.message.lower():
                actions.append(CodeAction(
                    title="Remove invalid section",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag]
                ))
            if "invalid keyword" in diag.message.lower():
                actions.append(CodeAction(
                    title="Remove invalid keyword",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag]
                ))

        return actions if actions else None


cp2k_server = LanguageServer("cp2k-lsp", "v0.2")
setup_cp2k_ls_server(cp2k_server)
