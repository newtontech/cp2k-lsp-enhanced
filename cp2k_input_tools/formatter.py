"""CP2K input file formatter using parser/AST-based approach with regex fallback."""

import re
from dataclasses import dataclass
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

    match = _COMMENT_RE.match(line)
    if match:
        fl.is_comment = True
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


def _format_lines(lines: List[str], indent_str: str = "  ") -> List[str]:
    """Format a list of lines, returning the formatted lines."""
    formatted_lines: List[str] = []
    indent_level = 0
    pending_blank_lines = 0

    for line in lines:
        fl = _parse_line(line)

        if fl.is_blank:
            pending_blank_lines += 1
            continue

        if fl.is_section_end:
            indent_level = max(0, indent_level - 1)

        if pending_blank_lines > 0 and formatted_lines:
            formatted_lines.append("")
            pending_blank_lines = 0
        elif pending_blank_lines > 0 and not formatted_lines:
            pending_blank_lines = 0

        indent = indent_str * indent_level

        if fl.is_comment:
            formatted_lines.append(indent + fl.content)
        elif fl.is_directive:
            formatted_lines.append(indent + fl.content)
        elif fl.is_section_start:
            sec_match = _SECTION_START_RE.match(fl.content)
            if sec_match:
                sec_name = sec_match.group(2).upper()
                sec_param = sec_match.group(3)
                if sec_param:
                    formatted_lines.append(indent + f"&{sec_name} {sec_param}")
                else:
                    formatted_lines.append(indent + f"&{sec_name}")
            else:
                formatted_lines.append(indent + fl.content)
            indent_level += 1
        elif fl.is_section_end:
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
            content, inline_comment = _extract_inline_comment(fl.content)
            content = content.strip()
            if content:
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

    return formatted_lines


def _compute_diff_edits(original_lines: List[str], formatted_lines: List[str]) -> List[TextEdit]:
    """Compute minimal TextEdits by comparing original and formatted lines.

    Handles trailing empty lines from split('\n') on text ending with newline.
    """
    edits: List[TextEdit] = []
    orig_idx = 0
    fmt_idx = 0

    orig_len = len(original_lines)
    fmt_len = len(formatted_lines)

    while orig_idx < orig_len or fmt_idx < fmt_len:
        if orig_idx >= orig_len:
            remaining = '\n'.join(formatted_lines[fmt_idx:])
            if remaining:
                edits.append(TextEdit(
                    range=Range(
                        start=Position(line=orig_idx, character=0),
                        end=Position(line=orig_idx, character=0),
                    ),
                    new_text=remaining,
                ))
            break

        if fmt_idx >= fmt_len:
            remaining_count = orig_len - orig_idx
            edits.append(TextEdit(
                range=Range(
                    start=Position(line=orig_idx, character=0),
                    end=Position(line=orig_idx + remaining_count, character=0),
                ),
                new_text='',
            ))
            break

        if original_lines[orig_idx] == formatted_lines[fmt_idx]:
            orig_idx += 1
            fmt_idx += 1
            continue

        run_start_orig = orig_idx
        run_start_fmt = fmt_idx

        while (orig_idx < orig_len and fmt_idx < fmt_len
               and original_lines[orig_idx] != formatted_lines[fmt_idx]):
            orig_idx += 1
            fmt_idx += 1

        run_end_orig = orig_idx
        run_end_fmt = fmt_idx

        new_text = '\n'.join(formatted_lines[run_start_fmt:run_end_fmt])
        edits.append(TextEdit(
            range=Range(
                start=Position(line=run_start_orig, character=0),
                end=Position(line=run_end_orig, character=0),
            ),
            new_text=new_text,
        ))

    return edits


def _is_formatting_safe(text: str) -> bool:
    """Check if formatting is safe (no ambiguous constructs that could change semantics)."""
    lines = text.split('\n')
    for line in lines:
        fl = _parse_line(line)
        if fl.is_directive:
            return False
        stripped = line.strip()
        if stripped.startswith('!') or stripped.startswith('#'):
            if '! ' not in stripped and '# ' not in stripped:
                if len(stripped) > 1 and stripped[1] not in (' ', '!', '#'):
                    return False
    return True


def format_document(text: str, indent_str: str = "  ", minimal_edits: bool = True) -> List[TextEdit]:
    """Format a CP2K input document.

    Args:
        text: The input document text.
        indent_str: Indentation string (default: two spaces).
        minimal_edits: If True, return minimal diff-based edits. If False, return full replacement.

    Returns:
        List of TextEdits. Empty list if formatting is unsafe or no changes needed.
    """
    if not _is_formatting_safe(text):
        return []

    if text == "":
        return [
            TextEdit(
                range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                new_text="",
            )
        ]

    lines = text.split('\n')
    formatted_lines = _format_lines(lines, indent_str)

    if text.endswith('\n') and formatted_lines and not formatted_lines[-1] == '':
        pass

    new_text = '\n'.join(formatted_lines)
    if text.endswith('\n') and not new_text.endswith('\n'):
        new_text += '\n'

    if new_text == text:
        return []

    return [TextEdit(
        range=Range(start=Position(line=0, character=0), end=Position(line=len(lines), character=0)),
        new_text=new_text,
    )]


def format_range(text: str, start_line: int, end_line: int, indent_str: str = "  ") -> List[TextEdit]:
    """Format a range of lines in a CP2K input document."""
    lines = text.split('\n')
    range_lines = lines[start_line:end_line]
    range_text = '\n'.join(range_lines)

    formatted = format_document(range_text, indent_str)
    if not formatted:
        return []

    return [TextEdit(
        range=Range(start=Position(line=start_line, character=0), end=Position(line=end_line, character=0)),
        new_text=formatted[0].new_text,
    )]
