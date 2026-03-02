import io
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple, Union

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_HOVER,
    CompletionItem,
    CompletionItemKind,
    CompletionParams,
    Diagnostic,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Hover,
    HoverParams,
    MarkupContent,
    Position,
    Range,
)
from pygls.server import LanguageServer

from . import DEFAULT_CP2K_INPUT_XML
from .parser import CP2KInputParser
from .parser_errors import ParserError
from .tokenizer import COMMENT_CHARS, TokenizerError

_SECTION_LINE_MATCH = re.compile(r"&(?P<name>[\w\-_]+)\s*(?P<rest>.*)")
_KEYWORD_LINE_MATCH = re.compile(r"(?P<name>[\w\-_]+)(?P<rest>.*)")
_WORD_MATCH = re.compile(r"&?[\w\-_]+")

_SCHEMA_ROOT = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()


def _schema_default_name(node: ET.Element) -> Optional[str]:
    name = node.find("./NAME[@type='default']")
    if name is not None and name.text:
        return name.text.upper()

    for alt in node.iterfind("./NAME"):
        if alt.text:
            return alt.text.upper()

    return None


def _schema_names(node: ET.Element) -> List[str]:
    names = []
    for name in node.iterfind("./NAME"):
        if name.text:
            names.append(name.text.upper())
    return names


def _schema_description(node: ET.Element) -> Optional[str]:
    desc = node.find("./DESCRIPTION")
    if desc is None or desc.text is None:
        return None

    text = desc.text.strip()
    return text if text else None


def _strip_inline_comment(value: str) -> str:
    for marker in COMMENT_CHARS:
        value = value.split(marker, 1)[0]
    return value


def _find_named_child(section_node: ET.Element, tag: str, name: str) -> Optional[ET.Element]:
    upper_name = name.upper()
    for candidate in section_node.iterfind(f"./{tag}"):
        if upper_name in _schema_names(candidate):
            return candidate
    return None


def _find_keyword_node(section_node: ET.Element, name: str) -> Optional[ET.Element]:
    keyword = _find_named_child(section_node, "KEYWORD", name)
    if keyword is not None:
        return keyword

    default_keyword = section_node.find("./DEFAULT_KEYWORD")
    if default_keyword is not None and name.upper() in _schema_names(default_keyword):
        return default_keyword

    return None


def _find_section_anywhere(name: str) -> Optional[ET.Element]:
    upper_name = name.upper()
    for section in _SCHEMA_ROOT.iterfind(".//SECTION"):
        if upper_name in _schema_names(section):
            return section
    return None


def _find_keyword_anywhere(name: str) -> Optional[ET.Element]:
    upper_name = name.upper()
    for keyword in _SCHEMA_ROOT.iterfind(".//KEYWORD"):
        if upper_name in _schema_names(keyword):
            return keyword
    return None


def _section_stack_until_position(text: str, line: int, character: int) -> List[ET.Element]:
    lines = text.splitlines()
    if not lines:
        return [_SCHEMA_ROOT]

    max_line = min(max(0, line), len(lines) - 1)
    relevant_lines = lines[:max_line]
    relevant_lines.append(lines[max_line][:character])

    stack: List[ET.Element] = [_SCHEMA_ROOT]

    for raw_line in relevant_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(COMMENT_CHARS) or stripped.startswith("@"):
            continue
        if not stripped.startswith("&"):
            continue

        match = _SECTION_LINE_MATCH.match(stripped)
        if not match:
            continue

        section_name = match.group("name").upper()
        section_rest = _strip_inline_comment(match.group("rest")).strip()

        if section_name == "END":
            if len(stack) == 1:
                continue

            end_name = section_rest.split(maxsplit=1)[0].upper() if section_rest else ""
            if not end_name or end_name in _schema_names(stack[-1]):
                stack.pop()
                continue

            # Best effort recovery for mismatched end tags.
            for idx in range(len(stack) - 1, 0, -1):
                if end_name in _schema_names(stack[idx]):
                    del stack[idx:]
                    break
            else:
                stack.pop()
            continue

        next_section = _find_named_child(stack[-1], "SECTION", section_name)
        if next_section is not None:
            stack.append(next_section)

    return stack


def _document_text(ls, uri: str) -> str:
    text_doc = ls.workspace.get_text_document(uri)
    source = getattr(text_doc, "source", None)
    if source is not None:
        return source

    with open(text_doc.path, "r") as fhandle:
        return fhandle.read()


def _build_section_doc(section: ET.Element) -> str:
    section_name = _schema_default_name(section) or "SECTION"
    parts = [f"## &{section_name}"]

    description = _schema_description(section)
    if description:
        parts.append(description)

    keywords = []
    for kw in section.iterfind("./KEYWORD"):
        name = _schema_default_name(kw)
        if name:
            keywords.append(name)
    if keywords:
        preview = ", ".join(keywords[:12])
        suffix = "..." if len(keywords) > 12 else ""
        parts.append(f"**Keywords:** {preview}{suffix}")

    subsections = []
    for sub in section.iterfind("./SECTION"):
        name = _schema_default_name(sub)
        if name:
            subsections.append(name)
    if subsections:
        preview = ", ".join(subsections[:12])
        suffix = "..." if len(subsections) > 12 else ""
        parts.append(f"**Subsections:** {preview}{suffix}")

    return "\n\n".join(parts)


def _build_keyword_doc(keyword: ET.Element) -> str:
    keyword_name = _schema_default_name(keyword) or "KEYWORD"
    parts = [f"## {keyword_name}"]

    description = _schema_description(keyword)
    if description:
        parts.append(description)

    usage = keyword.find("./USAGE")
    if usage is not None and usage.text and usage.text.strip():
        parts.append(f"**Usage:** `{usage.text.strip()}`")

    default = keyword.find("./DEFAULT_VALUE")
    if default is not None and default.text and default.text.strip():
        parts.append(f"**Default:** `{default.text.strip()}`")

    datatype = keyword.find("./DATA_TYPE")
    if datatype is not None:
        kind = datatype.get("kind")
        if kind:
            parts.append(f"**Type:** `{kind}`")

        values = [name.text for name in datatype.iterfind("./ENUMERATION/ITEM/NAME") if name.text]
        if values:
            enum_preview = ", ".join(values[:12])
            suffix = "..." if len(values) > 12 else ""
            parts.append(f"**Allowed values:** {enum_preview}{suffix}")

    return "\n\n".join(parts)


def _completion_items(items: List[Tuple[str, str]], kind: CompletionItemKind, prefix: str) -> List[CompletionItem]:
    upper_prefix = prefix.upper()
    seen = set()
    completions = []

    for label, detail in items:
        if upper_prefix and not label.upper().startswith(upper_prefix):
            continue
        if label in seen:
            continue
        seen.add(label)
        completions.append(CompletionItem(label=label, kind=kind, detail=detail))

    return completions


def _provide_section_completion(current_section: ET.Element, line_before_cursor: str) -> List[CompletionItem]:
    typed = line_before_cursor.lstrip()[1:].upper()
    prefix = f"&{typed}" if typed else ""
    candidates: List[Tuple[str, str]] = []

    for section in current_section.iterfind("./SECTION"):
        name = _schema_default_name(section)
        if name:
            candidates.append((f"&{name}", "CP2K section"))

    return _completion_items(candidates, CompletionItemKind.Module, prefix)


def _provide_keyword_completion(current_section: ET.Element, line_before_cursor: str) -> List[CompletionItem]:
    typed = line_before_cursor.lstrip().upper()
    candidates: List[Tuple[str, str]] = []

    for keyword in current_section.iterfind("./KEYWORD"):
        name = _schema_default_name(keyword)
        if name:
            candidates.append((name, "CP2K keyword"))

    default_keyword = current_section.find("./DEFAULT_KEYWORD")
    if default_keyword is not None:
        name = _schema_default_name(default_keyword)
        if name:
            candidates.append((name, "CP2K default keyword"))

    return _completion_items(candidates, CompletionItemKind.Property, typed)


def _provide_value_completion(current_section: ET.Element, keyword_name: str, value_prefix: str) -> List[CompletionItem]:
    keyword = _find_keyword_node(current_section, keyword_name)
    if keyword is None:
        return []

    suggestions: List[Tuple[str, str]] = []
    data_type = keyword.find("./DATA_TYPE")
    if data_type is None:
        return []

    kind = data_type.get("kind", "").lower()
    if kind == "keyword":
        for item in data_type.iterfind("./ENUMERATION/ITEM"):
            name = item.find("./NAME")
            if name is not None and name.text:
                suggestions.append((name.text, "Allowed value"))
    elif kind == "logical":
        suggestions.extend(
            [
                ("T", "Boolean true"),
                ("F", "Boolean false"),
                (".TRUE.", "Boolean true"),
                (".FALSE.", "Boolean false"),
            ]
        )

    lone_keyword_value = keyword.find("./LONE_KEYWORD_VALUE")
    if lone_keyword_value is not None and lone_keyword_value.text:
        suggestions.append((lone_keyword_value.text.strip(), "Lone keyword value"))

    return _completion_items(suggestions, CompletionItemKind.EnumMember, value_prefix)


def _word_at_position(line: str, character: int) -> Optional[str]:
    for match in _WORD_MATCH.finditer(line):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def _hover_for_value(keyword: ET.Element, value: str) -> Optional[Hover]:
    data_type = keyword.find("./DATA_TYPE")
    if data_type is None:
        return None

    upper_value = value.upper()
    for item in data_type.iterfind("./ENUMERATION/ITEM"):
        name_node = item.find("./NAME")
        if name_node is None or not name_node.text:
            continue
        if name_node.text.upper() != upper_value:
            continue

        description = _schema_description(item) or "CP2K value"
        return Hover(contents=MarkupContent(kind="markdown", value=f"## {name_node.text}\n\n{description}"))

    return None


def _completion(ls, params: CompletionParams) -> List[CompletionItem]:
    text = _document_text(ls, params.text_document.uri)
    lines = text.splitlines()

    if params.position.line >= len(lines):
        return []

    line = lines[params.position.line]
    line_before_cursor = line[: params.position.character]
    stripped_before_cursor = line_before_cursor.lstrip()
    section_stack = _section_stack_until_position(text, params.position.line, params.position.character)
    current_section = section_stack[-1]

    if stripped_before_cursor.startswith("&"):
        return _provide_section_completion(current_section, line_before_cursor)

    keyword_match = _KEYWORD_LINE_MATCH.match(_strip_inline_comment(stripped_before_cursor))
    if keyword_match:
        keyword_name = keyword_match.group("name").upper()
        keyword_rest = keyword_match.group("rest")
        if keyword_rest.startswith(" ") or keyword_rest.startswith("\t"):
            parts = keyword_rest.split()
            value_prefix = parts[-1] if parts else ""
            return _provide_value_completion(current_section, keyword_name, value_prefix)

    return _provide_keyword_completion(current_section, line_before_cursor)


def _hover(ls, params: HoverParams) -> Optional[Hover]:
    text = _document_text(ls, params.text_document.uri)
    lines = text.splitlines()
    if params.position.line >= len(lines):
        return None

    line = lines[params.position.line]
    word = _word_at_position(line, params.position.character)
    if not word:
        return None

    section_stack = _section_stack_until_position(text, params.position.line, params.position.character)
    current_section = section_stack[-1]
    upper_word = word.upper()

    if upper_word.startswith("&"):
        section = _find_named_child(current_section, "SECTION", upper_word[1:]) or _find_section_anywhere(upper_word[1:])
        if section is None:
            return None
        return Hover(contents=MarkupContent(kind="markdown", value=_build_section_doc(section)))

    keyword = _find_keyword_node(current_section, upper_word)
    if keyword is not None:
        return Hover(contents=MarkupContent(kind="markdown", value=_build_keyword_doc(keyword)))

    stripped_line = _strip_inline_comment(line.strip())
    keyword_match = _KEYWORD_LINE_MATCH.match(stripped_line)
    if keyword_match:
        keyword = _find_keyword_node(current_section, keyword_match.group("name"))
        if keyword is not None:
            hover = _hover_for_value(keyword, upper_word)
            if hover is not None:
                return hover

    keyword_global = _find_keyword_anywhere(upper_word)
    if keyword_global is not None:
        return Hover(contents=MarkupContent(kind="markdown", value=_build_keyword_doc(keyword_global)))

    return None


def _validate(ls, params: Union[DidChangeTextDocumentParams, DidCloseTextDocumentParams, DidOpenTextDocumentParams]):
    ls.show_message_log("Validating CP2K input...")

    diagnostics = []
    parser = CP2KInputParser()
    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    content = _document_text(ls, params.text_document.uri)

    with io.StringIO(content) as fhandle:
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

    @server.feature(TEXT_DOCUMENT_COMPLETION)
    def completion(ls, params: CompletionParams):
        """Completion for sections, keywords and basic values."""
        return _completion(ls, params)

    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(ls, params: HoverParams):
        """Hover documentation for sections, keywords and enum values."""
        return _hover(ls, params)


cp2k_server = LanguageServer("cp2k-lsp", "v0.1")
setup_cp2k_ls_server(cp2k_server)
