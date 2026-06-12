"""
CP2K input schema index for fast LSP lookups.

This module provides a cached index of the CP2K input XML schema,
enabling efficient lookups of sections, keywords, and their metadata
without re-parsing the 27MB XML file on every request.

TDD: Implementation written to pass tests in tests/test_schema_index.py
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from . import DEFAULT_CP2K_INPUT_XML


@dataclass(frozen=True)
class SectionSpec:
    """Specification for a CP2K input section."""

    name: str
    parent_path: Tuple[str, ...]
    description: str = ""
    repeats: bool = False
    aliases: Tuple[str, ...] = ()
    child_section_names: Tuple[str, ...] = ()
    child_keyword_names: Tuple[str, ...] = ()


@dataclass(frozen=True)
class KeywordSpec:
    """Specification for a CP2K input keyword."""

    name: str
    section_path: Tuple[str, ...]
    type_name: str = "string"
    default_value: str = ""
    default_unit: str = ""
    description: str = ""
    usage: str = ""
    enum_values: Tuple[str, ...] = ()
    repeats: bool = False
    lone_keyword_value: str = ""
    aliases: Tuple[str, ...] = ()


class CP2KSchemaIndex:
    """Cached index of CP2K input schema for fast lookups."""

    def __init__(self) -> None:
        """Load and parse the CP2K input XML schema."""
        self._loaded: bool = False
        self._sections: Dict[Tuple[str, ...], SectionSpec] = {}
        self._keywords: Dict[Tuple[Tuple[str, ...], str], KeywordSpec] = {}
        self._total_sections: int = 0
        self._total_keywords: int = 0
        self._load_schema()

    def _load_schema(self) -> None:
        """Parse the XML schema and build the index."""
        tree = ET.parse(DEFAULT_CP2K_INPUT_XML)
        root = tree.getroot()

        def walk_sections(
            node: ET.Element,
            path: Tuple[str, ...] = (),
        ) -> None:
            """Recursively walk sections and build index."""
            for section_elem in node.findall("SECTION"):
                name_elem = section_elem.find("NAME")
                if name_elem is None or not name_elem.text:
                    continue

                sec_name = name_elem.text.upper()
                new_path = path + (sec_name,)

                # Collect child section names
                child_section_names: List[str] = []
                for child_sec in section_elem.findall("SECTION"):
                    child_name = child_sec.find("NAME")
                    if child_name is not None and child_name.text:
                        child_section_names.append(child_name.text.upper())

                # Collect keyword specs
                child_keywords: List[str] = []
                for kw in section_elem.findall(".//KEYWORD"):
                    kw_name_elem = kw.find("NAME")
                    if kw_name_elem is None or not kw_name_elem.text:
                        continue

                    kw_name = kw_name_elem.text.upper()
                    child_keywords.append(kw_name)

                    # Build KeywordSpec
                    type_name = "string"
                    enum_values: Tuple[str, ...] = ()
                    default_value = ""
                    default_unit = ""
                    description = ""
                    usage = ""
                    repeats = False
                    lone_keyword_value = ""

                    # Data type
                    dt = kw.find("DATA_TYPE")
                    if dt is not None:
                        type_name = dt.get("kind", "string")

                        # Extract enum values from ENUMERATION/ITEM/NAME
                        enum_el = dt.find("ENUMERATION")
                        if enum_el is not None:
                            vals: List[str] = []
                            for item in enum_el.findall("ITEM"):
                                item_name = item.find("NAME")
                                if item_name is not None and item_name.text:
                                    vals.append(item_name.text.upper())
                            enum_values = tuple(vals)

                        # Default value
                        default_el = dt.find("DEFAULT")
                        if default_el is not None:
                            default_value = default_el.text or ""

                    # Default unit
                    du = kw.find("DEFAULT_UNIT")
                    if du is not None and du.text:
                        default_unit = du.text

                    # Description
                    desc = kw.find("DESCRIPTION")
                    if desc is not None and desc.text:
                        description = desc.text

                    # Usage
                    usage_el = kw.find("USAGE")
                    if usage_el is not None and usage_el.text:
                        usage = usage_el.text

                    # Repeats
                    repeats_el = kw.find("REPEATABLE")
                    if repeats_el is not None:
                        repeats = True

                    # Lone keyword value
                    lone_el = kw.find("LONE_KEYWORD_VALUE")
                    if lone_el is not None and lone_el.text:
                        lone_keyword_value = lone_el.text

                    keyword_spec = KeywordSpec(
                        name=kw_name,
                        section_path=new_path,
                        type_name=type_name,
                        default_value=default_value,
                        default_unit=default_unit,
                        description=description,
                        usage=usage,
                        enum_values=enum_values,
                        repeats=repeats,
                        lone_keyword_value=lone_keyword_value,
                    )
                    self._keywords[(new_path, kw_name)] = keyword_spec
                    self._total_keywords += 1

                # Section description
                section_desc = ""
                desc_elem = section_elem.find("DESCRIPTION")
                if desc_elem is not None and desc_elem.text:
                    section_desc = desc_elem.text

                # Repeats for section
                sec_repeats = False
                repeats_el = section_elem.find("REPEATABLE")
                if repeats_el is not None:
                    sec_repeats = True

                section_spec = SectionSpec(
                    name=sec_name,
                    parent_path=path,
                    description=section_desc,
                    repeats=sec_repeats,
                    child_section_names=tuple(child_section_names),
                    child_keyword_names=tuple(child_keywords),
                )
                self._sections[new_path] = section_spec
                self._total_sections += 1

                # Recurse into nested sections
                walk_sections(section_elem, new_path)

        walk_sections(root)
        self._loaded = True

    @property
    def loaded(self) -> bool:
        """Check if the schema has been loaded."""
        return self._loaded

    @property
    def total_sections(self) -> int:
        """Get total number of sections in the schema."""
        return self._total_sections

    @property
    def total_keywords(self) -> int:
        """Get total number of keywords in the schema."""
        return self._total_keywords

    def get_section(self, path: Tuple[str, ...]) -> Optional[SectionSpec]:
        """Get a section spec by its path.

        Args:
            path: Tuple of section names, e.g. ("FORCE_EVAL", "DFT", "QS")

        Returns:
            SectionSpec if found, None otherwise
        """
        return self._sections.get(path)

    def get_child_sections(
        self,
        path: Tuple[str, ...],
    ) -> List[SectionSpec]:
        """Get child sections of a given section path.

        Args:
            path: Tuple of section names, e.g. ("FORCE_EVAL", "DFT")

        Returns:
            List of SectionSpec objects for child sections
        """
        if not path:
            # Return top-level sections (sections with empty parent_path)
            return [
                spec for spec in self._sections.values()
                if spec.parent_path == ()
            ]

        parent_spec = self._sections.get(path)
        if parent_spec is None:
            return []

        return [
            self._sections.get(path + (name,))
            for name in parent_spec.child_section_names
        ]

    def get_keywords(
        self,
        path: Tuple[str, ...],
    ) -> List[KeywordSpec]:
        """Get all keywords for a given section path.

        Args:
            path: Tuple of section names, e.g. ("FORCE_EVAL", "DFT", "QS")

        Returns:
            List of KeywordSpec objects
        """
        section_spec = self._sections.get(path)
        if section_spec is None:
            return []

        return [
            self._keywords.get((path, name))
            for name in section_spec.child_keyword_names
            if self._keywords.get((path, name)) is not None
        ]

    def get_keyword(
        self,
        path: Tuple[str, ...],
        name: str,
    ) -> Optional[KeywordSpec]:
        """Get a keyword spec by section path and keyword name.

        Args:
            path: Tuple of section names
            name: Keyword name (case-insensitive lookup will be added)

        Returns:
            KeywordSpec if found, None otherwise
        """
        return self._keywords.get((path, name.upper()))


@lru_cache(maxsize=1)
def get_schema_index() -> CP2KSchemaIndex:
    """Get the singleton schema index instance.

    Returns:
        The cached CP2KSchemaIndex instance
    """
    return CP2KSchemaIndex()
