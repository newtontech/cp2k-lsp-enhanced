"""Workspace resource index for tracking file references and providing navigation.

This module provides the WorkspaceResourceIndex service that:
- Tracks @INCLUDE, BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME, COORD_FILE_NAME references
- Parses basis and potential files for entry listing
- Provides diagnostics for missing/unreadable files
- Supports goto-definition and completion for file references
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DataFileEntry:
    """Represents an entry in a basis or potential file."""
    name: str
    start_line: int
    end_line: int
    raw_text: str = ""


@dataclass
class FileReference:
    """Represents a reference to an external file in CP2K input."""
    uri: str
    line: int
    column: int
    ref_type: str  # 'INCLUDE', 'BASIS_SET_FILE_NAME', 'POTENTIAL_FILE_NAME', 'COORD_FILE_NAME'
    value: str


@dataclass
class WorkspaceResourceIndex:
    """Index of workspace resources for file tracking and navigation.
    
    This class tracks file references across the workspace and provides:
    - File reference tracking (@INCLUDE, BASIS_SET_FILE_NAME, etc.)
    - Data file parsing (BASIS_SET, POTENTIAL entries)
    - Diagnostics for missing files
    - Goto-definition and completion support
    """
    root_uri: str = ""
    file_references: Dict[str, List[FileReference]] = field(default_factory=dict)
    data_files: Dict[str, List[DataFileEntry]] = field(default_factory=dict)
    _cache: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.root_uri:
            self.root_uri = os.getcwd()
    
    def get_root_path(self) -> str:
        """Get the root path from URI."""
        if self.root_uri.startswith("file://"):
            return self.root_uri[7:]
        return self.root_uri
    
    def add_file_reference(self, doc_uri: str, ref: FileReference) -> None:
        """Add a file reference to the index."""
        if doc_uri not in self.file_references:
            self.file_references[doc_uri] = []
        self.file_references[doc_uri].append(ref)
    
    def clear_document(self, doc_uri: str) -> None:
        """Clear all references for a document."""
        if doc_uri in self.file_references:
            del self.file_references[doc_uri]
    
    def invalidate_file(self, file_path: str) -> None:
        """Invalidate cached data for a file."""
        # Clear data file cache
        if file_path in self.data_files:
            del self.data_files[file_path]
        # Clear general cache entries that reference this file
        keys_to_remove = [k for k in self._cache if file_path in str(self._cache[k])]
        for key in keys_to_remove:
            del self._cache[key]
    
    def parse_cp2k_document(self, doc_uri: str, content: str) -> List[FileReference]:
        """Parse a CP2K input document and extract file references.
        
        Args:
            doc_uri: The document URI
            content: The document content
            
        Returns:
            List of file references found
        """
        refs = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('!'):
                continue
            
            # Check for @INCLUDE
            include_match = re.match(r'\s*@INCLUDE\s+["\']([^"\']+)["\']', line, re.IGNORECASE)
            if include_match:
                ref_value = include_match.group(1)
                refs.append(FileReference(
                    uri=doc_uri,
                    line=line_num - 1,
                    column=line.index('@INCLUDE'),
                    ref_type='INCLUDE',
                    value=ref_value
                ))
                continue
            
            # Check for BASIS_SET_FILE_NAME
            basis_match = re.match(r'\s*BASIS_SET_FILE_NAME\s+(\S+)', line, re.IGNORECASE)
            if basis_match:
                ref_value = basis_match.group(1)
                refs.append(FileReference(
                    uri=doc_uri,
                    line=line_num - 1,
                    column=line.index('BASIS_SET_FILE_NAME'),
                    ref_type='BASIS_SET_FILE_NAME',
                    value=ref_value
                ))
                continue
            
            # Check for POTENTIAL_FILE_NAME
            potential_match = re.match(r'\s*POTENTIAL_FILE_NAME\s+(\S+)', line, re.IGNORECASE)
            if potential_match:
                ref_value = potential_match.group(1)
                refs.append(FileReference(
                    uri=doc_uri,
                    line=line_num - 1,
                    column=line.index('POTENTIAL_FILE_NAME'),
                    ref_type='POTENTIAL_FILE_NAME',
                    value=ref_value
                ))
                continue
            
            # Check for COORD_FILE_NAME
            coord_match = re.match(r'\s*COORD_FILE_NAME\s+(\S+)', line, re.IGNORECASE)
            if coord_match:
                ref_value = coord_match.group(1)
                refs.append(FileReference(
                    uri=doc_uri,
                    line=line_num - 1,
                    column=line.index('COORD_FILE_NAME'),
                    ref_type='COORD_FILE_NAME',
                    value=ref_value
                ))
                continue
        
        # Store references
        self.file_references[doc_uri] = refs
        return refs
    
    def resolve_file_path(self, ref: FileReference, doc_uri: str) -> Optional[str]:
        """Resolve a file reference to an absolute path.

        Args:
            ref: The file reference to resolve
            doc_uri: The document URI containing the reference

        Returns:
            Absolute path if file exists, None otherwise
        """
        # Handle relative paths
        if not os.path.isabs(ref.value):
            # Get directory of the referencing document
            if doc_uri.startswith("file://"):
                doc_path = doc_uri[7:]
            else:
                doc_path = doc_uri
            doc_dir = os.path.dirname(doc_path)
            file_path = os.path.join(doc_dir, ref.value)
        else:
            file_path = ref.value

        # Normalize path
        file_path = os.path.normpath(file_path)

        if os.path.exists(file_path):
            return file_path
        return None
    
    def parse_data_file(self, file_path: str) -> List[DataFileEntry]:
        """Parse a basis or potential file to extract entries.
        
        These files typically have entries like:
        - Basis set entries: element name followed by block of data
        - Potential entries: element name followed by block of data
        
        Args:
            file_path: Path to the data file
            
        Returns:
            List of data file entries
        """
        if file_path in self.data_files:
            return self.data_files[file_path]
        
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('!'):
                    i += 1
                    continue
                
                # Check if this is an entry start (element name or element with label)
                # Pattern: element name (possibly with numbers/letters) at start of line
                # Examples: "H", "He", "Si", "Cu", "Cl 1", "H GTH-PBE"
                entry_match = re.match(r'^([A-Z][a-z]?\d*(?:\s+[A-Za-z0-9_-]+)?)\s*$', line)
                if entry_match:
                    entry_name = entry_match.group(1).strip()
                    start_line = i
                    
                    # Find the end of this entry (next entry or end of file)
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        # Check if this is a new entry
                        if next_line and not next_line.startswith('#') and not next_line.startswith('!'):
                            if re.match(r'^([A-Z][a-z]?\d*(?:\s+[A-Za-z0-9_-]+)?)\s*$', next_line):
                                break
                        j += 1
                    
                    end_line = j - 1
                    raw_text = ''.join(lines[start_line:end_line + 1])
                    
                    entries.append(DataFileEntry(
                        name=entry_name,
                        start_line=start_line,
                        end_line=end_line,
                        raw_text=raw_text
                    ))
                    
                    i = j
                else:
                    i += 1
            
            # Cache the result
            self.data_files[file_path] = entries
            
        except Exception as e:
            logger.warning(f"Failed to parse data file {file_path}: {e}")
            self.data_files[file_path] = []
        
        return entries
    
    def find_data_entry(self, file_path: str, entry_name: str) -> Optional[DataFileEntry]:
        """Find a specific entry in a data file.
        
        Args:
            file_path: Path to the data file
            entry_name: Name of the entry to find
            
        Returns:
            DataFileEntry if found, None otherwise
        """
        entries = self.parse_data_file(file_path)
        
        # Try exact match first
        for entry in entries:
            if entry.name.lower() == entry_name.lower():
                return entry
        
        # Try partial match (for entries like "H GTH-PBE" matching "H")
        for entry in entries:
            if entry.name.lower().startswith(entry_name.lower()):
                return entry
        
        return None
    
    def get_all_references(self) -> Dict[str, List[FileReference]]:
        """Get all file references grouped by document."""
        return dict(self.file_references)
    
    def get_references_for_file(self, file_path: str) -> List[FileReference]:
        """Get all references to a specific file across all documents."""
        refs = []
        for doc_uri, doc_refs in self.file_references.items():
            for ref in doc_refs:
                resolved = self.resolve_file_path(ref, doc_uri)
                if resolved and os.path.normpath(resolved) == os.path.normpath(file_path):
                    refs.append(ref)
        return refs
    
    def get_missing_files(self) -> List[Tuple[FileReference, str]]:
        """Get all file references that point to missing files.
        
        Returns:
            List of (reference, resolved_path) tuples for missing files
        """
        missing = []
        for doc_uri, refs in self.file_references.items():
            for ref in refs:
                resolved = self.resolve_file_path(ref, doc_uri)
                if resolved is None:
                    missing.append((ref, ref.value))
        return missing
    
    def get_duplicate_entries(self, file_path: str) -> List[DataFileEntry]:
        """Find duplicate entries in a data file."""
        entries = self.parse_data_file(file_path)
        seen = {}
        duplicates = []
        
        for entry in entries:
            key = entry.name.lower()
            if key in seen:
                duplicates.append(entry)
            else:
                seen[key] = entry
        
        return duplicates
