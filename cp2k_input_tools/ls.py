import re
from typing import List, Optional, Union

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    CompletionOptions,
    Diagnostic,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Position,
    Range,
)
from pygls.server import LanguageServer

from . import DEFAULT_CP2K_INPUT_XML
from .parser import CP2KInputParser, Section
from .parser_errors import ParserError
from .tokenizer import TokenizerError


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
    ls.show_message_log("Validating CP2K input...")

    diagnostics = []

    text_doc = ls.workspace.get_document(params.text_document.uri)
    parser = CP2KInputParser()

    with open(text_doc.path, "r") as fhandle:
        try:
            parser.parse(fhandle)
        except (TokenizerError, ParserError) as exc:
            ctx = exc.args[1]
            line = ctx.line.rstrip()

            msg = f"Syntax error: {exc.args[0]} ({exc.__cause__})"

            linenr = ctx.linenr - 1
            colnr = ctx.colnr

            if colnr is not None:
                count = 0  # number of underline chars after (positiv) or before (negative) the marker if ref_colnr given
                nchars = colnr  # relevant line length

                if ctx.ref_colnr is not None:
                    count = ctx.ref_colnr - ctx.colnr
                    nchars = min(ctx.ref_colnr, ctx.colnr)  # correct if ref comes before

                if ctx.colnrs:
                    # shift by the number of left-stripped ws
                    # ctx.colnrs contains the left shift for each possibly continued line
                    nchars += ctx.colnrs[0]  # assume no line-continuation for now

                # at least do one context
                count = max(1, count)

                erange = Range(
                    start=Position(line=linenr, character=colnr + 1 - count), end=Position(line=linenr, character=colnr + 1)
                )

            else:
                erange = Range(start=Position(line=linenr, character=1), end=Position(line=linenr, character=len(line)))

            diagnostics += [Diagnostic(range=erange, message=msg, source=type(ls).__name__)]

    ls.publish_diagnostics(text_doc.uri, diagnostics)


def setup_cp2k_ls_server(server):
    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls, params: DidChangeTextDocumentParams):
        """Text document did change notification."""
        _validate(ls, params)

    @server.feature(TEXT_DOCUMENT_DID_CLOSE)
    def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
        """Text document did close notification."""
        pass

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    async def did_open(ls, params: DidOpenTextDocumentParams):
        """Text document did open notification."""
        _validate(ls, params)

    @server.feature(
        TEXT_DOCUMENT_COMPLETION,
        CompletionOptions(trigger_characters=["&"]),
    )
    def completion(ls: LanguageServer, params: CompletionParams):
        """Text document completion notification."""
        ls.show_message_log(f"Completion requested at line {params.position.line + 1}, char {params.position.character}")

        text_doc = ls.workspace.get_document(params.text_document.uri)
        lines = text_doc.source.splitlines()
        cursor_line = params.position.line
        cursor_char = params.position.character

        # Get the text up to the cursor position to determine context
        prefix = lines[cursor_line][:cursor_char] if cursor_line < len(lines) else ""

        # If we're typing a section (starts with &), provide section completions
        if prefix.strip().startswith("&") and not prefix.strip().startswith("&END"):
            # We're in a section name context - provide available sections
            # Parse up to the current line to get the parent section
            parser = CP2KInputParser()
            context = _get_section_context(lines, cursor_line, parser)

            if context:
                items = []
                for name_node in context.node.iterfind("./SECTION/NAME"):
                    if name_node.text:
                        items.append(
                            CompletionItem(
                                label=f"&{name_node.text}",
                                kind=CompletionItemKind.Class,
                                detail=f"Section in {context.name if context.name != '/' else 'root'}",
                            )
                        )
                return CompletionList(is_incomplete=False, items=items)

        # Otherwise, provide keyword/section completions for the current section
        parser = CP2KInputParser()
        context = _get_section_context(lines, cursor_line + 1, parser)

        if context:
            return CompletionList(is_incomplete=False, items=_get_completions_for_section(context))

        return CompletionList(is_incomplete=False, items=[])


cp2k_server = LanguageServer("cp2k-lsp", "v0.1")
setup_cp2k_ls_server(cp2k_server)
