"""Semantic token provider for CP2K language.

Provides syntax highlighting tokens for sections, keywords, values,
units, comments, and preprocessor directives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class SemanticToken:
    """Represents a single semantic token."""

    line: int
    start_char: int
    length: int
    token_type: str
    modifiers: List[str]


# Token type constants
TOKEN_SECTION = "section"
TOKEN_KEYWORD = "keyword"
TOKEN_VALUE = "value"
TOKEN_UNIT = "unit"
TOKEN_COMMENT = "comment"
TOKEN_PREPROCESSOR = "preprocessor"
TOKEN_VARIABLE = "variable"
TOKEN_INCLUDE_PATH = "include_path"

# Token modifier constants
MODIFIER_DEFINITION = "definition"
MODIFIER_READ_ONLY = "readonly"


class SemanticTokenProvider:
    """Provides semantic tokens for CP2K input files."""

    # Regex patterns for token classification
    _SECTION_START = re.compile(r"^\s*&(\w+)")
    _SECTION_END = re.compile(r"^\s*&END\s+(\w+)")
    _COMMENT = re.compile(r"^\s*!.*$")
    _PREPROCESSOR = re.compile(r"^\s*(@\w+)")
    _KEYWORD = re.compile(r"^\s*(\w+)\s*=")
    _VALUE = re.compile(r"=\s*(.+)$")
    _UNIT = re.compile(r"\[([a-zA-Z0-9_]+)\]")
    _VARIABLE = re.compile(r"\$\{(\w+)\}")
    _NUMBER = re.compile(r"^-?\d+\.?\d*([eE][+-]?\d+)?")

    def get_semantic_tokens(self, text: str) -> List[SemanticToken]:
        """Parse text and return semantic tokens.

        Args:
            text: The CP2K input text to tokenize

        Returns:
            List of SemanticToken objects
        """
        tokens: List[SemanticToken] = []
        lines = text.split("\n")

        for line_num, line in enumerate(lines):
            self._tokenize_line(line, line_num, tokens)

        return tokens

    def _tokenize_line(
        self, line: str, line_num: int, tokens: List[SemanticToken]
    ) -> None:
        """Tokenize a single line of CP2K input.

        Args:
            line: The line to tokenize
            line_num: The line number (0-indexed)
            tokens: List to append tokens to
        """
        # Check for comment
        if self._COMMENT.match(line):
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=0,
                    length=len(line),
                    token_type=TOKEN_COMMENT,
                    modifiers=[MODIFIER_READ_ONLY],
                )
            )
            return

        # Check for preprocessor directive
        pp_match = self._PREPROCESSOR.match(line)
        if pp_match:
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=pp_match.start(1),
                    length=len(pp_match.group(1)),
                    token_type=TOKEN_PREPROCESSOR,
                    modifiers=[MODIFIER_DEFINITION],
                )
            )
            return

        # Check for section start
        section_match = self._SECTION_START.match(line)
        if section_match:
            name = section_match.group(1)
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=section_match.start(1),
                    length=len(name),
                    token_type=TOKEN_SECTION,
                    modifiers=[MODIFIER_DEFINITION],
                )
            )
            return

        # Check for section end
        end_match = self._SECTION_END.match(line)
        if end_match:
            name = end_match.group(1)
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=end_match.start(1),
                    length=len(name),
                    token_type=TOKEN_SECTION,
                    modifiers=[],
                )
            )
            return

        keyword_match = self._KEYWORD.match(line)
        if keyword_match:
            name = keyword_match.group(1)
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=keyword_match.start(1),
                    length=len(name),
                    token_type=TOKEN_KEYWORD,
                    modifiers=[],
                )
            )

            # Extract and tokenize the value
            value_match = self._VALUE.match(line)
            if value_match:
                value = value_match.group(1).strip()
                value_start = line.find("=", keyword_match.start(1) + len(name))
                self._tokenize_value(value, line_num, value_start + 1, tokens)
            return

        space_match = re.match(r"^\s*(\w+)\s+(\S+.*)$", line)
        if space_match:
            name = space_match.group(1)
            value_str = space_match.group(2).strip()
            if name.isupper() or (len(name) > 2 and value_str and not value_str.startswith("&")):
                tokens.append(
                    SemanticToken(
                        line=line_num,
                        start_char=space_match.start(1),
                        length=len(name),
                        token_type=TOKEN_KEYWORD,
                        modifiers=[],
                    )
                )
                value_start = space_match.start(2)
                self._tokenize_value(value_str, line_num, value_start, tokens)
                return

        # Check for inline values (e.g., in cell specifications)
        value_match = self._VALUE.match(line)
        if value_match:
            value = value_match.group(1).strip()
            value_start = line.find("=") + 1
            self._tokenize_value(value, line_num, value_start, tokens)

    def _tokenize_value(
        self, value: str, line_num: int, start_pos: int, tokens: List[SemanticToken]
    ) -> None:
        """Tokenize a value, checking for units and variables.

        Args:
            value: The value string to tokenize
            line_num: The line number
            start_pos: The starting character position
            tokens: List to append tokens to
        """
        # Check for unit in brackets
        unit_match = self._UNIT.search(value)
        if unit_match:
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=start_pos + unit_match.start(1),
                    length=len(unit_match.group(1)),
                    token_type=TOKEN_UNIT,
                    modifiers=[],
                )
            )

        # Check for variable references
        var_match = self._VARIABLE.search(value)
        if var_match:
            tokens.append(
                SemanticToken(
                    line=line_num,
                    start_char=start_pos + var_match.start(1),
                    length=len(var_match.group(1)),
                    token_type=TOKEN_VARIABLE,
                    modifiers=[],
                )
            )

        # Tokenize the value itself
        tokens.append(
            SemanticToken(
                line=line_num,
                start_char=start_pos,
                length=len(value),
                token_type=TOKEN_VALUE,
                modifiers=[],
            )
        )
