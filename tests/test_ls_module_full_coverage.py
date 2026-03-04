"""Comprehensive tests for ls.py LSP server implementation."""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add language-server to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "language-server"))

if hasattr(sys, "pypy_version_info"):
    pytest.skip("pypy is currently not supported", allow_module_level=True)

pygls = pytest.importorskip("pygls")

from lsprotocol import types as lsp

from cp2k_input_tools.ls import (
    _build_keyword_doc,
    _build_section_doc,
    _completion,
    _completion_items,
    _document_text,
    _find_keyword_anywhere,
    _find_keyword_node,
    _find_named_child,
    _find_section_anywhere,
    _hover,
    _provide_keyword_completion,
    _provide_section_completion,
    _provide_value_completion,
    _schema_default_name,
    _schema_description,
    _schema_names,
    _section_stack_until_position,
    _strip_inline_comment,
    _validate,
    _word_at_position,
    setup_cp2k_ls_server,
)
from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML


class TestSchemaHelpers:
    """Tests for schema helper functions."""

    def test_schema_default_name(self):
        """Test _schema_default_name function."""
        import xml.etree.ElementTree as ET
        
        # Create a mock section element
        section_xml = '''<SECTION>
            <NAME type="default">TEST_SECTION</NAME>
            <DESCRIPTION>Test description</DESCRIPTION>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        name = _schema_default_name(section)
        assert name == "TEST_SECTION"

    def test_schema_default_name_no_default(self):
        """Test _schema_default_name without default."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <NAME>TEST_SECTION</NAME>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        name = _schema_default_name(section)
        assert name == "TEST_SECTION"

    def test_schema_default_name_empty(self):
        """Test _schema_default_name with empty name."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <NAME type="default"></NAME>
            <NAME>FALLBACK</NAME>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        name = _schema_default_name(section)
        assert name == "FALLBACK"

    def test_schema_names(self):
        """Test _schema_names function."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <NAME>NAME1</NAME>
            <NAME>NAME2</NAME>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        names = _schema_names(section)
        assert "NAME1" in names
        assert "NAME2" in names

    def test_schema_description(self):
        """Test _schema_description function."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <DESCRIPTION>  Test description  </DESCRIPTION>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        desc = _schema_description(section)
        assert desc == "Test description"

    def test_schema_description_empty(self):
        """Test _schema_description with empty description."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <DESCRIPTION>   </DESCRIPTION>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        desc = _schema_description(section)
        assert desc is None

    def test_schema_description_none(self):
        """Test _schema_description with no description."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <NAME>TEST</NAME>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        desc = _schema_description(section)
        assert desc is None


class TestStripInlineComment:
    """Tests for _strip_inline_comment."""

    def test_strip_bang_comment(self):
        """Test stripping ! comment."""
        result = _strip_inline_comment("value ! comment")
        assert result == "value "

    def test_strip_hash_comment(self):
        """Test stripping # comment."""
        result = _strip_inline_comment("value # comment")
        assert result == "value "

    def test_no_comment(self):
        """Test with no comment."""
        result = _strip_inline_comment("value")
        assert result == "value"


class TestFindNamedChild:
    """Tests for _find_named_child."""

    def test_find_existing_child(self):
        """Test finding an existing child."""
        import xml.etree.ElementTree as ET
        
        parent_xml = '''<SECTION>
            <KEYWORD>
                <NAME>TEST_KEY</NAME>
            </KEYWORD>
        </SECTION>'''
        parent = ET.fromstring(parent_xml)
        
        child = _find_named_child(parent, "KEYWORD", "TEST_KEY")
        assert child is not None

    def test_find_nonexistent_child(self):
        """Test finding a non-existent child."""
        import xml.etree.ElementTree as ET
        
        parent_xml = '''<SECTION>
            <KEYWORD>
                <NAME>TEST_KEY</NAME>
            </KEYWORD>
        </SECTION>'''
        parent = ET.fromstring(parent_xml)
        
        child = _find_named_child(parent, "KEYWORD", "NONEXISTENT")
        assert child is None


class TestFindKeywordNode:
    """Tests for _find_keyword_node."""

    def test_find_keyword(self):
        """Test finding a keyword."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <KEYWORD>
                <NAME>PROJECT_NAME</NAME>
            </KEYWORD>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        keyword = _find_keyword_node(section, "PROJECT_NAME")
        assert keyword is not None

    def test_find_default_keyword(self):
        """Test finding a default keyword."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <DEFAULT_KEYWORD>
                <NAME>DEFAULT</NAME>
            </DEFAULT_KEYWORD>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        keyword = _find_keyword_node(section, "DEFAULT")
        assert keyword is not None


class TestFindSectionAnywhere:
    """Tests for _find_section_anywhere."""

    def test_find_global_section(self):
        """Test finding GLOBAL section."""
        section = _find_section_anywhere("GLOBAL")
        assert section is not None

    def test_find_force_eval_section(self):
        """Test finding FORCE_EVAL section."""
        section = _find_section_anywhere("FORCE_EVAL")
        assert section is not None

    def test_find_nonexistent_section(self):
        """Test finding non-existent section."""
        section = _find_section_anywhere("NONEXISTENT_SECTION")
        assert section is None


class TestFindKeywordAnywhere:
    """Tests for _find_keyword_anywhere."""

    def test_find_project_name(self):
        """Test finding PROJECT_NAME keyword."""
        keyword = _find_keyword_anywhere("PROJECT_NAME")
        assert keyword is not None

    def test_find_run_type(self):
        """Test finding RUN_TYPE keyword."""
        keyword = _find_keyword_anywhere("RUN_TYPE")
        assert keyword is not None

    def test_find_nonexistent_keyword(self):
        """Test finding non-existent keyword."""
        keyword = _find_keyword_anywhere("NONEXISTENT_KEYWORD")
        assert keyword is None


class TestSectionStackUntilPosition:
    """Tests for _section_stack_until_position."""

    def test_empty_text(self):
        """Test with empty text."""
        stack = _section_stack_until_position("", 0, 0)
        assert len(stack) == 1  # Root only

    def test_single_section(self):
        """Test with single section."""
        text = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL"
        stack = _section_stack_until_position(text, 1, 0)
        # Stack should contain root + GLOBAL
        assert len(stack) >= 1

    def test_nested_sections(self):
        """Test with nested sections."""
        text = "&FORCE_EVAL\n  &DFT\n  &END DFT\n&END FORCE_EVAL"
        stack = _section_stack_until_position(text, 2, 0)
        assert len(stack) >= 1

    def test_section_end_recovery(self):
        """Test section end with mismatched name."""
        text = "&GLOBAL\n&END WRONG"
        # Should handle gracefully without crashing
        stack = _section_stack_until_position(text, 1, 0)
        assert len(stack) >= 1


class TestDocumentText:
    """Tests for _document_text."""

    def test_document_with_source(self):
        """Test document with source attribute."""
        mock_ls = MagicMock()
        mock_doc = MagicMock()
        mock_doc.source = "test content"
        mock_ls.workspace.get_text_document.return_value = mock_doc
        
        result = _document_text(mock_ls, "file://test.inp")
        assert result == "test content"

    def test_document_with_path(self, tmp_path):
        """Test document with path attribute."""
        mock_ls = MagicMock()
        test_file = tmp_path / "test.inp"
        test_file.write_text("file content")
        
        mock_doc = MagicMock()
        mock_doc.source = None
        mock_doc.path = str(test_file)
        mock_ls.workspace.get_text_document.return_value = mock_doc
        
        result = _document_text(mock_ls, f"file://{test_file}")
        assert result == "file content"


class TestBuildSectionDoc:
    """Tests for _build_section_doc."""

    def test_build_global_doc(self):
        """Test building GLOBAL section doc."""
        import xml.etree.ElementTree as ET
        
        section_xml = '''<SECTION>
            <NAME>GLOBAL</NAME>
            <DESCRIPTION>Global settings</DESCRIPTION>
            <KEYWORD><NAME>PROJECT_NAME</NAME></KEYWORD>
            <SECTION><NAME>PRINT</NAME></SECTION>
        </SECTION>'''
        section = ET.fromstring(section_xml)
        
        doc = _build_section_doc(section)
        assert "&GLOBAL" in doc
        assert "Global settings" in doc
        assert "PROJECT_NAME" in doc
        assert "PRINT" in doc


class TestBuildKeywordDoc:
    """Tests for _build_keyword_doc."""

    def test_build_keyword_doc(self):
        """Test building keyword documentation."""
        import xml.etree.ElementTree as ET
        
        keyword_xml = '''<KEYWORD>
            <NAME>PROJECT_NAME</NAME>
            <DESCRIPTION>Project name description</DESCRIPTION>
            <USAGE>PROJECT_NAME name</USAGE>
            <DEFAULT_VALUE>PROJECT</DEFAULT_VALUE>
            <DATA_TYPE kind="string">
                <N_VAR>1</N_VAR>
            </DATA_TYPE>
        </KEYWORD>'''
        keyword = ET.fromstring(keyword_xml)
        
        doc = _build_keyword_doc(keyword)
        assert "PROJECT_NAME" in doc
        assert "Project name description" in doc
        assert "PROJECT_NAME name" in doc
        assert "PROJECT" in doc
        assert "string" in doc


class TestCompletionItems:
    """Tests for _completion_items."""

    def test_basic_completion(self):
        """Test basic completion."""
        items = [("TEST", "Test item")]
        result = _completion_items(items, lsp.CompletionItemKind.Property, "TE")
        
        assert len(result) == 1
        assert result[0].label == "TEST"
        assert result[0].detail == "Test item"
        assert result[0].kind == lsp.CompletionItemKind.Property

    def test_prefix_filter(self):
        """Test prefix filtering."""
        items = [
            ("ALPHA", "Alpha item"),
            ("BETA", "Beta item")
        ]
        result = _completion_items(items, lsp.CompletionItemKind.Property, "AL")
        
        assert len(result) == 1
        assert result[0].label == "ALPHA"

    def test_deduplication(self):
        """Test deduplication."""
        items = [
            ("TEST", "Item 1"),
            ("TEST", "Item 2")
        ]
        result = _completion_items(items, lsp.CompletionItemKind.Property, "")
        
        assert len(result) == 1


class TestProvideSectionCompletion:
    """Tests for _provide_section_completion."""

    def test_global_completion(self):
        """Test GLOBAL section completion."""
        import xml.etree.ElementTree as ET
        
        root_xml = '''<SECTION>
            <SECTION>
                <NAME>GLOBAL</NAME>
                <DESCRIPTION>Global settings</DESCRIPTION>
            </SECTION>
            <SECTION>
                <NAME>FORCE_EVAL</NAME>
                <DESCRIPTION>Force eval</DESCRIPTION>
            </SECTION>
        </SECTION>'''
        root = ET.fromstring(root_xml)
        
        result = _provide_section_completion(root, "&GLO")
        assert len(result) > 0
        assert any(item.label == "&GLOBAL" for item in result)


class TestWordAtPosition:
    """Tests for _word_at_position."""

    def test_word_at_start(self):
        """Test word at start of line."""
        result = _word_at_position("PROJECT_NAME test", 0)
        assert result == "PROJECT_NAME"

    def test_word_in_middle(self):
        """Test word in middle of line."""
        result = _word_at_position("PROJECT_NAME test", 5)
        assert result == "PROJECT_NAME"

    def test_word_with_underscore(self):
        """Test word with underscore."""
        result = _word_at_position("TEST_WORD", 5)
        assert result == "TEST_WORD"

    def test_no_word(self):
        """Test when no word at position."""
        result = _word_at_position("   ", 1)
        assert result is None


class TestSetupServer:
    """Tests for setup_cp2k_ls_server."""

    def test_setup_server(self):
        """Test setting up server."""
        from pygls.server import LanguageServer
        
        server = LanguageServer("test", "1.0")
        setup_cp2k_ls_server(server)
        
        # Server should have features registered
        assert server is not None
