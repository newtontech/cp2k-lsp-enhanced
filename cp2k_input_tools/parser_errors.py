"""Parser error classes with enhanced context information."""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ErrorContext:
    """Enhanced context information for parser errors."""
    line: Optional[str] = None
    filename: Optional[str] = None
    linenr: Optional[int] = None
    colnr: Optional[int] = None
    colnrs: List[int] = field(default_factory=list)
    ref_colnr: Optional[int] = None
    ref_line: Optional[str] = None
    section: Any = None
    section_stack: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    def __str__(self):
        parts = []
        if self.filename:
            parts.append(f"in {self.filename}")
        if self.linenr is not None:
            parts.append(f"line {self.linenr}")
        if self.section_stack:
            parts.append(f"section: {'/'.join(self.section_stack)}")
        return " ".join(parts)

    def get_error_marker(self):
        """Generate an error marker for the context."""
        if self.colnr is None:
            return None
        
        marker = " " * self.colnr + "^"
        if self.ref_colnr is not None and self.ref_colnr > self.colnr:
            marker = " " * self.colnr + "~" * (self.ref_colnr - self.colnr) + "^"
        return marker


class ParserError(Exception):
    """Base parser error with context."""
    
    def __init__(self, message, context=None):
        super().__init__(message)
        self.message = message
        self.context = context if context is not None else ErrorContext()

    def __str__(self):
        base_msg = self.message
        if self.context:
            ctx_str = str(self.context)
            if ctx_str:
                base_msg += f"\n  Context: {ctx_str}"
            marker = self.context.get_error_marker()
            if marker and self.context.line:
                base_msg += f"\n    {self.context.line}"
                base_msg += f"\n    {marker}"
        return base_msg


class InvalidNameError(ParserError):
    """Error for invalid section or keyword names."""
    pass


class SectionMismatchError(ParserError):
    """Error for mismatched section open/close."""
    pass


class InvalidSectionError(ParserError):
    """Error for invalid section."""
    pass


class InvalidParameterError(ParserError):
    """Error for invalid parameter values."""
    pass


class NameRepetitionError(ParserError):
    """Error for repeated non-repeatable names."""
    pass


class PreprocessorError(ParserError):
    """Error in preprocessor directives."""
    pass


class DeprecatedKeywordWarning(Warning):
    """Warning for deprecated keywords."""
    
    def __init__(self, keyword_name, message=None, replacement=None):
        self.keyword_name = keyword_name
        self.message = message or f"Keyword '{keyword_name}' is deprecated"
        self.replacement = replacement
        super().__init__(self.message)

    def __str__(self):
        msg = self.message
        if self.replacement:
            msg += f". Use '{self.replacement}' instead."
        return msg


class DeprecatedSectionWarning(Warning):
    """Warning for deprecated sections."""
    
    def __init__(self, section_name, message=None, replacement=None):
        self.section_name = section_name
        self.message = message or f"Section '{section_name}' is deprecated"
        self.replacement = replacement
        super().__init__(self.message)

    def __str__(self):
        msg = self.message
        if self.replacement:
            msg += f". Use '{self.replacement}' instead."
        return msg


class IntegerRangeError(ParserError):
    """Error for invalid integer ranges (X..Y)."""
    pass


class NestedSectionError(ParserError):
    """Error for nested section issues."""
    pass
