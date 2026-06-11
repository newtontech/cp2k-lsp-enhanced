"""Cursor context resolution for CP2K input files."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class CursorContext:
    """Rich cursor context for CP2K LSP requests."""
    
    uri: str
    line: int
    character: int
    section_path: Tuple[str, ...]
    current_section: Optional[str]
    current_keyword: Optional[str]
    is_section_start: bool
    is_section_end: bool
    is_keyword_position: bool
    is_value_position: bool
    prefix: str


class CursorContextResolver:
    """Resolve cursor context from CP2K input text."""
    
    # Regular expressions for parsing
    _SECTION_START = re.compile(r'&\s*([\w\-_]+)?')
    _SECTION_END = re.compile(r'&\s*END\s*(?:\s+([\w\-_]+))?', re.IGNORECASE)
    _KEYWORD = re.compile(r'([\w\-_]+)\s*(?:=|\s)')
    _COMMENT_START = re.compile(r'[!#]')
    
    def resolve_cursor_context(
        self,
        uri: str,
        lines: List[str],
        line: int,
        character: int
    ) -> CursorContext:
        """
        Resolve cursor context for a given position.
        
        Args:
            uri: Document URI
            lines: List of document lines
            line: 0-based line number
            character: 0-based character position
            
        Returns:
            CursorContext with resolved information
        """
        # Validate position
        if line < 0 or line >= len(lines):
            return self._create_empty_context(uri, line, character)
        
        current_line = lines[line]
        if character < 0 or character > len(current_line):
            return self._create_empty_context(uri, line, character)
        
        # Get the text up to the cursor position
        line_before = current_line[:character]
        # Get text including one character after cursor for context
        line_with_context = current_line[:character + 1] if character < len(current_line) else line_before
        # Get the full current line for context when line_before is empty
        current_line_without_comment = self._strip_comment(current_line)

        # Initialize section stack
        section_stack: List[str] = []

        # Check if cursor is at a section start on current line
        is_at_section_start = self._SECTION_START.search(line_with_context) is not None

        # Scan lines up to cursor position
        for i in range(min(line + 1, len(lines))):
            scan_line = lines[i]

            # If we're on the cursor line, only scan up to cursor
            if i == line:
                scan_line = line_before

            # Process the line (but don't add section if we're at its start)
            if not (i == line and is_at_section_start):
                self._scan_line_for_sections(scan_line, section_stack)

        # Determine context from current line
        context_info = self._analyze_current_position(line_before, line_with_context, current_line_without_comment, section_stack)
        
        return CursorContext(
            uri=uri,
            line=line,
            character=character,
            section_path=tuple(section_stack),
            current_section=section_stack[-1] if section_stack else None,
            current_keyword=context_info['keyword'],
            is_section_start=context_info['is_section_start'],
            is_section_end=context_info['is_section_end'],
            is_keyword_position=context_info['is_keyword_position'],
            is_value_position=context_info['is_value_position'],
            prefix=context_info['prefix']
        )
    
    def _create_empty_context(self, uri: str, line: int, character: int) -> CursorContext:
        """Create empty context for invalid positions."""
        return CursorContext(
            uri=uri,
            line=line,
            character=character,
            section_path=(),
            current_section=None,
            current_keyword=None,
            is_section_start=False,
            is_section_end=False,
            is_keyword_position=False,
            is_value_position=False,
            prefix=""
        )
    
    def _scan_line_for_sections(self, line: str, section_stack: List[str]) -> None:
        """Scan a line and update section stack."""
        # Remove comments
        line_without_comment = self._strip_comment(line)

        # Check for section ends FIRST (before checking for section starts)
        end_match = self._SECTION_END.search(line_without_comment)
        if end_match:
            if section_stack:
                section_stack.pop()
            return

        # Check for section starts (but not &END)
        section_match = self._SECTION_START.search(line_without_comment)
        if section_match:
            # Don't treat &END as a section start
            line_stripped = line_without_comment.strip().upper()
            if line_stripped.startswith('&END'):
                return

            section_name = section_match.group(1)
            if section_name:  # Only add if we have a section name
                section_stack.append(section_name.upper())
            return
    
    def _analyze_current_position(self, line_before: str, line_with_context: str, current_line: str, section_stack: List[str]) -> dict:
        """Analyze the current cursor position."""
        # Remove comments for analysis
        line_without_comment = self._strip_comment(line_before)

        # Initialize defaults
        context = {
            'keyword': None,
            'is_section_start': False,
            'is_section_end': False,
            'is_keyword_position': False,
            'is_value_position': False,
            'prefix': ''
        }

        # Check for section end first (even incomplete)
        end_match = self._SECTION_END.search(line_with_context)
        # Check if the current line starts with &END (even if we haven't typed it all yet)
        current_line_stripped = current_line.strip().upper()
        if end_match or (current_line_stripped.startswith('&END') and '&' in line_with_context):
            context['is_section_end'] = True
            context['prefix'] = '&END'
            return context

        # Check for section start (even incomplete)
        section_match = self._SECTION_START.search(line_with_context)
        # Special case: if line_before is empty but current line starts with &, treat as section start
        # But NOT if it's an &END line
        is_section_start_condition = (
            not line_before
            and current_line
            and current_line[0] == '&'
            and not current_line_stripped.startswith('&END')
        )
        if section_match or is_section_start_condition:
            context['is_section_start'] = True
            context['prefix'] = '&'
            return context

        # Check for keyword/value position
        # Split the line into tokens
        tokens = self._tokenize_line(line_without_comment)

        if not tokens:
            # Empty line - could be keyword position
            if section_stack:
                context['is_keyword_position'] = True
            return context

        # Check if cursor is after a keyword (value position)
        if tokens:
            # Check if it looks like a keyword assignment
            keyword_match = self._KEYWORD.search(line_with_context)
            if keyword_match:
                keyword_name = keyword_match.group(1).upper()
                context['keyword'] = keyword_name

                # Check if we're at a value position
                # (after keyword and separator)
                match_end = keyword_match.end()
                if match_end <= len(line_with_context):
                    # We're at or past the separator
                    context['is_value_position'] = True

                    # Extract prefix (current partial value)
                    # Get text after the keyword and separator
                    remaining_text = line_with_context[match_end:].strip()
                    context['prefix'] = remaining_text

                return context

            # Check if we're typing a keyword (incomplete, no separator yet)
            # Look for a word token that might be a keyword being typed
            if tokens and len(tokens) == 1:
                # Single token without separator - likely typing a keyword
                potential_keyword = tokens[0].strip()
                if potential_keyword and not potential_keyword.startswith('&'):
                    context['is_keyword_position'] = True
                    context['prefix'] = potential_keyword
                    return context

        # If we have tokens but no keyword matched, might be keyword position
        if section_stack:
            context['is_keyword_position'] = True
            context['prefix'] = line_without_comment.strip()

        return context
    
    def _strip_comment(self, line: str) -> str:
        """Remove comments from a line."""
        comment_match = self._COMMENT_START.search(line)
        if comment_match:
            return line[:comment_match.start()]
        return line
    
    def _tokenize_line(self, line: str) -> List[str]:
        """Tokenize a line into whitespace-separated tokens."""
        tokens = []
        current_token = []
        in_string = False
        string_char = None
        
        for i, char in enumerate(line):
            if not in_string:
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                    current_token.append(char)
                elif char.isspace():
                    if current_token:
                        tokens.append(''.join(current_token))
                        current_token = []
                else:
                    current_token.append(char)
            else:
                current_token.append(char)
                if char == string_char and (i == 0 or line[i-1] != '\\'):
                    in_string = False
                    string_char = None
        
        if current_token:
            tokens.append(''.join(current_token))
        
        return tokens