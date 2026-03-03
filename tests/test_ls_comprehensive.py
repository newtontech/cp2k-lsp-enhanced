"""Comprehensive tests for cp2k_input_tools/ls.py to achieve 100% coverage."""

import io
import sys
import pytest
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Skip on pypy
if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.ls import (
    _schema_default_name,
    _schema_names,
    _schema_description,
    _strip_inline_comment,
    _find_named_child,
    _find_section_anywhere,
    _find_keyword_anywhere,
    _section_stack_until_position,
    _build_section_doc,
    _build_keyword_doc,
    _completion_items,
    _provide_section_completion,
    _provide_keyword_completion,
    _provide_value_completion,
    _word_at_position,
    _hover_for_value,
)
from cp2k_input_tools.parser import CP2KInputParser


class TestSchemaHelpers:
    """Test schema helper functions."""

    def test_schema_default_name(self):
        """Test _schema_default_name function."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        for section in root.iterfind(".//SECTION"):
            name = _schema_default_name(section)
            if name:
                assert isinstance(name, str)
                assert name.isupper()
                break

    def test_schema_default_name_none(self):
        """Test _schema_default_name returns None for elements without names."""
        elem = ET.Element("TEST")
        result = _schema_default_name(elem)
        assert result is None

    def test_schema_names(self):
        """Test _schema_names function."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        for section in root.iterfind(".//SECTION"):
            names = _schema_names(section)
            assert isinstance(names, list)
            if names:
                assert all(isinstance(n, str) for n in names)
                break

    def test_schema_description(self):
        """Test _schema_description function."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        for section in root.iterfind(".//SECTION"):
            desc = _schema_description(section)
            if desc:
                assert isinstance(desc, str)
                break

    def test_schema_description_none(self):
        """Test _schema_description returns None for elements without description."""
        elem = ET.Element("TEST")
        result = _schema_description(elem)
        assert result is None

    def test_strip_inline_comment(self):
        """Test _strip_inline_comment function."""
        assert _strip_inline_comment("value # comment") == "value "
        assert _strip_inline_comment("value ! comment") == "value "
        assert _strip_inline_comment("value") == "value"
        assert _strip_inline_comment("") == ""

    def test_find_named_child(self):
        """Test _find_named_child function."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        global_section = _find_named_child(root, "SECTION", "GLOBAL")
        if global_section is not None:
            name = _schema_default_name(global_section)
            assert name == "GLOBAL"

    def test_find_named_child_not_found(self):
        """Test _find_named_child returns None for non-existent child."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        result = _find_named_child(root, "SECTION", "NONEXISTENT_SECTION")
        assert result is None

    def test_find_section_anywhere(self):
        """Test _find_section_anywhere function."""
        section = _find_section_anywhere("GLOBAL")
        if section is not None:
            name = _schema_default_name(section)
            assert name == "GLOBAL"

    def test_find_section_anywhere_not_found(self):
        """Test _find_section_anywhere returns None for non-existent section."""
        result = _find_section_anywhere("NONEXISTENT_SECTION")
        assert result is None

    def test_find_keyword_anywhere(self):
        """Test _find_keyword_anywhere function."""
        keyword = _find_keyword_anywhere("PROJECT_NAME")
        if keyword is not None:
            name = _schema_default_name(keyword)
            assert name == "PROJECT_NAME"

    def test_find_keyword_anywhere_not_found(self):
        """Test _find_keyword_anywhere returns None for non-existent keyword."""
        result = _find_keyword_anywhere("NONEXISTENT_KEYWORD")
        assert result is None


class TestSectionStack:
    """Test _section_stack_until_position function."""

    def test_empty_text(self):
        """Test with empty text."""
        result = _section_stack_until_position("", 0, 0)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_simple_section(self):
        """Test with simple section."""
        text = "&GLOBAL\nPROJECT_NAME test\n&END GLOBAL"
        result = _section_stack_until_position(text, 0, 7)
        assert isinstance(result, list)

    def test_nested_sections(self):
        """Test with nested sections."""
        text = "&GLOBAL\n&FORCE_EVAL\n&END FORCE_EVAL\n&END GLOBAL"
        result = _section_stack_until_position(text, 2, 0)
        assert isinstance(result, list)

    def test_with_comments(self):
        """Test with comments."""
        text = "# comment\n&GLOBAL\n&END GLOBAL"
        result = _section_stack_until_position(text, 1, 7)
        assert isinstance(result, list)

    def test_with_preprocessor(self):
        """Test with preprocessor directives."""
        text = "@SET VAR value\n&GLOBAL\n&END GLOBAL"
        result = _section_stack_until_position(text, 1, 7)
        assert isinstance(result, list)

    def test_end_section(self):
        """Test ending a section."""
        text = "&GLOBAL\n&END GLOBAL\n"
        result = _section_stack_until_position(text, 1, 10)
        assert isinstance(result, list)

    def test_mismatched_end(self):
        """Test mismatched end tag."""
        text = "&GLOBAL\n&END WRONG\n"
        result = _section_stack_until_position(text, 1, 10)
        assert isinstance(result, list)


class TestDocumentationBuilders:
    """Test documentation builder functions."""

    def test_build_section_doc(self):
        """Test _build_section_doc function."""
        section = _find_section_anywhere("GLOBAL")
        if section:
            doc = _build_section_doc(section)
            assert "GLOBAL" in doc
            assert isinstance(doc, str)

    def test_build_keyword_doc(self):
        """Test _build_keyword_doc function."""
        keyword = _find_keyword_anywhere("PROJECT_NAME")
        if keyword:
            doc = _build_keyword_doc(keyword)
            assert "PROJECT_NAME" in doc
            assert isinstance(doc, str)

    def test_build_keyword_doc_with_enumeration(self):
        """Test building doc for keyword with enumeration."""
        keyword = _find_keyword_anywhere("RUN_TYPE")
        if keyword:
            doc = _build_keyword_doc(keyword)
            assert "RUN_TYPE" in doc or "Type:" in doc


class TestCompletionItems:
    """Test completion item generation."""

    def test_completion_items_basic(self):
        """Test basic completion items."""
        from lsprotocol.types import CompletionItemKind
        items = [("LABEL1", "detail1"), ("LABEL2", "detail2")]
        result = _completion_items(items, CompletionItemKind.Property, "")
        assert len(result) == 2

    def test_completion_items_with_prefix(self):
        """Test completion items with prefix filter."""
        from lsprotocol.types import CompletionItemKind
        items = [("ABC", "detail1"), ("ABD", "detail2"), ("XYZ", "detail3")]
        result = _completion_items(items, CompletionItemKind.Property, "AB")
        assert len(result) == 2

    def test_completion_items_dedup(self):
        """Test completion items deduplication."""
        from lsprotocol.types import CompletionItemKind
        items = [("ABC", "detail1"), ("ABC", "detail2")]
        result = _completion_items(items, CompletionItemKind.Property, "")
        assert len(result) == 1


class TestCompletionProviders:
    """Test completion provider functions."""

    def test_provide_section_completion(self):
        """Test _provide_section_completion function."""
        root = ET.parse(DEFAULT_CP2K_INPUT_XML).getroot()
        items = _provide_section_completion(root, "&")
        assert isinstance(items, list)

    def test_provide_keyword_completion(self):
        """Test _provide_keyword_completion function."""
        section = _find_section_anywhere("GLOBAL")
        if section:
            items = _provide_keyword_completion(section, "PRO")
            assert isinstance(items, list)

    def test_provide_value_completion(self):
        """Test _provide_value_completion function."""
        section = _find_section_anywhere("GLOBAL")
        if section:
            items = _provide_value_completion(section, "RUN_TYPE", "")
            assert isinstance(items, list)


class TestWordAtPosition:
    """Test _word_at_position function."""

    def test_word_at_start(self):
        """Test word at start of line."""
        result = _word_at_position("PROJECT_NAME test", 5)
        assert result == "PROJECT_NAME"

    def test_word_in_middle(self):
        """Test word in middle of line."""
        result = _word_at_position("PROJECT_NAME test", 15)
        assert result == "test"

    def test_no_word(self):
        """Test when no word at position."""
        result = _word_at_position("   ", 1)
        assert result is None

    def test_with_ampersand(self):
        """Test word with ampersand."""
        result = _word_at_position("&GLOBAL", 3)
        assert result == "&GLOBAL"


class TestHoverForValue:
    """Test _hover_for_value function."""

    def test_hover_for_value(self):
        """Test hover for enum value."""
        keyword = _find_keyword_anywhere("RUN_TYPE")
        if keyword:
            hover = _hover_for_value(keyword, "ENERGY")
            if hover:
                assert hasattr(hover, "contents")

    def test_hover_for_value_not_found(self):
        """Test hover for non-existent value."""
        keyword = _find_keyword_anywhere("PROJECT_NAME")
        if keyword:
            hover = _hover_for_value(keyword, "NONEXISTENT")
            assert hover is None
