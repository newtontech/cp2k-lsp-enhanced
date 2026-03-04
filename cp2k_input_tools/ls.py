"""
CP2K Language Server Protocol (LSP) Implementation

This module provides LSP features for CP2K input files:
- Auto-completion for sections, keywords, and values
- Real-time diagnostics (syntax errors, type checking)
- Hover documentation
- Go-to-definition support
"""

import io
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Union, Set
from functools import lru_cache

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    CompletionItem,
    CompletionItemKind,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    Hover,
    HoverParams,
    Location,
    LocationLink,
    DefinitionParams,
    MarkupContent,
    Position,
    Range,
    SymbolInformation,
    DocumentSymbolParams,
    SymbolKind,
)
from pygls.server import LanguageServer

from . import DEFAULT_CP2K_INPUT_XML
from .parser import CP2KInputParser
from .parser_errors import ParserError, InvalidNameError, InvalidSectionError
from .tokenizer import COMMENT_CHARS, TokenizerError

# Regular expressions for parsing
_SECTION_LINE_MATCH = re.compile(r"&(?P<name>[\w\-_]+)\s*(?P<rest>.*)")
_KEYWORD_LINE_MATCH = re.compile(r"(?P<name>[\w\-_]+)(?P<rest>.*)")
_WORD_MATCH = re.compile(r"&?[\w\-_]+")
_VALUE_SPLIT_MATCH = re.compile(r"\s+|,")

# Cache for schema
_SCHEMA_ROOT = None

def get_schema_root() -> ET.Element:
    """Get the cached schema root element."""
    global _SCHEMA_ROOT
    if _SCHEMA_ROOT is None:
        _SCHEMA_ROOT = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
    return _SCHEMA_ROOT

# ============================================================================
# Schema Helper Functions
# ============================================================================

def _schema_default_name(node: ET.Element) -> Optional[str]:
    """Get the default name for a schema node (section or keyword)."""
    name = node.find("./NAME[@type='default']")
    if name is not None and name.text:
        return name.text.upper()

    for alt in node.iterfind("./NAME"):
        if alt.text:
            return alt.text.upper()

    return None


def _schema_names(node: ET.Element) -> List[str]:
    """Get all names (including aliases) for a schema node."""
    names = []
    for name in node.iterfind("./NAME"):
        if name.text:
            names.append(name.text.upper())
    return names


def _schema_description(node: ET.Element) -> Optional[str]:
    """Get the description for a schema node."""
    desc = node.find("./DESCRIPTION")
    if desc is None or desc.text is None:
        return None

    text = desc.text.strip()
    return text if text else None


def _schema_default_value(keyword_node: ET.Element) -> Optional[str]:
    """Get the default value for a keyword."""
    default = keyword_node.find("./DEFAULT_VALUE")
    if default is not None and default.text:
        return default.text.strip()
    return None


def _schema_data_type(keyword_node: ET.Element) -> Optional[str]:
    """Get the data type for a keyword."""
    dtype = keyword_node.find("./DATA_TYPE")
    if dtype is not None:
        kind = dtype.get("kind")
        if kind:
            return kind.upper()
    return None


def _schema_allowed_values(keyword_node: ET.Element) -> List[str]:
    """Get allowed enum values for a keyword."""
    values = []
    dtype = keyword_node.find("./DATA_TYPE")
    if dtype is not None:
        for item in dtype.iterfind("./ENUMERATION/ITEM"):
            name = item.find("./NAME")
            if name is not None and name.text:
                values.append(name.text.upper())
    return values


def _strip_inline_comment(value: str) -> str:
    """Remove inline comments from a line."""
    for marker in COMMENT_CHARS:
        if marker in value:
            value = value.split(marker, 1)[0]
    return value


def _find_named_child(section_node: ET.Element, tag: str, name: str) -> Optional[ET.Element]:
    """Find a child element by name (case-insensitive)."""
    upper_name = name.upper()
    for candidate in section_node.iterfind(f"./{tag}"):
        if upper_name in _schema_names(candidate):
            return candidate
    return None


def _find_keyword_node(section_node: ET.Element, name: str) -> Optional[ET.Element]:
    """Find a keyword node within a section."""
    keyword = _find_named_child(section_node, "KEYWORD", name)
    if keyword is not None:
        return keyword

    default_keyword = section_node.find("./DEFAULT_KEYWORD")
    if default_keyword is not None and name.upper() in _schema_names(default_keyword):
        return default_keyword

    return None


def _find_section_anywhere(name: str) -> Optional[ET.Element]:
    """Find a section anywhere in the schema."""
    upper_name = name.upper()
    for section in get_schema_root().iterfind(".//SECTION"):
        if upper_name in _schema_names(section):
            return section
    return None


def _find_keyword_anywhere(name: str) -> Optional[ET.Element]:
    """Find a keyword anywhere in the schema."""
    upper_name = name.upper()
    for keyword in get_schema_root().iterfind(".//KEYWORD"):
        if upper_name in _schema_names(keyword):
            return keyword
    return None


# ============================================================================
# Context Analysis
# ============================================================================

class SectionContext:
    """Represents the current section context."""
    def __init__(self, name: str, node: ET.Element, level: int):
        self.name = name
        self.node = node
        self.level = level
        self.keywords: Set[str] = set()
        
    def is_valid_keyword(self, name: str) -> bool:
        """Check if a keyword name is valid in this section."""
        return _find_keyword_node(self.node, name) is not None
    
    def is_valid_subsection(self, name: str) -> bool:
        """Check if a section name is a valid subsection."""
        return _find_named_child(self.node, "SECTION", name) is not None


def _section_stack_until_position(text: str, line: int, character: int) -> List[ET.Element]:
    """
    Build the section stack up to a given position in the document.
    Returns a list of schema nodes, with the root at index 0.
    """
    lines = text.splitlines()
    if not lines:
        return [get_schema_root()]

    max_line = min(max(0, line), len(lines) - 1)
    relevant_lines = lines[:max_line]
    relevant_lines.append(lines[max_line][:character])

    stack: List[ET.Element] = [get_schema_root()]

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


def _get_line_context(text: str, line_num: int, character: int) -> Dict:
    """
    Analyze the context of the current line.
    Returns a dict with:
    - type: 'section', 'keyword', 'value', or 'unknown'
    - prefix: the text before cursor
    - keyword_name: if inside a keyword line
    - section_stack: the current section stack
    """
    lines = text.splitlines()
    if line_num >= len(lines):
        return {'type': 'unknown', 'prefix': ''}
    
    line = lines[line_num]
    line_before = line[:character]
    stripped = line_before.lstrip()
    
    context = {
        'type': 'unknown',
        'prefix': stripped,
        'section_stack': _section_stack_until_position(text, line_num, character)
    }
    
    # Check if we're typing a section
    if stripped.startswith('&'):
        context['type'] = 'section'
        context['prefix'] = stripped[1:]  # Remove & for matching
        return context
    
    # Check if we're typing a keyword value
    keyword_match = re.match(r'(\w+)\s+(.*)$', stripped)
    if keyword_match:
        context['type'] = 'value'
        context['keyword_name'] = keyword_match.group(1).upper()
        context['prefix'] = keyword_match.group(2)
        return context
    
    # Default to keyword completion
    context['type'] = 'keyword'
    return context


# ============================================================================
# Document Access
# ============================================================================

def _document_text(ls, uri: str) -> str:
    """Get the text content of a document."""
    text_doc = ls.workspace.get_text_document(uri)
    source = getattr(text_doc, "source", None)
    if source is not None:
        return source

    with open(text_doc.path, "r") as fhandle:
        return fhandle.read()


# ============================================================================
# Documentation Builders
# ============================================================================

def _build_section_doc(section: ET.Element) -> str:
    """Build hover documentation for a section."""
    section_name = _schema_default_name(section) or "SECTION"
    parts = [f"## &{section_name}"]

    description = _schema_description(section)
    if description:
        parts.append(description)

    # List keywords
    keywords = []
    for kw in section.iterfind("./KEYWORD"):
        name = _schema_default_name(kw)
        if name:
            keywords.append(name)
    if keywords:
        preview = ", ".join(keywords[:12])
        suffix = "..." if len(keywords) > 12 else ""
        parts.append(f"**Keywords:** {preview}{suffix}")

    # List subsections
    subsections = []
    for sub in section.iterfind("./SECTION"):
        name = _schema_default_name(sub)
        if name:
            subsections.append(name)
    if subsections:
        preview = ", ".join(subsections[:12])
        suffix = "..." if len(subsections) > 12 else ""
        parts.append(f"**Subsections:** {preview}{suffix}")
    
    # Check if section repeats
    repeats = section.get("repeats")
    if repeats == "yes":
        parts.append("*This section can be repeated*")

    return "\n\n".join(parts)


def _build_keyword_doc(keyword: ET.Element) -> str:
    """Build hover documentation for a keyword."""
    keyword_name = _schema_default_name(keyword) or "KEYWORD"
    parts = [f"## {keyword_name}"]

    description = _schema_description(keyword)
    if description:
        parts.append(description)

    # Usage
    usage = keyword.find("./USAGE")
    if usage is not None and usage.text and usage.text.strip():
        parts.append(f"**Usage:** `{usage.text.strip()}`")

    # Default value
    default = _schema_default_value(keyword)
    if default:
        parts.append(f"**Default:** `{default}`")

    # Data type
    data_type = _schema_data_type(keyword)
    if data_type:
        parts.append(f"**Type:** `{data_type}`")

    # Allowed values (enums)
    allowed_values = _schema_allowed_values(keyword)
    if allowed_values:
        enum_preview = ", ".join(allowed_values[:12])
        suffix = "..." if len(allowed_values) > 12 else ""
        parts.append(f"**Allowed values:** {enum_preview}{suffix}")
    
    # Lone keyword value
    lone_value = keyword.find("./LONE_KEYWORD_VALUE")
    if lone_value is not None and lone_value.text:
        parts.append(f"**Lone value:** `{lone_value.text.strip()}`")
    
    # Repeats
    repeats = keyword.get("repeats")
    if repeats == "yes":
        parts.append("*This keyword can be repeated*")
    
    # Deprecated
    deprecated = keyword.get("deprecated")
    if deprecated == "yes":
        parts.append("⚠️ **Deprecated**")

    return "\n\n".join(parts)


def _build_enum_value_doc(keyword: ET.Element, value: str) -> Optional[str]:
    """Build documentation for an enum value."""
    data_type = keyword.find("./DATA_TYPE")
    if data_type is None:
        return None

    upper_value = value.upper()
    for item in data_type.iterfind("./ENUMERATION/ITEM"):
        name_node = item.find("./NAME")
        if name_node is None or not name_node.text:
            continue
        if name_node.text.upper() == upper_value:
            description = _schema_description(item)
            return description or f"Value `{value}` for keyword `{_schema_default_name(keyword)}`"
    return None


# ============================================================================
# Completion Providers
# ============================================================================

def _completion_items(items: List[Tuple[str, str, Optional[str]]], kind: CompletionItemKind, prefix: str, max_items: int = 50) -> List[CompletionItem]:
    """Create completion items from a list of (label, detail, doc) tuples."""
    upper_prefix = prefix.upper()
    seen = set()
    completions = []

    for label, detail, doc in items:
        if upper_prefix and not label.upper().startswith(upper_prefix):
            continue
        if label in seen:
            continue
        seen.add(label)
        
        item = CompletionItem(
            label=label, 
            kind=kind, 
            detail=detail
        )
        if doc:
            item.documentation = MarkupContent(kind="markdown", value=doc)
        completions.append(item)
        
        if len(completions) >= max_items:
            break

    return completions


def _provide_section_completion(current_section: ET.Element, line_before_cursor: str) -> List[CompletionItem]:
    """Provide section name completions."""
    typed = line_before_cursor.lstrip()[1:].upper() if line_before_cursor.lstrip().startswith('&') else ""
    prefix = f"&{typed}" if typed else ""
    candidates: List[Tuple[str, str, Optional[str]]] = []

    for section in current_section.iterfind("./SECTION"):
        name = _schema_default_name(section)
        if name:
            doc = _schema_description(section)
            candidates.append((f"&{name}", "CP2K section", doc))

    return _completion_items(candidates, CompletionItemKind.Module, prefix)


def _provide_keyword_completion(current_section: ET.Element, prefix: str) -> List[CompletionItem]:
    """Provide keyword completions for the current section."""
    upper_prefix = prefix.upper()
    candidates: List[Tuple[str, str, Optional[str]]] = []

    # Add subsections as completions
    for subsection in current_section.iterfind("./SECTION"):
        name = _schema_default_name(subsection)
        if name:
            doc = _schema_description(subsection)
            candidates.append((name, "CP2K subsection", doc))

    # Add keywords
    for keyword in current_section.iterfind("./KEYWORD"):
        name = _schema_default_name(keyword)
        if name:
            data_type = _schema_data_type(keyword)
            default = _schema_default_value(keyword)
            doc = _build_keyword_doc(keyword)
            detail = f"CP2K keyword ({data_type})" if data_type else "CP2K keyword"
            if default:
                detail += f", default={default}"
            candidates.append((name, detail, doc))

    # Add default keyword if present
    default_keyword = current_section.find("./DEFAULT_KEYWORD")
    if default_keyword is not None:
        name = _schema_default_name(default_keyword)
        if name:
            doc = _build_keyword_doc(default_keyword)
            candidates.append((name, "CP2K default keyword", doc))

    return _completion_items(candidates, CompletionItemKind.Property, upper_prefix)


def _provide_value_completion(current_section: ET.Element, keyword_name: str, value_prefix: str) -> List[CompletionItem]:
    """Provide value completions for a keyword."""
    keyword = _find_keyword_node(current_section, keyword_name)
    if keyword is None:
        return []

    suggestions: List[Tuple[str, str, Optional[str]]] = []
    data_type = _schema_data_type(keyword)
    
    if data_type == "KEYWORD":
        # Enum values
        for item in keyword.iterfind("./DATA_TYPE/ENUMERATION/ITEM"):
            name = item.find("./NAME")
            if name is not None and name.text:
                doc = _schema_description(item)
                suggestions.append((name.text, "Allowed value", doc))
    elif data_type == "LOGICAL":
        # Boolean values
        suggestions.extend([
            ("T", "Boolean true", None),
            ("F", "Boolean false", None),
            (".TRUE.", "Fortran-style true", None),
            (".FALSE.", "Fortran-style false", None),
        ])
    elif data_type in ["REAL", "REAL_LIST"]:
        # Common units for real values
        units_elem = keyword.find("./DATA_TYPE/UNIT")
        if units_elem is not None:
            # Could provide unit completions here
            pass

    # Lone keyword value
    lone_keyword_value = keyword.find("./LONE_KEYWORD_VALUE")
    if lone_keyword_value is not None and lone_keyword_value.text:
        suggestions.append((lone_keyword_value.text.strip(), "Lone keyword value", None))

    return _completion_items(suggestions, CompletionItemKind.EnumMember, value_prefix)


def _word_at_position(line: str, character: int) -> Optional[str]:
    """Get the word at a specific character position in a line."""
    for match in _WORD_MATCH.finditer(line):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


# ============================================================================
# LSP Feature Handlers
# ============================================================================

def _completion(ls, params: CompletionParams) -> List[CompletionItem]:
    """Handle completion requests."""
    text = _document_text(ls, params.text_document.uri)
    lines = text.splitlines()

    if params.position.line >= len(lines):
        return []

    line = lines[params.position.line]
    line_before_cursor = line[: params.position.character]
    stripped_before_cursor = line_before_cursor.lstrip()
    section_stack = _section_stack_until_position(text, params.position.line, params.position.character)
    current_section = section_stack[-1]

    # Section completion (&SECTION)
    if stripped_before_cursor.startswith("&"):
        return _provide_section_completion(current_section, line_before_cursor)

    # Keyword value completion (KEYWORD <value>)
    keyword_match = _KEYWORD_LINE_MATCH.match(_strip_inline_comment(stripped_before_cursor))
    if keyword_match:
        keyword_name = keyword_match.group("name").upper()
        keyword_rest = keyword_match.group("rest")
        if keyword_rest.startswith(" ") or keyword_rest.startswith("\t"):
            parts = keyword_rest.split()
            value_prefix = parts[-1] if parts else ""
            return _provide_value_completion(current_section, keyword_name, value_prefix)

    # Default: keyword completion
    return _provide_keyword_completion(current_section, stripped_before_cursor)


def _hover(ls, params: HoverParams) -> Optional[Hover]:
    """Handle hover requests."""
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

    # Section hover
    if upper_word.startswith("&"):
        section = _find_named_child(current_section, "SECTION", upper_word[1:]) or _find_section_anywhere(upper_word[1:])
        if section is None:
            return None
        return Hover(contents=MarkupContent(kind="markdown", value=_build_section_doc(section)))

    # Keyword hover (in current section context)
    keyword = _find_keyword_node(current_section, upper_word)
    if keyword is not None:
        return Hover(contents=MarkupContent(kind="markdown", value=_build_keyword_doc(keyword)))

    # Check if it's a value of a keyword
    stripped_line = _strip_inline_comment(line.strip())
    keyword_match = _KEYWORD_LINE_MATCH.match(stripped_line)
    if keyword_match:
        keyword = _find_keyword_node(current_section, keyword_match.group("name"))
        if keyword is not None:
            # Check for enum value documentation
            enum_doc = _build_enum_value_doc(keyword, upper_word)
            if enum_doc:
                return Hover(contents=MarkupContent(kind="markdown", value=f"## {word}\n\n{enum_doc}"))

    # Global keyword search
    keyword_global = _find_keyword_anywhere(upper_word)
    if keyword_global is not None:
        return Hover(contents=MarkupContent(kind="markdown", value=_build_keyword_doc(keyword_global)))

    return None


def _definition(ls, params: DefinitionParams) -> Optional[Location]:
    """Handle go-to-definition requests."""
    text = _document_text(ls, params.text_document.uri)
    lines = text.splitlines()
    if params.position.line >= len(lines):
        return None

    line = lines[params.position.line]
    word = _word_at_position(line, params.position.character)
    if not word:
        return None

    upper_word = word.upper()

    # Handle section references
    if upper_word.startswith("&"):
        section_name = upper_word[1:]
        # Find the section definition in the document
        for i, doc_line in enumerate(lines):
            match = re.match(rf'&{section_name}\b', doc_line.strip(), re.IGNORECASE)
            if match and i != params.position.line:
                return Location(
                    uri=params.text_document.uri,
                    range=Range(
                        start=Position(line=i, character=doc_line.index('&')),
                        end=Position(line=i, character=doc_line.index('&') + len(word))
                    )
                )

    # Handle @SET variable definitions
    if line.strip().upper().startswith('@SET'):
        var_match = re.match(r'@SET\s+(\S+)', line.strip(), re.IGNORECASE)
        if var_match and var_match.group(1).upper() == upper_word:
            # Find where this variable is used
            for i, doc_line in enumerate(lines):
                if i != params.position.line and upper_word in doc_line.upper():
                    col = doc_line.upper().find(upper_word)
                    return Location(
                        uri=params.text_document.uri,
                        range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(word))
                        )
                    )

    return None


def _document_symbol(ls, params: DocumentSymbolParams) -> List[SymbolInformation]:
    """Handle document symbol requests (outline view)."""
    text = _document_text(ls, params.text_document.uri)
    lines = text.splitlines()
    symbols: List[SymbolInformation] = []
    section_stack: List[Tuple[str, int]] = []  # (name, line)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('&'):
            continue

        match = _SECTION_LINE_MATCH.match(stripped)
        if not match:
            continue

        name = match.group("name").upper()
        
        if name == "END":
            # Pop from stack
            if section_stack:
                section_stack.pop()
            continue

        # Add symbol for section
        char_pos = line.index('&')
        symbol = SymbolInformation(
            name=name,
            kind=SymbolKind.Namespace,
            location=Location(
                uri=params.text_document.uri,
                range=Range(
                    start=Position(line=i, character=char_pos),
                    end=Position(line=i, character=char_pos + 1 + len(name))
                )
            ),
            container_name=section_stack[-1][0] if section_stack else None
        )
        symbols.append(symbol)
        section_stack.append((name, i))

    return symbols


def _validate(ls, params: Union[DidChangeTextDocumentParams, DidCloseTextDocumentParams, DidOpenTextDocumentParams]):
    """Validate a document and publish diagnostics."""
    ls.show_message_log("Validating CP2K input...")

    diagnostics = []
    parser = CP2KInputParser()
    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    content = _document_text(ls, params.text_document.uri)

    with io.StringIO(content) as fhandle:
        try:
            parser.parse(fhandle)
        except (TokenizerError, ParserError, InvalidNameError, InvalidSectionError) as exc:
            # Extract context information
            ctx = exc.args[1] if len(exc.args) > 1 else None
            if ctx:
                line = ctx.line.rstrip() if hasattr(ctx, 'line') else ""
                linenr = ctx.linenr - 1 if hasattr(ctx, 'linenr') else 0
                colnr = ctx.colnr if hasattr(ctx, 'colnr') else 0
                
                msg = f"{exc.args[0]}"
                if exc.__cause__:
                    msg += f" ({exc.__cause__})"

                # Create diagnostic range
                if colnr is not None:
                    count = max(1, 1)
                    erange = Range(
                        start=Position(line=linenr, character=max(0, colnr - count)),
                        end=Position(line=linenr, character=colnr + 1)
                    )
                else:
                    erange = Range(
                        start=Position(line=linenr, character=0),
                        end=Position(line=linenr, character=len(line))
                    )

                diagnostics.append(Diagnostic(
                    range=erange, 
                    message=msg, 
                    source=type(ls).__name__,
                    severity=DiagnosticSeverity.Error
                ))
        except Exception as exc:
            # Catch any other exceptions
            diagnostics.append(Diagnostic(
                range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
                message=f"Parse error: {str(exc)}",
                source=type(ls).__name__,
                severity=DiagnosticSeverity.Error
            ))

    # Additional semantic validation
    lines = content.splitlines()
    section_stack = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for unclosed sections
        if stripped.startswith('&') and not stripped.startswith('&END'):
            match = _SECTION_LINE_MATCH.match(stripped)
            if match:
                section_name = match.group("name").upper()
                if section_name != "END":
                    section_stack.append((section_name, i))
        
        if stripped.upper().startswith('&END'):
            match = _SECTION_LINE_MATCH.match(stripped)
            if match:
                end_name = match.group("rest").strip().upper() if match.group("rest") else ""
                if section_stack:
                    opened_name, opened_line = section_stack[-1]
                    if end_name and end_name != opened_name:
                        diagnostics.append(Diagnostic(
                            range=Range(
                                start=Position(line=i, character=line.index('&')),
                                end=Position(line=i, character=len(line))
                            ),
                            message=f"Mismatched section: expected &END {opened_name}, found &END {end_name}",
                            source=type(ls).__name__,
                            severity=DiagnosticSeverity.Warning
                        ))
                    section_stack.pop()
    
    # Report unclosed sections
    for section_name, line_num in section_stack:
        diagnostics.append(Diagnostic(
            range=Range(
                start=Position(line=line_num, character=0),
                end=Position(line=line_num, character=len(lines[line_num]) if line_num < len(lines) else 0)
            ),
            message=f"Unclosed section: &{section_name}",
            source=type(ls).__name__,
            severity=DiagnosticSeverity.Error
        ))

    ls.publish_diagnostics(text_doc.uri, diagnostics)


# ============================================================================
# Server Setup
# ============================================================================

def setup_cp2k_ls_server(server):
    """Set up the CP2K Language Server with all features."""
    
    @server.feature(TEXT_DOCUMENT_DID_CHANGE)
    def did_change(ls, params: DidChangeTextDocumentParams):
        """Text document did change notification."""
        _validate(ls, params)

    @server.feature(TEXT_DOCUMENT_DID_CLOSE)
    def did_close(ls: LanguageServer, params: DidCloseTextDocumentParams):
        """Text document did close notification."""
        # Clear diagnostics when document is closed
        ls.publish_diagnostics(params.text_document.uri, [])

    @server.feature(TEXT_DOCUMENT_DID_OPEN)
    async def did_open(ls, params: DidOpenTextDocumentParams):
        """Text document did open notification."""
        _validate(ls, params)

    @server.feature(TEXT_DOCUMENT_COMPLETION)
    def completion(ls, params: CompletionParams):
        """Completion for sections, keywords and values."""
        return _completion(ls, params)

    @server.feature(TEXT_DOCUMENT_HOVER)
    def hover(ls, params: HoverParams):
        """Hover documentation for sections, keywords and values."""
        return _hover(ls, params)
    
    @server.feature(TEXT_DOCUMENT_DEFINITION)
    def definition(ls, params: DefinitionParams):
        """Go-to-definition for sections and variables."""
        return _definition(ls, params)
    
    @server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(ls, params: DocumentSymbolParams):
        """Document symbols for outline view."""
        return _document_symbol(ls, params)


# Create the global server instance
cp2k_server = LanguageServer("cp2k-lsp", "v0.2")
setup_cp2k_ls_server(cp2k_server)
