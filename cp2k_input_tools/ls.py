"""
CP2K Language Server implementation.

Provides LSP features: diagnostics, hover, definition, references,
code actions, document symbols, formatting, and rename for CP2K input files.
"""

import re
from typing import List, Optional, Union

from lsprotocol.types import (
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_RENAME,
    TEXT_DOCUMENT_PREPARE_RENAME,
    CodeAction,
    CodeActionKind,
    CodeActionParams,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    DefinitionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentSymbol,
    DocumentSymbolParams,
    Hover,
    HoverParams,
    MarkedString,
    MarkupContent,
    MarkupKind,
    Position,
    PrepareRenameParams,
    PrepareRenameResult,
    Range,
    ReferenceParams,
    RenameParams,
    TextDocumentEdit,
    TextEdit,
    WorkspaceEdit,
)
from pygls.server import LanguageServer
from pygls.workspace import TextDocument

from .parser import CP2KInputParserSimplified
from .parser_errors import ParserError
from .preprocessor import CP2KPreprocessor
from .tokenizer import TokenizerError
from .validator import validate_semantics

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


# Diagnostic source labels
SOURCE_PARSER = "cp2k-parser"
SOURCE_SCHEMA = "cp2k-schema"
SOURCE_LINT = "cp2k-lint"
SOURCE_SEMANTICS = "cp2k-semantics"


def _severity_to_lsp(severity: str) -> DiagnosticSeverity:
    if severity == "error":
        return DiagnosticSeverity.Error
    elif severity == "warning":
        return DiagnosticSeverity.Warning
    return DiagnosticSeverity.Information


def _validate(ls, params: Union[DidChangeTextDocumentParams, DidCloseTextDocumentParams, DidOpenTextDocumentParams]):
    """Validate a CP2K input document and publish diagnostics."""
    ls.show_message_log("Validating CP2K input...")
    diagnostics = []

    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    parser = CP2KInputParserSimplified()

    with open(text_doc.path, "r") as fhandle:
        try:
            tree = parser.parse(fhandle)

            # Syntax validation passed, now do semantic validation
            semantic_diagnostics = validate_semantics(tree)
            for diag in semantic_diagnostics:
                severity = DiagnosticSeverity.Warning
                if diag.severity == "error":
                    severity = DiagnosticSeverity.Error

                line = diag.line - 1 if diag.line > 0 else 0
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=line, character=0), end=Position(line=line, character=100)
                        ),
                        message=diag.message,
                        severity=severity,
                        source="cp2k-lsp",
                        code=diag.code,
                    )
                )

        except (TokenizerError, ParserError) as exc:
            ctx = exc.args[1]
            line = ctx.line.rstrip()

        msg = f"Syntax error: {exc.args[0]}"
        if exc.__cause__:
            msg = f"Syntax error: {exc.args[0]} ({exc.__cause__})"

        linenr = (ctx.linenr or 1) - 1
        colnr = ctx.colnr or 0

        if colnr is not None and colnr > 0:
            count = 0
            nchars = colnr

            if ctx.ref_colnr is not None:
                count = ctx.ref_colnr - ctx.colnr
                nchars = min(ctx.ref_colnr, ctx.colnr)

            if ctx.colnrs:
                nchars += ctx.colnrs[0]

            count = max(1, count)
            erange = Range(
                start=Position(line=linenr, character=max(0, colnr - count)),
                end=Position(line=linenr, character=min(len(line_text), colnr + 1)),
            )
        else:
            erange = Range(
                start=Position(line=linenr, character=0),
                end=Position(line=linenr, character=len(line_text)),
            )

        diagnostics.append(Diagnostic(
            range=erange,
            message=msg,
            severity=DiagnosticSeverity.Error,
            source=SOURCE_PARSER,
            code="syntax-error",
        ))
    except Exception as exc:
        diagnostics.append(Diagnostic(
            range=Range(start=Position(0, 0), end=Position(0, 1)),
            message=f"Unexpected error during parsing: {exc}",
            severity=DiagnosticSeverity.Error,
            source=SOURCE_PARSER,
            code="parse-error",
        ))

    # Run semantic validation if parsing succeeded
    if tree is not None:
        try:
            from .validator import validate as semantic_validate
            validation_result = semantic_validate(tree)

            # For semantic diagnostics we don't have precise line info,
            # so attach them to the top of the file
            for diag in validation_result.diagnostics:
                diagnostics.append(Diagnostic(
                    range=Range(start=Position(0, 0), end=Position(0, 1)),
                    message=diag.message,
                    severity=_severity_to_lsp(diag.severity),
                    source=diag.source,
                    code=diag.code,
                ))
        except ImportError:
            ls.show_message_log("Semantic validation module not available")
        except Exception as exc:
            ls.show_message_log(f"Semantic validation error: {exc}")

    # Run type-checking validation (keyword types, enums, units)
    try:
        from .typecheck import validate_text as tc_validate
        type_diags = tc_validate(text_doc.source)
        for td in type_diags:
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=td.line - 1, character=td.col),
                    end=Position(line=td.line - 1, character=td.col + 1),
                ),
                message=td.message,
                severity=DiagnosticSeverity.Error if td.severity == "error" else DiagnosticSeverity.Warning,
                source=td.source,
                code=td.code,
            ))
    except ImportError:
        ls.show_message_log("Typecheck module not available")
    except Exception as exc:
        ls.show_message_log(f"Typecheck error: {exc}")

    # Run static lint checks (always run, even if parsing failed partially)
    try:
        from .linter import lint as static_lint
        lint_diagnostics = static_lint(text_doc.source)

        for diag in lint_diagnostics:
            line_nr = diag.line if diag.line is not None else 0
            col_nr = diag.column if diag.column is not None else 0
            line_text = text_doc.source.split('\n')[line_nr] if line_nr < len(text_doc.source.split('\n')) else ""

            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=line_nr, character=col_nr),
                    end=Position(line=line_nr, character=len(line_text)),
                ),
                message=diag.message,
                severity=_severity_to_lsp(diag.severity),
                source=diag.source,
                code=diag.code,
            ))
    except ImportError:
        ls.show_message_log("Static lint module not available")
    except Exception as exc:
        ls.show_message_log(f"Static lint error: {exc}")

    ls.publish_diagnostics(text_doc.uri, diagnostics)
    return tree


def _get_section_path_at_position(text_doc: TextDocument, tree: dict, position: Position) -> List[str]:
    """Get the section path at a given cursor position by analyzing indentation."""
    lines = text_doc.source.split("\n")
    if position.line >= len(lines):
        return []

    line = lines[position.line]
    target_indent = len(line) - len(line.lstrip())

    section_stack = []
    current_indent = -2  # root is at -2

    for i, doc_line in enumerate(lines):
        if i > position.line:
            break
        stripped = doc_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(doc_line) - len(doc_line.lstrip())

        if stripped.startswith("&") and not stripped.startswith("&END"):
            section_name = stripped[1:].split()[0].upper()
            # Pop sections that are at same or deeper indent
            while section_stack and indent <= section_stack[-1][1]:
                section_stack.pop()
            section_stack.append((section_name, indent))
            current_indent = indent
        elif stripped.upper().startswith("&END"):
            while section_stack:
                section_stack.pop()
                break

    return [s[0] for s in section_stack]


def _build_code_actions(tree: dict, diagnostics: List[Diagnostic]) -> List[CodeAction]:
    """Generate code actions from diagnostics."""
    actions = []

    for diag in diagnostics:
        if not diag.code:
            continue

        if diag.code == "REMOVED_KEYWORD":
            actions.append(CodeAction(
                title=f"Remove deprecated keyword",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
                is_preferred=True,
            ))
        elif diag.code == "RUN_TYPE_MOTION_MISMATCH":
            if "Remove" in (diag.message or ""):
                actions.append(CodeAction(
                    title="Remove conflicting section",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))
            if "change RUN_TYPE" in (diag.message or ""):
                actions.append(CodeAction(
                    title="Change RUN_TYPE to match section",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))
        elif diag.code == "MULTIPLE_XC_FUNCTIONALS":
            actions.append(CodeAction(
                title="Keep only one XC functional",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
            ))
        elif diag.code == "SCF_SOLVER_CONFLICT":
            actions.append(CodeAction(
                title="Remove conflicting SCF solver",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
            ))
        elif diag.code == "METHOD_SECTION_CONFLICT":
            actions.append(CodeAction(
                title="Fix METHOD/section conflict",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
            ))
        elif diag.code == "CUTOFF_TOO_LOW":
            actions.append(CodeAction(
                title="Increase CUTOFF to 200 Ry",
                kind=CodeActionKind.QuickFix,
                diagnostics=[diag],
            ))

    return actions


def _get_keyword_docs(kw_name: str) -> Optional[str]:
    """Get documentation for a keyword from the XML schema."""
    try:
        from . import DEFAULT_CP2K_INPUT_XML
        import xml.etree.ElementTree as ET

        spec = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = spec.getroot()

        for kw in root.iter("KEYWORD"):
            name_node = kw.find("NAME")
            if name_node is not None and name_node.text and name_node.text.upper() == kw_name.upper():
                desc = kw.find("DESCRIPTION")
                dtype = kw.find("DATA_TYPE")
                default = kw.find("DEFAULT_VALUE")
                default_unit = kw.find("DEFAULT_UNIT")

                parts = []
                if desc is not None and desc.text:
                    # Truncate long descriptions
                    text = desc.text.strip()
                    if len(text) > 300:
                        text = text[:297] + "..."
                    parts.append(text)
                if dtype is not None:
                    parts.append(f"**Type:** {dtype.get('kind', 'unknown')}")
                if default is not None and default.text:
                    parts.append(f"**Default:** {default.text}")
                if default_unit is not None and default_unit.text:
                    parts.append(f"**Unit:** {default_unit.text}")

                return "\n\n".join(parts) if parts else None
    except Exception:
        pass
    return None


def _find_variable_definitions(text_doc: TextDocument, var_name: str) -> List[Position]:
    """Find all @SET variable definitions with a given name."""
    positions = []
    pattern = re.compile(rf"^@SET\s+{re.escape(var_name)}\b", re.IGNORECASE | re.MULTILINE)
    for match in pattern.finditer(text_doc.source):
        line_num = text_doc.source[:match.start()].count("\n")
        positions.append(Position(line=line_num, character=0))
    return positions


def _find_variable_usages(text_doc: TextDocument, var_name: str) -> List[Position]:
    """Find all $VAR usages of a variable."""
    positions = []
    pattern = re.compile(rf"\${re.escape(var_name)}\b")
    for match in pattern.finditer(text_doc.source):
        line_num = text_doc.source[:match.start()].count("\n")
        col = match.start() - text_doc.source.rfind("\n", 0, match.start()) - 1
        positions.append(Position(line=line_num, character=col))
    return positions


def _parse_set_vars(text_doc: TextDocument) -> dict:
    """Parse all @SET variable definitions from a document."""
    variables = {}
    pattern = re.compile(r"^@SET\s+(\w+)\s+(.*)$", re.MULTILINE)
    for match in pattern.finditer(text_doc.source):
        var_name = match.group(1)
        var_value = match.group(2).strip()
        line_num = text_doc.source[:match.start()].count("\n")
        variables[var_name] = {"value": var_value, "line": line_num}
    return variables


def setup_cp2k_ls_server(server):
    """Register all LSP features on the server."""

    @server.feature(TEXT_DOCUMENT_COMPLETION)
    def completions(ls: LanguageServer, params: CompletionParams) -> CompletionList:
        """Provide completion suggestions for CP2K keywords and sections."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        lines = text_doc.source.split("\n")
        line_idx = params.position.line
        col_idx = params.position.character

        if line_idx >= len(lines):
            return CompletionList(is_incomplete=False, items=[])

        line = lines[line_idx]
        stripped = line.strip()

        items = []

        # Determine if we're in a section context by parsing up to this line
        try:
            parser = CP2KInputParser()
            section = _get_section_context(lines, line_idx + 1, parser)
        except Exception:
            section = None

        if section is not None:
            items = _get_completions_for_section(section)

        # If typing a keyword name (no & prefix), also add keywords
        if not stripped.startswith("&") and not stripped.startswith("@"):
            kw_prefix = stripped.split()[0].upper() if stripped else ""
            if kw_prefix and section:
                # Filter completions to match prefix
                filtered = [
                    item for item in items
                    if item.label.upper().startswith(kw_prefix)
                ]
                if filtered:
                    items = filtered

        # If typing a section name (starts with &), add section completions
        if stripped.startswith("&") and not stripped.upper().startswith("&END"):
            sec_prefix = stripped[1:].split()[0].upper() if len(stripped) > 1 else ""
            if section:
                for name_node in section.node.iterfind("./SECTION/NAME"):
                    if name_node.text:
                        if not sec_prefix or name_node.text.upper().startswith(sec_prefix):
                            items.append(
                                CompletionItem(
                                    label=f"&{name_node.text}",
                                    kind=CompletionItemKind.Class,
                                    detail="Section",
                                )
                            )

        return CompletionList(is_incomplete=False, items=items)

    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls, params: DidChangeTextDocumentParams):
        _validate(ls, params)

    @server.feature(TEXT_DOCUMENT_DID_CLOSE)
    def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
        """Text document did close notification."""
        # Clear diagnostics for closed document
        ls.publish_diagnostics(params.text_document.uri, [])

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    async def did_open(ls, params: DidOpenTextDocumentParams):
        _validate(ls, params)

    # --- Hover ---
    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(ls: LanguageServer, params: HoverParams) -> Optional[Hover]:
        """Provide hover information for sections and keywords."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        line = text_doc.source.split("\n")[params.position.line] if params.position.line < len(text_doc.source.split("\n")) else ""
        stripped = line.strip()

        # Check if hovering over a keyword
        kw_match = re.match(r"^(\w+)\s", stripped)
        if kw_match and not stripped.startswith("&"):
            kw_name = kw_match.group(1).upper()
            docs = _get_keyword_docs(kw_name)
            if docs:
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.Markdown, value=docs),
                )

        # Check if hovering over a section
        sec_match = re.match(r"^&(\w+)", stripped)
        if sec_match:
            sec_name = sec_match.group(1).upper()
            return Hover(
                contents=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=f"**Section:** `&{sec_name}`\n\nA CP2K input section. See CP2K manual for details.",
                ),
            )

        return None

    # --- Definition ---
    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def definition(ls: LanguageServer, params: DefinitionParams):
        """Go to definition for variables and includes."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        line = text_doc.source.split("\n")[params.position.line] if params.position.line < len(text_doc.source.split("\n")) else ""

        # Check for @INCLUDE
        inc_match = re.search(r"@INCLUDE\s+(.+)", line, re.IGNORECASE)
        if inc_match:
            inc_path = inc_match.group(1).strip().strip("'\"")
            # Try to resolve relative to document
            import pathlib
            doc_path = pathlib.Path(text_doc.path)
            resolved = (doc_path.parent / inc_path).resolve()
            if resolved.exists():
                return {
                    "uri": resolved.as_uri(),
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 0},
                    },
                }

        # Check for $VARIABLE usage
        var_match = re.search(r"\$(\w+)", line)
        if var_match:
            var_name = var_match.group(1)
            defs = _find_variable_definitions(text_doc, var_name)
            if defs:
                return [{
                    "uri": text_doc.uri,
                    "range": {
                        "start": {"line": d.line, "character": 0},
                        "end": {"line": d.line, "character": len(f"@SET {var_name}")},
                    },
                } for d in defs]

        return None

    # --- References ---
    @server.feature(TEXT_DOCUMENT_REFERENCES)
    def references(ls: LanguageServer, params: ReferenceParams):
        """Find all references to a variable."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        line = text_doc.source.split("\n")[params.position.line] if params.position.line < len(text_doc.source.split("\n")) else ""

        # Check if cursor is on a @SET definition
        set_match = re.match(r"^@SET\s+(\w+)", line.strip())
        if set_match:
            var_name = set_match.group(1)
            usages = _find_variable_usages(text_doc, var_name)
            defs = _find_variable_definitions(text_doc, var_name)
            locations = []
            for d in defs:
                locations.append({
                    "uri": text_doc.uri,
                    "range": {
                        "start": {"line": d.line, "character": 0},
                        "end": {"line": d.line, "character": len(f"@SET {var_name}")},
                    },
                })
            for u in usages:
                locations.append({
                    "uri": text_doc.uri,
                    "range": {
                        "start": {"line": u.line, "character": u.character},
                        "end": {"line": u.line, "character": u.character + len(var_name) + 1},
                    },
                })
            return locations

        # Check if cursor is on a $VARIABLE usage
        var_match = re.search(r"\$(\w+)", line)
        if var_match:
            var_name = var_match.group(1)
            usages = _find_variable_usages(text_doc, var_name)
            defs = _find_variable_definitions(text_doc, var_name)
            locations = []
            for d in defs:
                locations.append({
                    "uri": text_doc.uri,
                    "range": {
                        "start": {"line": d.line, "character": 0},
                        "end": {"line": d.line, "character": len(f"@SET {var_name}")},
                    },
                })
            for u in usages:
                locations.append({
                    "uri": text_doc.uri,
                    "range": {
                        "start": {"line": u.line, "character": u.character},
                        "end": {"line": u.line, "character": u.character + len(var_name) + 1},
                    },
                })
            return locations

        return []

    # --- Document Symbols ---
    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(ls: LanguageServer, params: DocumentSymbolParams):
        """Return document symbol tree for nested sections."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        symbols = []
        stack = []  # (indent, symbol)

        for i, line in enumerate(text_doc.source.split("\n")):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())

            if stripped.startswith("&") and not stripped.upper().startswith("&END"):
                sec_name = stripped[1:].split()[0]
                # Pop stack items with same or greater indent
                while stack and indent <= stack[-1][0]:
                    stack.pop()

                sym = DocumentSymbol(
                    name=sec_name,
                    kind=21,  # SymbolKind.Struct
                    range=Range(
                        start=Position(line=i, character=0),
                        end=Position(line=i, character=len(line)),
                    ),
                    selection_range=Range(
                        start=Position(line=i, character=indent),
                        end=Position(line=i, character=indent + len(sec_name) + 1),
                    ),
                    children=[],
                )

                if stack:
                    stack[-1][1].children.append(sym)
                else:
                    symbols.append(sym)

                stack.append((indent, sym))

            elif stripped.upper().startswith("&END"):
                while stack:
                    stack.pop()
                    break

        return symbols

    # --- Code Actions ---
    @server.feature(TEXT_DOCUMENT_CODE_ACTION)
    def code_action(ls: LanguageServer, params: CodeActionParams):
        """Provide quick fixes for common errors."""
        actions = []

        # Generate actions from current diagnostics
        diagnostics = params.context.diagnostics
        for diag in diagnostics:
            if not diag.code:
                continue

            if diag.code == "REMOVED_KEYWORD":
                actions.append(CodeAction(
                    title="Remove this keyword",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                    is_preferred=True,
                ))
            elif "CONFLICT" in (diag.code or ""):
                actions.append(CodeAction(
                    title=f"Fix: {diag.message[:60]}",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))
            elif "CUTOFF" in (diag.code or ""):
                actions.append(CodeAction(
                    title="Set CUTOFF to 300 Ry",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))
            elif "RUN_TYPE" in (diag.code or ""):
                actions.append(CodeAction(
                    title="Fix RUN_TYPE/MOTION mismatch",
                    kind=CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))

        return actions if actions else None

    # --- Prepare Rename ---
    @server.feature(TEXT_DOCUMENT_PREPARE_RENAME)
    def prepare_rename(ls: LanguageServer, params):
        """Check if rename is supported at position."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        line = text_doc.source.split("\n")[params.position.line] if params.position.line < len(text_doc.source.split("\n")) else ""
        stripped = line.strip()

        # Support @SET variable rename
        set_match = re.match(r"^@SET\s+(\w+)", stripped)
        if set_match:
            var_name = set_match.group(1)
            col = len(line) - len(line.lstrip()) + len("@SET ")
            return {
                "range": {
                    "start": {"line": params.position.line, "character": col},
                    "end": {"line": params.position.line, "character": col + len(var_name)},
                },
                "placeholder": var_name,
            }

        # Support $VARIABLE rename
        var_match = re.search(r"\$(\w+)", line)
        if var_match:
            var_name = var_match.group(1)
            col = line.index("$" + var_name)
            return {
                "range": {
                    "start": {"line": params.position.line, "character": col + 1},
                    "end": {"line": params.position.line, "character": col + 1 + len(var_name)},
                },
                "placeholder": var_name,
            }

        return None

    # --- Rename ---
    @server.feature(TEXT_DOCUMENT_RENAME)
    def rename(ls: LanguageServer, params: RenameParams):
        """Rename a variable across all its definitions and usages."""
        text_doc = ls.workspace.get_document(params.text_document.uri)
        line = text_doc.source.split("\n")[params.position.line] if params.position.line < len(text_doc.source.split("\n")) else ""
        stripped = line.strip()

        # Find variable name at position
        var_name = None
        set_match = re.match(r"^@SET\s+(\w+)", stripped)
        if set_match:
            var_name = set_match.group(1)
        else:
            var_match = re.search(r"\$(\w+)", line)
            if var_match:
                var_name = var_match.group(1)

        if not var_name:
            return None

        new_name = params.new_name
        edits = []

        # Edit all @SET definitions
        for defn in _find_variable_definitions(text_doc, var_name):
            edits.append(TextEdit(
                range=Range(
                    start=Position(line=defn.line, character=len("@SET ")),
                    end=Position(line=defn.line, character=len("@SET ") + len(var_name)),
                ),
                new_text=new_name,
            ))

        # Edit all $VAR usages
        for usage in _find_variable_usages(text_doc, var_name):
            edits.append(TextEdit(
                range=Range(
                    start=Position(line=usage.line, character=usage.character + 1),
                    end=Position(line=usage.line, character=usage.character + 1 + len(var_name)),
                ),
                new_text=new_name,
            ))

        if not edits:
            return None

        return WorkspaceEdit(
            document_changes=[TextDocumentEdit(
                text_document={"uri": text_doc.uri, "version": text_doc.version},
                edits=edits,
            )]
        )


cp2k_server = LanguageServer("cp2k-lsp", "v0.2")
setup_cp2k_ls_server(cp2k_server)
