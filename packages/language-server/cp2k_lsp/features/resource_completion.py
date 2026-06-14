"""Resource completion provider for CP2K language server.

Provides completion items for:
- Local filenames for @INCLUDE, BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME
- Datafile entries for BASIS_SET, POTENTIAL keywords
- Variable names for ${VAR} references
"""

import os
import re
from typing import List, Optional

from lsprotocol import types as lsp

from cp2k_input_tools.datafile_parser import parse_basis_file, parse_potential_file
from cp2k_input_tools.workspace_index import FileReference, WorkspaceResourceIndex
from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section

# Patterns
_INCLUDE_PATTERN = re.compile(r'@INCLUDE\s+["\']([^"\']+)["\']', re.IGNORECASE)
_SET_PATTERN = re.compile(r'@SET\s+(\w+)', re.IGNORECASE)
_VAR_PATTERN = re.compile(r'\$\{(\w+)\}', re.IGNORECASE)


def provide_resource_completions(
    ast: CP2KInput,
    position: lsp.Position,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    lines: Optional[List[str]] = None
) -> Optional[lsp.CompletionList]:
    """Provide completion items for resource references.
    
    Args:
        ast: The parsed CP2K input AST
        position: The cursor position
        doc_uri: The document URI
        workspace_index: The workspace resource index
        lines: Optional source lines for context
        
    Returns:
        CompletionList with relevant completions
    """
    if ast is None or lines is None:
        return None
    
    # Get the current line content
    if position.line < 0 or position.line >= len(lines):
        return None
    
    line = lines[position.line]
    line_upper = line.upper()
    
    # Check what type of completion is needed
    completions: List[lsp.CompletionItem] = []
    
    # Check for @INCLUDE
    if '@INCLUDE' in line_upper:
        completions.extend(_get_include_completions(doc_uri, position))
    
    # Check for BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME
    elif any(kw in line_upper for kw in ('BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'COORD_FILE_NAME')):
        completions.extend(_get_datafile_name_completions(doc_uri, position))
    
    # Check for BASIS_SET, POTENTIAL
    elif 'BASIS_SET' in line_upper or 'POTENTIAL' in line_upper:
        completions.extend(_get_datafile_entry_completions(ast, line, doc_uri, workspace_index, position))
    
    # Check for ${VAR}
    elif '${' in line:
        completions.extend(_get_variable_completions(lines, position))
    
    if completions:
        return lsp.CompletionList(
            items=completions,
            is_incomplete=False
        )
    
    return None


def _get_include_completions(
    doc_uri: str,
    position: lsp.Position
) -> List[lsp.CompletionItem]:
    """Get completion items for @INCLUDE directives."""
    completions = []
    
    # Get the directory of the current document
    if doc_uri.startswith("file://"):
        doc_path = doc_uri[7:]
    else:
        doc_path = doc_uri
    
    doc_dir = os.path.dirname(doc_path)
    
    # List files in the directory
    try:
        for entry in sorted(os.listdir(doc_dir)):
            full_path = os.path.join(doc_dir, entry)
            if os.path.isfile(full_path):
                if entry.endswith(('.inp', '.cp2k', '.input')) or '.' not in entry:
                    completions.append(lsp.CompletionItem(
                        label=entry,
                        kind=lsp.CompletionItemKind.File,
                        detail="CP2K input file",
                        text_edit=lsp.TextEdit(
                            range=lsp.Range(start=position, end=position),
                            new_text=entry
                        )
                    ))
    except OSError:
        pass
    
    return completions


def _get_datafile_name_completions(
    doc_uri: str,
    position: lsp.Position
) -> List[lsp.CompletionItem]:
    """Get completion items for datafile name keywords."""
    completions = []
    
    # Common CP2K data file names
    common_files = [
        "BASIS_SET", "BASIS_MOLOPT", "BASIS_ADMM",
        "POTENTIAL", "GTH_POTENTIALS", "GTH_POTENTIALS_Q4",
        "POTENTIAL_ADMM", "POTENTIAL_GTH",
        "coord.xyz"
    ]
    
    for filename in common_files:
        completions.append(lsp.CompletionItem(
            label=filename,
            kind=lsp.CompletionItemKind.File,
            detail="Data file",
            text_edit=lsp.TextEdit(
                range=lsp.Range(start=position, end=position),
                new_text=filename
            )
        ))
    
    # Also list actual files in the directory
    if doc_uri.startswith("file://"):
        doc_path = doc_uri[7:]
    else:
        doc_path = doc_uri
    
    doc_dir = os.path.dirname(doc_path)
    
    try:
        for entry in sorted(os.listdir(doc_dir)):
            full_path = os.path.join(doc_dir, entry)
            if os.path.isfile(full_path):
                entry_upper = entry.upper()
                if any(pattern in entry_upper for pattern in ('BASIS', 'POTENTIAL', 'POT', 'GTH')):
                    completions.append(lsp.CompletionItem(
                        label=entry,
                        kind=lsp.CompletionItemKind.File,
                        detail="Data file",
                        text_edit=lsp.TextEdit(
                            range=lsp.Range(start=position, end=position),
                            new_text=entry
                        )
                    ))
    except OSError:
        pass
    
    return completions


def _get_datafile_entry_completions(
    ast: CP2KInput,
    line: str,
    doc_uri: str,
    workspace_index: WorkspaceResourceIndex,
    position: lsp.Position
) -> List[lsp.CompletionItem]:
    """Get completion items for BASIS_SET/POTENTIAL entries."""
    completions = []
    
    # Find the BASIS_SET_FILE_NAME or POTENTIAL_FILE_NAME
    data_filename = _find_data_filename(ast, line)
    
    if data_filename:
        ref = FileReference(
            uri=doc_uri,
            line=0,
            column=0,
            ref_type='DATA_FILE',
            value=data_filename
        )
        
        resolved = workspace_index.resolve_file_path(ref, doc_uri)
        
        if resolved and os.path.exists(resolved):
            if 'BASIS' in line.upper():
                data_file = parse_basis_file(resolved)
            else:
                data_file = parse_potential_file(resolved)
            
            if data_file:
                # List all available elements
                seen_elements: set = set()
                for entry in data_file.entries:
                    if entry.name not in seen_elements:
                        seen_elements.add(entry.name)
                        completions.append(lsp.CompletionItem(
                            label=entry.name,
                            kind=lsp.CompletionItemKind.Class,
                            detail="Element",
                            text_edit=lsp.TextEdit(
                                range=lsp.Range(start=position, end=position),
                                new_text=entry.name
                            )
                        ))
    
    return completions


def _find_data_filename(ast: CP2KInput, line: str) -> Optional[str]:
    """Find the data filename based on the current line context."""
    line_upper = line.upper()
    
    target_keyword = None
    if 'BASIS_SET' in line_upper and 'FILE_NAME' not in line_upper:
        target_keyword = 'BASIS_SET_FILE_NAME'
    elif 'POTENTIAL' in line_upper and 'FILE_NAME' not in line_upper:
        target_keyword = 'POTENTIAL_FILE_NAME'
    
    if not target_keyword:
        return None
    
    # Search in all sections
    def search_section(section: Section) -> Optional[Keyword]:
        for keyword in section.keywords:
            if keyword.name.upper() == target_keyword:
                return keyword
        for subsection in section.subsections:
            result = search_section(subsection)
            if result:
                return result
        return None
    
    if ast.global_section:
        result = search_section(ast.global_section)
        if result and result.value and result.value.value:
            return str(result.value.value).strip()
    
    for section in ast.sections:
        result = search_section(section)
        if result and result.value and result.value.value:
            return str(result.value.value).strip()
    
    return None


def _get_variable_completions(
    lines: List[str],
    position: lsp.Position
) -> List[lsp.CompletionItem]:
    """Get completion items for ${VAR} references by finding @SET definitions."""
    completions = []
    seen: set = set()
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            continue
        
        match = _SET_PATTERN.search(line_stripped)
        if match:
            var_name = match.group(1)
            if var_name not in seen:
                seen.add(var_name)
                completions.append(lsp.CompletionItem(
                    label=var_name,
                    kind=lsp.CompletionItemKind.Variable,
                    detail="@SET variable",
                    text_edit=lsp.TextEdit(
                        range=lsp.Range(start=position, end=position),
                        new_text=var_name
                    )
                ))
    
    return completions
