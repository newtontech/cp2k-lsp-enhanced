"""CP2K Schema Index - Parsed XML schema for completion and validation.

Provides lazy-loaded access to CP2K section/keyword definitions parsed from
the cp2k_input.xml schema file.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class KeywordSpec:
    """Specification for a CP2K keyword."""

    name: str
    variable_type: Optional[str] = None
    default_value: Optional[str] = None
    enumeration_values: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class SectionSpec:
    """Specification for a CP2K section."""

    name: str
    description: Optional[str] = None
    subsections: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


class CP2KSchemaIndex:
    """Index of CP2K schema parsed from cp2k_input.xml.

    Provides efficient lookup of sections and keywords by path.
    """

    def __init__(self, xml_path: Path):
        self._xml_path = xml_path
        self._tree: Optional[ET.ElementTree[ET.Element[str]]] = None
        self._sections: Dict[Tuple[str, ...], SectionSpec] = {}
        self._keywords: Dict[Tuple[str, ...], Dict[str, KeywordSpec]] = {}
        self._root_section_names: List[str] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load the schema on first access."""
        if self._loaded:
            return

        tree = ET.parse(self._xml_path)
        self._tree = tree
        root = tree.getroot()

        # Find the root section container
        sections_container = root.find(".//SECTIONS")
        if sections_container is None:
            # Fallback: look for SECTION elements directly under root
            sections_container = root

        # Parse root-level sections
        for section_elem in sections_container.findall("SECTION"):
            name_elem = section_elem.find("NAME")
            if name_elem is None or name_elem.text is None:
                continue
            section_name = name_elem.text.strip().upper()
            self._root_section_names.append(section_name)
            self._parse_section(section_elem, (section_name,))

        self._loaded = True

    def _parse_section(self, section_elem: ET.Element, path: Tuple[str, ...]) -> None:
        """Recursively parse a section element."""
        name_elem = section_elem.find("NAME")
        if name_elem is None or name_elem.text is None:
            return

        section_name = name_elem.text.strip().upper()

        # Get description
        desc_elem = section_elem.find("DESCRIPTION")
        description = desc_elem.text if desc_elem is not None else None

        # Get subsections
        subsection_names: List[str] = []
        keyword_names: List[str] = []

        # Parse keywords in this section
        for kw_elem in section_elem.findall("KEYWORD"):
            kw_name_elem = kw_elem.find("NAME[@type='default']")
            if kw_name_elem is None or kw_name_elem.text is None:
                continue
            kw_name = kw_name_elem.text.strip().upper()
            keyword_names.append(kw_name)

            # Parse keyword details
            self._parse_keyword(kw_elem, path, kw_name)

        # Parse subsections
        for subsec_elem in section_elem.findall("SECTION"):
            subsec_name_elem = subsec_elem.find("NAME")
            if subsec_name_elem is None or subsec_name_elem.text is None:
                continue
            subsec_name = subsec_name_elem.text.strip().upper()
            subsection_names.append(subsec_name)

            # Recursively parse subsection
            subsec_path = path + (subsec_name,)
            self._parse_section(subsec_elem, subsec_path)

        # Store section spec
        self._sections[path] = SectionSpec(
            name=section_name,
            description=description,
            subsections=subsection_names,
            keywords=keyword_names,
        )

    def _parse_keyword(self, kw_elem: ET.Element, section_path: Tuple[str, ...], kw_name: str) -> None:
        """Parse a keyword element."""
        # Get data type
        dt_elem = kw_elem.find("DATA_TYPE")
        variable_type = None
        enumeration_values: List[str] = []

        if dt_elem is not None:
            kind_elem = dt_elem.find("kind")
            if kind_elem is not None and kind_elem.text:
                variable_type = kind_elem.text.strip()

            # For keyword type, extract enum values
            if variable_type == "keyword":
                for name_elem in dt_elem.findall(".//NAME"):
                    if name_elem.text:
                        enumeration_values.append(name_elem.text.strip())

        # Get default value
        default_value = None
        default_elem = kw_elem.find("DEFAULT_VALUE")
        if default_elem is not None and default_elem.text:
            default_value = default_elem.text.strip()

        # Get description
        desc_elem = kw_elem.find("DESCRIPTION")
        description = desc_elem.text if desc_elem is not None else None

        keyword_spec = KeywordSpec(
            name=kw_name,
            variable_type=variable_type,
            default_value=default_value,
            enumeration_values=enumeration_values,
            description=description,
        )

        if section_path not in self._keywords:
            self._keywords[section_path] = {}
        self._keywords[section_path][kw_name] = keyword_spec

    def get_root_sections(self) -> List[str]:
        """Get list of root section names."""
        self._ensure_loaded()
        return list(self._root_section_names)

    def get_child_sections(self, parent_path: Tuple[str, ...]) -> List[str]:
        """Get child section names for a given parent path."""
        self._ensure_loaded()
        section = self._sections.get(parent_path)
        if section:
            return list(section.subsections)
        return []

    def get_section(self, path: Tuple[str, ...]) -> Optional[SectionSpec]:
        """Get section spec by path."""
        self._ensure_loaded()
        return self._sections.get(path)

    def get_keywords(self, section_path: Tuple[str, ...]) -> Dict[str, KeywordSpec]:
        """Get keywords for a section path."""
        self._ensure_loaded()
        return dict(self._keywords.get(section_path, {}))

    def get_keyword(self, section_path: Tuple[str, ...], keyword_name: str) -> Optional[KeywordSpec]:
        """Get a specific keyword spec."""
        self._ensure_loaded()
        keywords = self._keywords.get(section_path, {})
        return keywords.get(keyword_name)


# Singleton instance
_schema_index: Optional[CP2KSchemaIndex] = None


def get_schema_index() -> CP2KSchemaIndex:
    """Get or create the global schema index singleton."""
    global _schema_index
    if _schema_index is None:
        from . import DEFAULT_CP2K_INPUT_XML

        _schema_index = CP2KSchemaIndex(DEFAULT_CP2K_INPUT_XML)
    return _schema_index
