"""CP2K input file formatter using parser/AST-based approach with regex fallback."""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from lsprotocol.types import Position, Range, TextEdit

_SECTION_START_RE = re.compile(r"^(\s*)&([\w\-_]+)\s*(.*)")
_SECTION_END_RE = re.compile(r"^(\s*)&(END)\s+([\w\-_]+)(.*)", re.IGNORECASE)
_DIRECTIVE_RE = re.compile(r"^(\s*)(@INCLUDE|@XCTYPE|@SET|@IF|@ENDIF)\b\s*(.*)", re.IGNORECASE)
_COMMENT_RE = re.compile(r"^(\s*)([!#].*)$")
_BLANK_LINE_RE = re.compile(r"^\s*$")


@dataclass
class FormatLine:
    """Represents a single line with its formatting context."""
    original: str
    indent_level: int = 0
    is_section_start: bool = False
    is_section_end: bool = False
    is_comment: bool = False
    is_blank: bool = False
    is_directive: bool = False
    section_name: Optional[str] = None
    comment: Optional[str] = None
    content: str = ""


def _parse_line(line: str) -> FormatLine:
    """Parse a single line to determine its type."""
    fl = FormatLine(original=line)

    if _BLANK_LINE_RE.match(line):
        fl.is_blank = True
        return fl

    if _COMMENT_RE.match(line):
        fl.is_comment = True
        match = _COMMENT_RE.match(line)
        fl.content = match.group(2)
        return fl

    # Check directives
    if _DIRECTIVE_RE.match(line):
        fl.is_directive = True
        match = _DIRECTIVE_RE.match(line)
        fl.content = line.strip()
        return fl

    # Check section end
    end_match = _SECTION_END_RE.match(line)
    if end_match:
        fl.is_section_end = True
        fl.section_name = end_match.group(3).strip().upper()
        fl.content = line.strip()
        return fl

    # Check section start
    sec_match = _SECTION_START_RE.match(line)
    if sec_match:
        fl.is_section_start = True
        fl.section_name = sec_match.group(2).strip().upper()
        fl.content = line.strip()
        return fl

    # Regular keyword line
    fl.content = line.strip()
    return fl


def _extract_inline_comment(content: str) -> Tuple[str, Optional[str]]:
    """Extract inline comment from a line, respecting strings."""
    in_string = False
    string_char = None
    i = 0
    while i < len(content):
        c = content[i]
        if in_string:
            if c == string_char and (i == 0 or content[i - 1] != '\\'):
                in_string = False
        elif c in ('"', "'"):
            in_string = True
            string_char = c
        elif c in ('!', '#') and (i == 0 or content[i - 1] != '\\'):
            return content[:i].rstrip(), content[i:]
        i += 1
    return content, None


def format_document(text: str, indent_str: str = "  ") -> List[TextEdit]:
    """Format a CP2K input document. Returns TextEdit list for full document replacement."""
    lines = text.split('\n')
    formatted_lines = []
    indent_level = 0
    pending_blank_lines = 0
    section_stack = []  # Stack of section names for &END matching

    for line in lines:
        fl = _parse_line(line)

        if fl.is_blank:
            pending_blank_lines += 1
            continue

        # Adjust indent for section ends (dedent before writing)
        if fl.is_section_end:
            indent_level = max(0, indent_level - 1)
            # Pop from section stack
            if section_stack:
                section_stack.pop()

        # Flush pending blank lines (at most one between content lines)
        if pending_blank_lines > 0 and formatted_lines:
            formatted_lines.append("")
            pending_blank_lines = 0
        elif pending_blank_lines > 0 and not formatted_lines:
            pending_blank_lines = 0  # Skip leading blanks

        # Format based on line type
        indent = indent_str * indent_level

        if fl.is_comment:
            formatted_lines.append(indent + fl.content)
        elif fl.is_directive:
            # Keep directives at current indent level
            formatted_lines.append(indent + fl.content)
        elif fl.is_section_start:
            # Format: &SECTION param ! comment
            content = fl.content
            # Ensure proper casing: &SECTIONNAME uppercase
            sec_match = _SECTION_START_RE.match(content)
            if sec_match:
                sec_name = sec_match.group(2).upper()
                sec_param = sec_match.group(3)
                if sec_param:
                    formatted_lines.append(indent + f"&{sec_name} {sec_param}")
                else:
                    formatted_lines.append(indent + f"&{sec_name}")
            else:
                formatted_lines.append(indent + content)
            indent_level += 1
            section_stack.append(fl.section_name)
        elif fl.is_section_end:
            # Format: &END SECTIONNAME
            end_match = _SECTION_END_RE.match(fl.content)
            if end_match:
                end_name = end_match.group(3).upper()
                end_rest = end_match.group(4)
                if end_rest:
                    formatted_lines.append(indent + f"&END {end_name}{end_rest}")
                else:
                    formatted_lines.append(indent + f"&END {end_name}")
            else:
                formatted_lines.append(indent + fl.content)
        else:
            # Regular keyword line
            content, inline_comment = _extract_inline_comment(fl.content)
            content = content.strip()
            if content:
                # Normalize keyword casing to uppercase
                kw_match = re.match(r'^([\w\-_]+)\s*(.*)', content)
                if kw_match:
                    kw_name = kw_match.group(1).upper()
                    kw_value = kw_match.group(2)
                    if inline_comment:
                        formatted_lines.append(indent + f"{kw_name} {kw_value} {inline_comment}")
                    else:
                        formatted_lines.append(indent + f"{kw_name} {kw_value}".rstrip())
                else:
                    if inline_comment:
                        formatted_lines.append(indent + f"{content} {inline_comment}")
                    else:
                        formatted_lines.append(indent + content)

    # Build single TextEdit for the entire document
    line_count = len(lines)
    new_text = '\n'.join(formatted_lines)
    # Ensure trailing newline if original had one
    if text.endswith('\n') and not new_text.endswith('\n'):
        new_text += '\n'

    return [TextEdit(
        range=Range(start=Position(line=0, character=0), end=Position(line=line_count, character=0)),
        new_text=new_text
    )]


def format_range(text: str, start_line: int, end_line: int, indent_str: str = "  ") -> List[TextEdit]:
    """Format a range of lines in a CP2K input document."""
    lines = text.split('\n')
    # Extract the range, format it, and return edits
    range_lines = lines[start_line:end_line]
    range_text = '\n'.join(range_lines)

    formatted = format_document(range_text, indent_str)
    if not formatted:
        return []

    return [TextEdit(
        range=Range(start=Position(line=start_line, character=0), end=Position(line=end_line, character=0)),
        new_text=formatted[0].new_text
    )]
