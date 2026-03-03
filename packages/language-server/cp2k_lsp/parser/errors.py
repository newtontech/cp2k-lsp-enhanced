"""Parser errors."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParseError:
    """Base parse error."""

    message: str
    line: int
    column: int
    source: Optional[str] = None

    def __str__(self) -> str:
        if self.source:
            return f"{self.message} at {self.source}:{self.line}:{self.column}"
        return f"{self.message} at line {self.line}, column {self.column}"


@dataclass
class SyntaxError(ParseError):
    """Syntax error."""

    expected: Optional[str] = None
    found: Optional[str] = None

    def __str__(self) -> str:
        base = super().__str__()
        if self.expected and self.found:
            return f"{base} (expected {self.expected}, found {self.found})"
        return base
