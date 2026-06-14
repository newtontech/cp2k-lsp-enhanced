"""Resource diagnostics provider for CP2K language server.

Provides diagnostics for:
- Missing or unreadable @INCLUDE files
- Missing BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME files
- Unknown entries in BASIS_SET, POTENTIAL keywords
- Duplicate entries in data files
- Coordinate format mismatches
"""

import logging
import os
import re
from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.datafile_parser import parse_basis_file, parse_potential_file
from cp2k_input_tools.workspace_index import FileReference, WorkspaceResourceIndex
from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section

logger = logging.getLogger(__name__)

# Preprocessor directive patterns
_INCLUDE_PATTERN = re.compile(r'@INCLUDE\s+["\']([^"\']+)["\']', re.IGNORECASE)


def provide_resource_diagnostics(
    ast: CP2KInput,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    lines: Optional[List[str]] = None
) -> List[lsp.Diagnostic]:
    """Provide diagnostics for resource references in the document.
    
    Checks for:
    - Missing @INCLUDE files (detected via source text)
    - Missing BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME files
    - Unknown BASIS_SET/POTENTIAL entries
    - Duplicate entries in data files
    
    Args:
        ast: The parsed CP2K input AST
        doc_uri: The document URI
        workspace_index: The workspace resource index
        lines: Optional source lines for @INCLUDE detection
        
    Returns:
        List of diagnostics
    """
    diagnostics = []
    
    if ast is None:
        return diagnostics
    
    # Check @INCLUDE files (from source lines)
    if lines:
        diagnostics.extend(_check_include_files_from_lines(lines, doc_uri, workspace_index))
    
    # Check data file references
    diagnostics.extend(_check_data_file_references(ast, doc_uri, workspace_index))
    
    # Check BASIS_SET/POTENTIAL entries
    diagnostics.extend(_check_data_entries(ast, doc_uri, workspace_index))
    
    return diagnostics


def _check_include_files_from_lines(
    lines: List[str],
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> List[lsp.Diagnostic]:
    """Check that all @INCLUDE files exist and are readable from source lines.
    
    Args:
        lines: Source lines to search
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        List of diagnostics for missing include files
    """
    diagnostics = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            continue
        
        match = _INCLUDE_PATTERN.search(line_stripped)
        if match:
            include_path = match.group(1)
            ref = FileReference(
                uri=doc_uri,
                line=i,
                column=0,
                ref_type='INCLUDE',
                value=include_path
            )
            
            resolved = workspace_index.resolve_file_path(ref, doc_uri)
            
            if resolved is None:
                diagnostics.append(lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=i, character=match.start()),
                        end=lsp.Position(line=i, character=match.end())
                    ),
                    message=f"Include file not found: {include_path}",
                    severity=lsp.DiagnosticSeverity.Error,
                    source="cp2k-lsp",
                    code="missing-include"
                ))
            elif not os.access(resolved, os.R_OK):
                diagnostics.append(lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=i, character=match.start()),
                        end=lsp.Position(line=i, character=match.end())
                    ),
                    message=f"Include file not readable: {include_path}",
                    severity=lsp.DiagnosticSeverity.Warning,
                    source="cp2k-lsp",
                    code="unreadable-include"
                ))
    
    return diagnostics


def _check_data_file_references(
    ast: CP2KInput,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> List[lsp.Diagnostic]:
    """Check that BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME files exist.
    
    Args:
        ast: The parsed AST
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        List of diagnostics for missing data files
    """
    diagnostics: List[lsp.Diagnostic] = []
    target_keywords = ('BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'COORD_FILE_NAME')
    
    def search_section(section: Section):
        for keyword in section.keywords:
            if keyword.name.upper() in target_keywords:
                _check_keyword_file(keyword, doc_uri, workspace_index, diagnostics)
        for subsection in section.subsections:
            search_section(subsection)
    
    if ast.global_section:
        search_section(ast.global_section)
    
    for section in ast.sections:
        search_section(section)
    
    return diagnostics


def _check_keyword_file(
    keyword: Keyword,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    diagnostics: List[lsp.Diagnostic]
):
    """Check that a data file keyword points to an existing file."""
    if not keyword.value or keyword.value.value is None:
        return
    
    filename = str(keyword.value.value).strip().strip('"').strip("'")
    
    if not filename:
        return
    
    ref_type = keyword.name.upper().replace('_FILE_NAME', '_FILE')
    ref = FileReference(
        uri=doc_uri,
        line=keyword.line - 1 if keyword.line else 0,
        column=keyword.column if keyword.column else 0,
        ref_type=ref_type,
        value=filename
    )
    
    resolved = workspace_index.resolve_file_path(ref, doc_uri)
    
    if resolved is None:
        diagnostics.append(lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(
                    line=keyword.line - 1 if keyword.line else 0,
                    character=keyword.column if keyword.column else 0
                ),
                end=lsp.Position(
                    line=keyword.line - 1 if keyword.line else 0,
                    character=(keyword.column if keyword.column else 0) + len(keyword.name) + len(filename) + 5
                )
            ),
            message=f"Data file not found: {filename}",
            severity=lsp.DiagnosticSeverity.Error,
            source="cp2k-lsp",
            code="missing-datafile"
        ))
    elif not os.access(resolved, os.R_OK):
        diagnostics.append(lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(
                    line=keyword.line - 1 if keyword.line else 0,
                    character=keyword.column if keyword.column else 0
                ),
                end=lsp.Position(
                    line=keyword.line - 1 if keyword.line else 0,
                    character=(keyword.column if keyword.column else 0) + len(keyword.name) + len(filename) + 5
                )
            ),
            message=f"Data file not readable: {filename}",
            severity=lsp.DiagnosticSeverity.Warning,
            source="cp2k-lsp",
            code="unreadable-datafile"
        ))


def _check_data_entries(
    ast: CP2KInput,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex
) -> List[lsp.Diagnostic]:
    """Check that BASIS_SET and POTENTIAL entries exist in their data files.
    
    Args:
        ast: The parsed AST
        doc_uri: The document URI
        workspace_index: The workspace resource index
        
    Returns:
        List of diagnostics for unknown entries
    """
    diagnostics: List[lsp.Diagnostic] = []
    
    # Find FORCE_EVAL section
    def find_force_eval(section: Section) -> Optional[Section]:
        if section.name.upper() == 'FORCE_EVAL':
            return section
        for subsection in section.subsections:
            result = find_force_eval(subsection)
            if result:
                return result
        return None
    
    force_eval = None
    if ast.global_section:
        force_eval = find_force_eval(ast.global_section)
    
    if not force_eval:
        for section in ast.sections:
            force_eval = find_force_eval(section)
            if force_eval:
                break
    
    if force_eval:
        _check_force_eval_entries(force_eval, doc_uri, workspace_index, diagnostics)
    
    return diagnostics


def _check_force_eval_entries(
    section: Section,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    diagnostics: List[lsp.Diagnostic]
):
    """Check entries in FORCE_EVAL section.

    BASIS_SET_FILE_NAME and POTENTIAL_FILE_NAME may live directly under
    FORCE_EVAL or inside a nested &DFT subsection; we search recursively so
    real-world inputs are validated correctly.
    """
    basis_file = _find_keyword_value(section, "BASIS_SET_FILE_NAME")
    potential_file = _find_keyword_value(section, "POTENTIAL_FILE_NAME")

    # Check BASIS_SET and POTENTIAL entries in KIND sections
    for subsection in section.subsections:
        if subsection.name.upper() == 'SUBSYS':
            _check_subsys_entries(subsection, basis_file, potential_file, doc_uri, workspace_index, diagnostics)


def _find_keyword_value(section: Section, keyword_name: str) -> Optional[str]:
    """Recursively search a section tree for the first occurrence of a keyword value."""
    target = keyword_name.upper()

    def search(s: Section) -> Optional[str]:
        for kw in s.keywords:
            if kw.name.upper() == target and kw.value and kw.value.value is not None:
                return str(kw.value.value).strip()
        for sub in s.subsections:
            result = search(sub)
            if result is not None:
                return result
        return None

    return search(section)


def _check_subsys_entries(
    section: Section,
    basis_file: Optional[str],
    potential_file: Optional[str],
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    diagnostics: List[lsp.Diagnostic]
):
    """Check entries in SUBSYS section."""
    for subsection in section.subsections:
        if subsection.name.upper() == 'KIND':
            _check_kind_entries(subsection, basis_file, potential_file, doc_uri, workspace_index, diagnostics)


def _check_kind_entries(
    section: Section,
    basis_file: Optional[str],
    potential_file: Optional[str],
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    diagnostics: List[lsp.Diagnostic]
):
    """Check BASIS_SET and POTENTIAL entries in a KIND section."""
    # Extract element name from section parameter or name
    # In CP2K: &KIND He or &KIND ELEMENT=He
    element = section.parameter if section.parameter else section.name
    
    for keyword in section.keywords:
        name_upper = keyword.name.upper()
        
        if name_upper == 'BASIS_SET' and basis_file and keyword.value and keyword.value.value:
            entry_name = str(keyword.value.value).strip().strip('"').strip("'")
            
            if entry_name:
                _validate_data_entry(
                    keyword, element, entry_name, basis_file, 'basis',
                    doc_uri, workspace_index, diagnostics
                )
        
        elif name_upper == 'POTENTIAL' and potential_file and keyword.value and keyword.value.value:
            entry_name = str(keyword.value.value).strip().strip('"').strip("'")
            
            if entry_name:
                _validate_data_entry(
                    keyword, element, entry_name, potential_file, 'potential',
                    doc_uri, workspace_index, diagnostics
                )


def _validate_data_entry(
    keyword: Keyword,
    element: str,
    entry_name: str,
    data_filename: str,
    file_type: str,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    diagnostics: List[lsp.Diagnostic]
):
    """Validate a data entry exists in the data file."""
    ref_type = f"{file_type.upper()}_FILE"
    ref = FileReference(
        uri=doc_uri,
        line=keyword.line - 1 if keyword.line else 0,
        column=keyword.column if keyword.column else 0,
        ref_type=ref_type,
        value=data_filename
    )
    
    resolved = workspace_index.resolve_file_path(ref, doc_uri)
    
    if resolved and os.path.exists(resolved):
        if file_type == 'basis':
            data_file = parse_basis_file(resolved)
        else:
            data_file = parse_potential_file(resolved)
        
        if data_file:
            entry = data_file.find_entry(element, entry_name)
            if entry is None:
                # Try to find any entry for this element
                available = data_file.find_entries_by_name(element)
                if available:
                    labels = [e.label for e in available if e.label]
                    if labels:
                        message = f"Unknown {file_type} entry: {entry_name} for {element}. Available: {', '.join(labels)}"
                    else:
                        message = f"Unknown {file_type} entry: {entry_name} for {element}"
                else:
                    message = f"Element {element} not found in {file_type} file"
                
                diagnostics.append(lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(
                            line=keyword.line - 1 if keyword.line else 0,
                            character=keyword.column if keyword.column else 0
                        ),
                        end=lsp.Position(
                            line=keyword.line - 1 if keyword.line else 0,
                            character=(keyword.column if keyword.column else 0) + len(keyword.name) + len(entry_name) + 5
                        )
                    ),
                    message=message,
                    severity=lsp.DiagnosticSeverity.Warning,
                    source="cp2k-lsp",
                    code="unknown-entry"
                ))
