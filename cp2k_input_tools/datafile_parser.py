"""Parser for CP2K basis set and potential files.

This module provides parsing for CP2K data files (BASIS_SET, POTENTIAL, etc.)
to extract entry names, ranges, and support navigation features.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DataEntry:
    """Represents an entry in a CP2K data file (basis set or potential)."""
    name: str
    label: str = ""  # Optional label like "GTH-PBE", "DZV-GTH-PADE"
    start_line: int = 0
    end_line: int = 0
    line_count: int = 0
    
    @property
    def full_name(self) -> str:
        """Get the full name with label."""
        if self.label:
            return f"{self.name} {self.label}"
        return self.name


@dataclass
class DataFile:
    """Represents a parsed CP2K data file."""
    path: str
    entries: List[DataEntry]
    raw_lines: List[str]
    
    def find_entry(self, name: str, label: str = "") -> Optional[DataEntry]:
        """Find an entry by name and optional label."""
        name_lower = name.lower()
        label_lower = label.lower() if label else ""
        
        for entry in self.entries:
            if entry.name.lower() == name_lower:
                if not label or entry.label.lower() == label_lower:
                    return entry
        
        # Try partial match on label
        if label:
            for entry in self.entries:
                if entry.name.lower() == name_lower and label_lower in entry.label.lower():
                    return entry
        
        return None
    
    def find_entries_by_name(self, name: str) -> List[DataEntry]:
        """Find all entries with a given name (e.g., all H entries)."""
        return [e for e in self.entries if e.name.lower() == name.lower()]


def parse_basis_file(file_path: str) -> Optional[DataFile]:
    """Parse a CP2K basis set file.
    
    Basis set files have entries like:
        H
        2
        1  0  1  1.3  1.0
        1  0  0  0.8  1.0
        
        He
        2
        1  0  1  1.8  1.0
        1  0  0  1.2  1.0
    
    Args:
        file_path: Path to the basis set file
        
    Returns:
        DataFile with parsed entries, or None if parsing fails
    """
    return _parse_data_file(file_path, 'basis')


def parse_potential_file(file_path: str) -> Optional[DataFile]:
    """Parse a CP2K potential file.
    
    Potential files have entries like:
        H GTH-PBE
        1
        0  2  0  1.3
        
        He GTH-PBE
        2
        0  2  0  1.8
        0  2  1  1.1  1.0  1.5  1.4
    
    Args:
        file_path: Path to the potential file
        
    Returns:
        DataFile with parsed entries, or None if parsing fails
    """
    return _parse_data_file(file_path, 'potential')


def _parse_data_file(file_path: str, file_type: str) -> Optional[DataFile]:
    """Parse a CP2K data file (basis or potential).
    
    Args:
        file_path: Path to the data file
        file_type: Type of file ('basis' or 'potential')
        
    Returns:
        DataFile with parsed entries, or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        logger.warning(f"Failed to read {file_type} file {file_path}: {e}")
        return None
    
    entries = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('!'):
            i += 1
            continue
        
        # Try to match entry start
        # Pattern: element name (1-2 chars) optionally followed by label
        # Examples: "H", "He", "H GTH-PBE", "Si DZVP-MOLOPT-GTH"
        entry_match = re.match(r'^([A-Z][a-z]?)\s*(.*?)\s*$', line)
        
        if entry_match:
            element = entry_match.group(1)
            label = entry_match.group(2).strip()
            
            start_line = i
            
            # Find the end of this entry
            # Entry ends at: next element entry, or end of file
            j = i + 1
            last_content_line = i  # Track last non-empty, non-comment line
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Skip empty lines and comments
                if not next_line or next_line.startswith('#') or next_line.startswith('!'):
                    j += 1
                    continue
                
                # Check if this is a new element entry
                if re.match(r'^[A-Z][a-z]?\s', next_line) or re.match(r'^[A-Z][a-z]?$', next_line):
                    break
                
                last_content_line = j
                j += 1
            
            end_line = last_content_line
            line_count = end_line - start_line + 1
            
            entries.append(DataEntry(
                name=element,
                label=label,
                start_line=start_line,
                end_line=end_line,
                line_count=line_count
            ))
            
            i = j
        else:
            i += 1
    
    return DataFile(
        path=file_path,
        entries=entries,
        raw_lines=lines
    )


def get_entry_range(data_file: DataFile, entry_name: str, label: str = "") -> Optional[Tuple[int, int]]:
    """Get the line range for a specific entry.
    
    Args:
        data_file: The parsed data file
        entry_name: Element name (e.g., "H", "Si")
        label: Optional label (e.g., "GTH-PBE")
        
    Returns:
        Tuple of (start_line, end_line) 0-indexed, or None if not found
    """
    entry = data_file.find_entry(entry_name, label)
    if entry:
        return (entry.start_line, entry.end_line)
    return None


def list_entries(data_file: DataFile, element: str = "") -> List[DataEntry]:
    """List entries in a data file, optionally filtered by element.
    
    Args:
        data_file: The parsed data file
        element: Optional element name to filter by
        
    Returns:
        List of matching entries
    """
    if element:
        return data_file.find_entries_by_name(element)
    return data_file.entries


def get_available_labels(data_file: DataFile, element: str) -> List[str]:
    """Get all available labels for an element.
    
    Args:
        data_file: The parsed data file
        element: Element name
        
    Returns:
        List of labels for the element
    """
    entries = data_file.find_entries_by_name(element)
    return [e.label for e in entries if e.label]


def validate_entry(data_file: DataFile, element: str, label: str = "") -> Tuple[bool, str]:
    """Validate if an entry exists in the data file.
    
    Args:
        data_file: The parsed data file
        element: Element name
        label: Optional label
        
    Returns:
        Tuple of (is_valid, message)
    """
    entry = data_file.find_entry(element, label)
    if entry:
        return True, f"Entry {entry.full_name} found at lines {entry.start_line + 1}-{entry.end_line + 1}"
    
    # Try to provide helpful suggestions
    available = data_file.find_entries_by_name(element)
    if available:
        labels = [e.label for e in available if e.label]
        if labels:
            return False, f"Entry {element} found but label '{label}' not available. Available labels: {', '.join(labels)}"
        return False, f"Entry {element} found but without label"
    
    # Check if element exists at all
    all_elements = set(e.name for e in data_file.entries)
    if element in all_elements:
        return True, f"Entry {element} exists"
    
    return False, f"Element {element} not found in data file"
