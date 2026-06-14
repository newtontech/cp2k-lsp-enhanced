"""Document symbols provider for CP2K language server.

Provides document symbols with proper ranges using AST positions,
supporting nested sections, keywords, and comment disambiguation.
"""

import re
from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_lsp.parser.ast import Comment, CP2KInput, Keyword, Section

# Preprocessor directive patterns
_INCLUDE_PATTERN = re.compile(r'@INCLUDE\s+["\']([^"\']+)["\']', re.IGNORECASE)
_SET_PATTERN = re.compile(r'@SET\s+(\w+)', re.IGNORECASE)


def provide_document_symbols(ast: CP2KInput, lines: Optional[List[str]] = None) -> List[lsp.DocumentSymbol]:
    """Extract document symbols from CP2K AST.
    
    Args:
        ast: The parsed CP2K input AST
        lines: Optional source lines for @INCLUDE/@SET detection
        
    Returns:
        List of document symbols with hierarchical structure
    """
    symbols = []
    
    if ast is None:
        return symbols
    
    # Process global section if present
    if ast.global_section is not None:
        symbol = _process_section(ast.global_section)
        if symbol:
            symbols.append(symbol)
    
    # Process top-level sections
    for section in ast.sections:
        symbol = _process_section(section)
        if symbol:
            symbols.append(symbol)
    
    # Process @INCLUDE/@SET directives from comments
    if lines is not None:
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('#'):
                continue
            
            # Check for @INCLUDE
            match = _INCLUDE_PATTERN.search(line_stripped)
            if match:
                symbol = _make_preprocessor_symbol("@INCLUDE", match.group(1), i, line_stripped)
                if symbol:
                    symbols.append(symbol)
                    continue
            
            # Check for @SET
            match = _SET_PATTERN.search(line_stripped)
            if match:
                symbol = _make_preprocessor_symbol("@SET", match.group(1), i, line_stripped)
                if symbol:
                    symbols.append(symbol)
    
    return symbols


def _make_preprocessor_symbol(directive: str, value: str, line_idx: int, line_text: str) -> Optional[lsp.DocumentSymbol]:
    """Create a document symbol for a preprocessor directive.
    
    Args:
        directive: The directive type (@INCLUDE or @SET)
        value: The directive value (filename or variable name)
        line_idx: 0-based line index
        line_text: The full line text
        
    Returns:
        DocumentSymbol or None
    """
    kind = lsp.SymbolKind.Event
    name = f"{directive} {value}"
    
    range_start = lsp.Position(line=line_idx, character=0)
    range_end = lsp.Position(line=line_idx, character=len(line_text))
    
    selection_range = lsp.Range(
        start=range_start,
        end=lsp.Position(line=line_idx, character=len(directive))
    )
    
    return lsp.DocumentSymbol(
        name=name,
        detail="Preprocessor directive",
        kind=kind,
        range=lsp.Range(start=range_start, end=range_end),
        selection_range=selection_range
    )


def _process_section(section: Section) -> Optional[lsp.DocumentSymbol]:
    """Process a section into a document symbol.
    
    Args:
        section: The section to process
        
    Returns:
        DocumentSymbol for the section
    """
    # Determine symbol kind based on section name
    kind = lsp.SymbolKind.Namespace
    name = section.name
    
    # Special handling for common sections
    name_upper = name.upper()
    if name_upper in ('FORCE_EVAL', 'SUBSYS', 'CELL', 'COORD', 'KIND'):
        kind = lsp.SymbolKind.Struct
    elif name_upper in ('DFT', 'QS', 'SCF', 'MGRID'):
        kind = lsp.SymbolKind.Class
    elif name_upper in ('GLOBAL', 'OUTPUT'):
        kind = lsp.SymbolKind.Module
    
    # Get range from section node (line is 1-based, LSP is 0-based)
    range_start = lsp.Position(
        line=section.line - 1 if section.line else 0,
        character=section.column if section.column else 0
    )
    
    # Estimate end range based on last child
    range_end = _estimate_section_end(section, range_start.line)
    
    # Create selection range (just the name)
    selection_range = lsp.Range(
        start=range_start,
        end=lsp.Position(
            line=range_start.line,
            character=range_start.character + len(name) + 1  # +1 for &
        )
    )
    
    # Process keywords
    children: List[lsp.DocumentSymbol] = []
    for keyword in section.keywords:
        child_symbol = _process_keyword(keyword)
        if child_symbol:
            children.append(child_symbol)
    
    # Process subsections
    for subsection in section.subsections:
        child_symbol = _process_section(subsection)
        if child_symbol:
            children.append(child_symbol)
    
    # Process comments
    for comment in section.comments:
        child_symbol = _process_comment(comment)
        if child_symbol:
            children.append(child_symbol)
    
    return lsp.DocumentSymbol(
        name=name,
        detail=f"&{name}",
        kind=kind,
        range=lsp.Range(start=range_start, end=range_end),
        selection_range=selection_range,
        children=children if children else None
    )


def _estimate_section_end(section: Section, start_line: int) -> lsp.Position:
    """Estimate the end position of a section based on its contents.
    
    Args:
        section: The section
        start_line: The 0-based start line
        
    Returns:
        Estimated end position
    """
    max_line = start_line
    
    # Check keywords
    for keyword in section.keywords:
        if keyword.line:
            max_line = max(max_line, keyword.line - 1)
            # Add a few lines for the value if multi-line
            if keyword.value and isinstance(keyword.value.value, list):
                max_line += len(keyword.value.value) - 1
    
    # Check subsections
    for subsection in section.subsections:
        if subsection.line:
            subsection_end = _estimate_section_end(subsection, subsection.line - 1)
            max_line = max(max_line, subsection_end.line)
    
    # Check comments
    for comment in section.comments:
        if comment.line:
            max_line = max(max_line, comment.line - 1)
    
    # Add a buffer for the &END statement
    max_line += 2
    
    return lsp.Position(line=max_line, character=0)


def _process_keyword(keyword: Keyword) -> Optional[lsp.DocumentSymbol]:
    """Process a keyword into a document symbol.
    
    Args:
        keyword: The keyword to process
        
    Returns:
        DocumentSymbol for the keyword
    """
    kind = lsp.SymbolKind.Property
    name = keyword.name
    
    # Get range from keyword node
    range_start = lsp.Position(
        line=keyword.line - 1 if keyword.line else 0,
        character=keyword.column if keyword.column else 0
    )
    
    # Estimate end based on name length and value
    name_len = len(name)
    if keyword.value and keyword.value.value is not None:
        if isinstance(keyword.value.value, list):
            value_str = " ".join(str(v) for v in keyword.value.value)
        else:
            value_str = str(keyword.value.value)
        name_len += 3 + len(value_str)  # " = " + value
    
    range_end = lsp.Position(
        line=range_start.line,
        character=range_start.character + name_len
    )
    
    # Selection range (just the keyword name)
    selection_range = lsp.Range(
        start=range_start,
        end=lsp.Position(
            line=range_start.line,
            character=range_start.character + len(name)
        )
    )
    
    # Build detail string
    detail = name
    if keyword.value and keyword.value.value is not None:
        if isinstance(keyword.value.value, list):
            detail += f" = [{' '.join(str(v) for v in keyword.value.value)}]"
        else:
            detail += f" = {keyword.value.value}"
    
    return lsp.DocumentSymbol(
        name=name,
        detail=detail,
        kind=kind,
        range=lsp.Range(start=range_start, end=range_end),
        selection_range=selection_range
    )


def _process_comment(comment: Comment) -> Optional[lsp.DocumentSymbol]:
    """Process a comment into a document symbol.
    
    Args:
        comment: The comment to process
        
    Returns:
        DocumentSymbol for the comment
    """
    kind = lsp.SymbolKind.String
    text = comment.text.strip()
    name = text[:50] + "..." if len(text) > 50 else text
    
    range_start = lsp.Position(
        line=comment.line - 1 if comment.line else 0,
        character=comment.column if comment.column else 0
    )
    range_end = lsp.Position(
        line=range_start.line,
        character=range_start.character + len(comment.text)
    )
    
    selection_range = lsp.Range(
        start=range_start,
        end=range_end
    )
    
    return lsp.DocumentSymbol(
        name=name,
        detail="Comment",
        kind=kind,
        range=lsp.Range(start=range_start, end=range_end),
        selection_range=selection_range
    )


def provide_folding_ranges(ast: CP2KInput) -> List[lsp.FoldingRange]:
    """Extract folding ranges from CP2K AST.
    
    Supports folding for:
    - &SECTION / &END SECTION blocks
    
    Args:
        ast: The parsed CP2K input AST
        
    Returns:
        List of folding ranges
    """
    ranges: List[lsp.FoldingRange] = []
    
    if ast is None:
        return ranges
    
    # Process global section
    if ast.global_section is not None:
        _collect_section_folding_ranges(ast.global_section, ranges)
    
    # Process top-level sections
    for section in ast.sections:
        _collect_section_folding_ranges(section, ranges)
    
    return ranges


def _collect_section_folding_ranges(section: Section, ranges: List[lsp.FoldingRange]) -> None:
    """Recursively collect folding ranges from sections.
    
    Args:
        section: The current section
        ranges: List to append folding ranges to
    """
    start_line = section.line - 1 if section.line else 0
    
    if hasattr(section, 'end_line') and section.end_line:
        end_line = section.end_line - 1
    else:
        end_line = _estimate_section_end(section, start_line).line - 1
    
    # Only add if we have a multi-line section
    if end_line > start_line:
        ranges.append(lsp.FoldingRange(
            start_line=start_line,
            end_line=end_line,
            kind=lsp.FoldingRangeKind.Region,
            collapsed_text=f"&{section.name}..."
        ))
    
    # Process subsections recursively
    for subsection in section.subsections:
        _collect_section_folding_ranges(subsection, ranges)
