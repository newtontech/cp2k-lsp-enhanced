"""Goto definition provider for CP2K language server.

Supports goto-definition for:
- @INCLUDE file paths
- BASIS_SET_FILE_NAME values
- POTENTIAL_FILE_NAME values
- BASIS_SET/POTENTIAL values to datafile entries
"""

import os
import re
from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.workspace_index import FileReference, WorkspaceResourceIndex
from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section

# Preprocessor directive patterns
_INCLUDE_PATTERN = re.compile(r'@INCLUDE\s+["\']([^"\']+)["\']', re.IGNORECASE)
_SET_PATTERN = re.compile(r'@SET\s+(\w+)', re.IGNORECASE)
_VAR_PATTERN = re.compile(r'\$\{(\w+)\}', re.IGNORECASE)


def provide_definition(
    ast: CP2KInput,
    position: lsp.Position,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    lines: Optional[List[str]] = None
) -> Optional[lsp.Location]:
    """Provide goto-definition for the given position.
    
    Args:
        ast: The parsed CP2K input AST
        position: The cursor position
        doc_uri: The document URI
        workspace_index: The workspace resource index
        lines: Optional source lines for @INCLUDE detection
        
    Returns:
        Location if definition found, None otherwise
    """
    if ast is None:
        return None
    
    line_idx = position.line
    character = position.character
    
    # Check for @INCLUDE directive in the source line
    if lines and 0 <= line_idx < len(lines):
        line_text = lines[line_idx]
        include_match = _INCLUDE_PATTERN.search(line_text)
        if include_match and character >= include_match.start() and character <= include_match.end():
            include_path = include_match.group(1)
            return _resolve_include(include_path, doc_uri, workspace_index)
        
        # Check for @SET directive
        set_match = _SET_PATTERN.search(line_text)
        if set_match and character >= set_match.start() and character <= set_match.end():
            # @SET is a definition, not a reference
            return None
    
    # Check for ${VAR} references anywhere on the current line
    if lines and 0 <= line_idx < len(lines):
        for var_match in _VAR_PATTERN.finditer(lines[line_idx]):
            if var_match.start() <= character <= var_match.end():
                var_name = var_match.group(1)
                return _handle_variable_reference(var_name, ast, doc_uri, lines)

    # Find keyword at position
    keyword = _find_keyword_at_position(ast, line_idx, character)

    if keyword:
        return _handle_keyword_definition(keyword, ast, doc_uri, workspace_index, lines)

    return None


def _find_keyword_at_position(ast: CP2KInput, line_idx: int, character: int) -> Optional[Keyword]:
    """Find the keyword at the given position.
    
    Args:
        ast: The parsed AST
        line_idx: 0-based line index
        character: Character position
        
    Returns:
        Keyword if found, None otherwise
    """
    # Check global section
    if ast.global_section:
        result = _search_keyword_in_section(ast.global_section, line_idx, character)
        if result:
            return result
    
    # Check top-level sections
    for section in ast.sections:
        result = _search_keyword_in_section(section, line_idx, character)
        if result:
            return result
    
    return None


def _search_keyword_in_section(section: Section, line_idx: int, character: int) -> Optional[Keyword]:
    """Search for a keyword in a section.
    
    Args:
        section: The section to search
        line_idx: 0-based line index
        character: Character position
        
    Returns:
        Keyword if found, None otherwise
    """
    # Check keywords in this section
    for keyword in section.keywords:
        if keyword.line and keyword.line - 1 == line_idx:
            # Check if character is within the keyword name
            if keyword.column and keyword.column <= character < keyword.column + len(keyword.name):
                return keyword
    
    # Recurse into subsections
    for subsection in section.subsections:
        result = _search_keyword_in_section(subsection, line_idx, character)
        if result:
            return result
    
    return None


def _handle_keyword_definition(
    keyword: Keyword,
    ast: CP2KInput,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    lines: Optional[List[str]] = None
) -> Optional[lsp.Location]:
    """Handle goto-definition for keywords.

    Args:
        keyword: The keyword node
        ast: The parsed AST
        doc_uri: The document URI
        workspace_index: The workspace resource index
        lines: Optional source lines for @SET variable lookup

    Returns:
        Location if definition found, None otherwise
    """
    name_upper = keyword.name.upper()

    # Handle BASIS_SET_FILE_NAME and POTENTIAL_FILE_NAME
    if name_upper in ('BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'COORD_FILE_NAME'):
        return _handle_datafile_reference(keyword, doc_uri, workspace_index)

    # Handle BASIS_SET and POTENTIAL values (goto entry in datafile)
    if name_upper in ('BASIS_SET', 'POTENTIAL'):
        return _handle_datafile_entry_reference(keyword, ast, doc_uri, workspace_index)

    # Handle ${VAR} references (goto @SET definition) in keyword values
    if keyword.value and keyword.value.value is not None:
        value_str = str(keyword.value.value)
        var_match = _VAR_PATTERN.search(value_str)
        if var_match and lines is not None:
            var_name = var_match.group(1)
            return _handle_variable_reference(var_name, ast, doc_uri, lines)

    return None


def _resolve_include(
    include_path: str,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> Optional[lsp.Location]:
    """Resolve an @INCLUDE path to a file location.
    
    Args:
        include_path: The path from the @INCLUDE directive
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        Location if file found, None otherwise
    """
    from cp2k_input_tools.workspace_index import FileReference
    
    # Create a temporary FileReference for resolution
    ref = FileReference(
        uri=doc_uri,
        line=0,
        column=0,
        ref_type='INCLUDE',
        value=include_path
    )
    
    resolved_path = workspace_index.resolve_file_path(ref, doc_uri)
    
    if resolved_path and os.path.exists(resolved_path):
        return lsp.Location(
            uri=f"file://{resolved_path}",
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=0)
            )
        )
    
    return None


def _handle_datafile_reference(
    keyword: Keyword,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> Optional[lsp.Location]:
    """Handle goto-definition for datafile name keywords.
    
    Args:
        keyword: The keyword (BASIS_SET_FILE_NAME, etc.)
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        Location pointing to the datafile
    """
    if not keyword.value or keyword.value.value is None:
        return None
    
    filename = str(keyword.value.value).strip().strip('"').strip("'")
    
    if not filename:
        return None
    
    # Try to resolve the file path
    from cp2k_input_tools.workspace_index import FileReference
    ref_type = keyword.name.upper().replace('_FILE_NAME', '_FILE')
    ref = FileReference(
        uri=doc_uri,
        line=keyword.line - 1 if keyword.line else 0,
        column=keyword.column if keyword.column else 0,
        ref_type=ref_type,
        value=filename
    )
    
    resolved_path = workspace_index.resolve_file_path(ref, doc_uri)
    
    if resolved_path and os.path.exists(resolved_path):
        return lsp.Location(
            uri=f"file://{resolved_path}",
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=0, character=0)
            )
        )
    
    return None


def _handle_datafile_entry_reference(
    keyword: Keyword,
    ast: CP2KInput,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> Optional[lsp.Location]:
    """Handle goto-definition for BASIS_SET/POTENTIAL values (goto entry in datafile).
    
    Args:
        keyword: The keyword (BASIS_SET or POTENTIAL)
        ast: The parsed AST
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        Location pointing to the entry in the datafile
    """
    if not keyword.value or keyword.value.value is None:
        return None
    
    entry_name = str(keyword.value.value).strip().strip('"').strip("'")
    
    if not entry_name:
        return None
    
    # Find the KIND section to get the element name
    element_name = _find_kind_element(keyword, ast)
    
    if not element_name:
        return None
    
    # Find the data file reference
    datafile_ref = _find_datafile_reference(keyword.name, ast, doc_uri)
    
    if datafile_ref:
        resolved_path = workspace_index.resolve_file_path(datafile_ref, doc_uri)
        
        if resolved_path and os.path.exists(resolved_path):
            # Parse the data file and find the entry
            from cp2k_input_tools.datafile_parser import parse_basis_file, parse_potential_file
            
            if 'BASIS' in keyword.name.upper():
                data_file = parse_basis_file(resolved_path)
            else:
                data_file = parse_potential_file(resolved_path)
            
            if data_file:
                entry = data_file.find_entry(element_name, entry_name)
                if entry:
                    return lsp.Location(
                        uri=f"file://{resolved_path}",
                        range=lsp.Range(
                            start=lsp.Position(line=entry.start_line, character=0),
                            end=lsp.Position(line=entry.end_line, character=0)
                        )
                    )
    
    return None


def _find_kind_element(keyword: Keyword, ast: CP2KInput) -> Optional[str]:
    """Find the element name for the KIND section containing the keyword.
    
    Args:
        keyword: The keyword node
        ast: The parsed AST
        
    Returns:
        Element name if found, None otherwise
    """
    # Find the enclosing KIND section by looking at section structure
    # In CP2K, BASIS_SET/POTENTIAL are inside &KIND sections
    # The KIND name is the element name
    
    def search_section(section: Section) -> Optional[str]:
        for subsection in section.subsections:
            if subsection.name.upper() == 'KIND':
                # Check if our keyword is inside this KIND section
                if _is_keyword_in_section(keyword, subsection):
                    # Extract element name from section parameter or name
                    # KIND He or &KIND He
                    return subsection.parameter if subsection.parameter else subsection.name
            result = search_section(subsection)
            if result:
                return result
        return None
    
    # Search in global section
    if ast.global_section:
        result = search_section(ast.global_section)
        if result:
            return result
    
    # Search in top-level sections
    for section in ast.sections:
        result = search_section(section)
        if result:
            return result
    
    return None


def _is_keyword_in_section(keyword: Keyword, section: Section) -> bool:
    """Check if a keyword is inside a section."""
    if keyword.line and section.line:
        # Simple heuristic: keyword line > section line
        # A more robust approach would track end lines
        return keyword.line > section.line
    return False


def _find_datafile_reference(
    keyword_name: str,
    ast: CP2KInput,
    doc_uri: str
) -> Optional[FileReference]:
    """Find the datafile reference for a BASIS_SET or POTENTIAL keyword.
    
    Args:
        keyword_name: The keyword name (BASIS_SET or POTENTIAL)
        ast: The parsed AST
        doc_uri: The document URI
        
    Returns:
        FileReference if found, None otherwise
    """
    from cp2k_input_tools.workspace_index import FileReference
    
    # Determine which file name keyword to look for
    if 'BASIS' in keyword_name.upper():
        target_keyword = 'BASIS_SET_FILE_NAME'
    else:
        target_keyword = 'POTENTIAL_FILE_NAME'
    
    # Search through the AST for the file name keyword
    def search_section(section: Section):
        for kw in section.keywords:
            if kw.name.upper() == target_keyword:
                return kw
        for subsection in section.subsections:
            result = search_section(subsection)
            if result:
                return result
        return None
    
    # Search in global section
    if ast.global_section:
        result = search_section(ast.global_section)
        if result:
            return FileReference(
                uri=doc_uri,
                line=result.line - 1 if result.line else 0,
                column=result.column if result.column else 0,
                ref_type=target_keyword,
                value=str(result.value.value) if result.value and result.value.value else ""
            )
    
    # Search in top-level sections
    for section in ast.sections:
        result = search_section(section)
        if result:
            return FileReference(
                uri=doc_uri,
                line=result.line - 1 if result.line else 0,
                column=result.column if result.column else 0,
                ref_type=target_keyword,
                value=str(result.value.value) if result.value and result.value.value else ""
            )
    
    return None


def _handle_variable_reference(
    var_name: str,
    ast: CP2KInput,
    doc_uri: str,
    lines: Optional[List[str]] = None
) -> Optional[lsp.Location]:
    """Handle goto-definition for ${VAR} references.

    Resolves the variable to its nearest preceding ``@SET VAR`` definition.
    When source lines are unavailable, returns ``None``.

    Args:
        var_name: The variable name
        ast: The parsed AST
        doc_uri: The document URI
        lines: Optional source lines (used to locate ``@SET`` and the call site)

    Returns:
        Location pointing to the @SET definition, or None if not found
    """
    if lines is None:
        return None

    var_upper = var_name.upper()
    target_line = None
    # Find the @SET definition by scanning source lines
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            continue
        set_match = _SET_PATTERN.search(line_stripped)
        if set_match and set_match.group(1).upper() == var_upper:
            # Record this as a candidate; later definitions win
            target_line = i
            target_col = line.upper().find('@SET')

    if target_line is None:
        return None

    return lsp.Location(
        uri=doc_uri,
        range=lsp.Range(
            start=lsp.Position(line=target_line, character=max(target_col, 0)),
            end=lsp.Position(line=target_line, character=max(target_col, 0) + len(f"@SET {var_name}")),
        ),
    )


def provide_references(
    ast: CP2KInput,
    position: lsp.Position,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    include_declaration: bool = True,
    lines: Optional[List[str]] = None
) -> List[lsp.Location]:
    """Find all references to the symbol at the given position.
    
    Args:
        ast: The parsed CP2K input AST
        position: The cursor position
        doc_uri: The document URI
        workspace_index: The workspace resource index
        include_declaration: Whether to include the declaration
        lines: Optional source lines for variable detection
        
    Returns:
        List of locations where the symbol is referenced
    """
    if ast is None:
        return []
    
    references: List[lsp.Location] = []
    line_idx = position.line
    character = position.character
    
    # Check for @SET directive definition
    if lines and 0 <= line_idx < len(lines):
        line_text = lines[line_idx]
        set_match = _SET_PATTERN.search(line_text)
        if set_match and character >= set_match.start() and character <= set_match.end():
            var_name = set_match.group(1)
            references.extend(_find_variable_references(var_name, ast, doc_uri, lines))
            return references
    
    # Find keyword at position
    keyword = _find_keyword_at_position(ast, line_idx, character)
    
    if keyword:
        name_upper = keyword.name.upper()
        
        # Find references to BASIS_SET_FILE_NAME or POTENTIAL_FILE_NAME
        if name_upper in ('BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'COORD_FILE_NAME'):
            references.extend(_find_keyword_references(ast, name_upper, doc_uri))
        
        # Find references to BASIS_SET or POTENTIAL values
        elif name_upper in ('BASIS_SET', 'POTENTIAL'):
            if keyword.value and keyword.value.value:
                entry_name = str(keyword.value.value)
                references.extend(_find_entry_references(ast, name_upper, entry_name, doc_uri))
    
    return references


def _find_variable_references(
    var_name: str,
    ast: CP2KInput,
    doc_uri: str,
    lines: List[str]
) -> List[lsp.Location]:
    """Find all references to a variable (${VAR}).
    
    Args:
        var_name: The variable name
        ast: The parsed AST
        doc_uri: The document URI
        lines: Source lines to search
        
    Returns:
        List of locations where the variable is referenced
    """
    references = []
    var_pattern = re.compile(r'\$\{' + re.escape(var_name) + r'\}', re.IGNORECASE)
    
    for i, line in enumerate(lines):
        for match in var_pattern.finditer(line):
            references.append(lsp.Location(
                uri=doc_uri,
                range=lsp.Range(
                    start=lsp.Position(line=i, character=match.start()),
                    end=lsp.Position(line=i, character=match.end())
                )
            ))
    
    return references


def _find_keyword_references(ast: CP2KInput, keyword_name: str, doc_uri: str) -> List[lsp.Location]:
    """Find all references to a keyword like BASIS_SET_FILE_NAME.
    
    Args:
        ast: The parsed AST
        keyword_name: The keyword name
        doc_uri: The document URI
        
    Returns:
        List of locations where the keyword is used
    """
    references = []
    
    def search_section(section: Section):
        for keyword in section.keywords:
            if keyword.name.upper() == keyword_name:
                references.append(lsp.Location(
                    uri=doc_uri,
                    range=lsp.Range(
                        start=lsp.Position(
                            line=keyword.line - 1 if keyword.line else 0,
                            character=keyword.column if keyword.column else 0
                        ),
                        end=lsp.Position(
                            line=keyword.line - 1 if keyword.line else 0,
                            character=(keyword.column if keyword.column else 0) + len(keyword.name)
                        )
                    )
                ))
        for subsection in section.subsections:
            search_section(subsection)
    
    if ast.global_section:
        search_section(ast.global_section)
    
    for section in ast.sections:
        search_section(section)
    
    return references


def _find_entry_references(ast: CP2KInput, keyword_name: str, entry_name: str, doc_uri: str) -> List[lsp.Location]:
    """Find all references to a BASIS_SET or POTENTIAL entry value.
    
    Args:
        ast: The parsed AST
        keyword_name: The keyword name (BASIS_SET or POTENTIAL)
        entry_name: The entry value to find
        doc_uri: The document URI
        
    Returns:
        List of locations where the entry is referenced
    """
    references = []
    entry_lower = entry_name.strip().lower()
    
    def search_section(section: Section):
        for keyword in section.keywords:
            if keyword.name.upper() == keyword_name and keyword.value and keyword.value.value:
                child_entry = str(keyword.value.value).strip().lower()
                if child_entry == entry_lower:
                    references.append(lsp.Location(
                        uri=doc_uri,
                        range=lsp.Range(
                            start=lsp.Position(
                                line=keyword.line - 1 if keyword.line else 0,
                                character=keyword.column if keyword.column else 0
                            ),
                            end=lsp.Position(
                                line=keyword.line - 1 if keyword.line else 0,
                                character=(keyword.column if keyword.column else 0) + len(keyword.name) + len(child_entry) + 5
                            )
                        )
                    ))
        for subsection in section.subsections:
            search_section(subsection)
    
    if ast.global_section:
        search_section(ast.global_section)
    
    for section in ast.sections:
        search_section(section)
    
    return references
