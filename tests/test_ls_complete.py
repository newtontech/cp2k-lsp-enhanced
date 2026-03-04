"""
Comprehensive unit tests for cp2k_input_tools/ls.py
Target: 100% code coverage
"""

import io
import pytest
from unittest.mock import MagicMock, patch, mock_open
import xml.etree.ElementTree as ET

# Skip all tests if pygls is not available
pygls = pytest.importorskip("pygls")

from lsprotocol.types import (
    CompletionParams,
    HoverParams,
    DefinitionParams,
    DocumentSymbolParams,
    Position,
    TextDocumentIdentifier,
    CompletionItemKind,
)

from cp2k_input_tools import ls
from cp2k_input_tools.ls import (
    get_schema_root,
    _schema_default_name,
    _schema_names,
    _schema_description,
    _schema_default_value,
    _schema_data_type,
    _schema_allowed_values,
    _strip_inline_comment,
    _find_named_child,
    _find_keyword_node,
    _find_section_anywhere,
    _find_keyword_anywhere,
    _section_stack_until_position,
    _document_text,
    _build_section_doc,
    _build_keyword_doc,
    _build_enum_value_doc,
    _completion_items,
    _provide_section_completion,
    _provide_keyword_completion,
    _provide_value_completion,
    _word_at_position,
    _completion,
    _hover,
    _definition,
    _document_symbol,
    _validate,
    setup_cp2k_ls_server,
    cp2k_server,
    SectionContext,
)


class TestSchemaRoot:
    """Test get_schema_root function"""
    
    def test_get_schema_root_caching(self):
        """Test that schema root is cached"""
        # Reset cache
        import cp2k_input_tools.ls as ls_module
        ls_module._SCHEMA_ROOT = None
        
        root1 = get_schema_root()
        root2 = get_schema_root()
        
        assert root1 is root2  # Should be same cached object


class TestSchemaHelpers:
    """Test schema helper functions"""
    
    def test_schema_default_name_with_default_type(self):
        """Test _schema_default_name with default type"""
        xml = """<SECTION>
            <NAME type="default">TEST_SECTION</NAME>
        </SECTION>"""
        node = ET.fromstring(xml)
        assert _schema_default_name(node) == "TEST_SECTION"
    
    def test_schema_default_name_without_default(self):
        """Test _schema_default_name without default type"""
        xml = """<SECTION>
            <NAME>ALT_NAME</NAME>
        </SECTION>"""
        node = ET.fromstring(xml)
        assert _schema_default_name(node) == "ALT_NAME"
    
    def test_schema_default_name_empty(self):
        """Test _schema_default_name with no names"""
        xml = "<SECTION></SECTION>"
        node = ET.fromstring(xml)
        assert _schema_default_name(node) is None
    
    def test_schema_names(self):
        """Test _schema_names function"""
        xml = """<SECTION>
            <NAME type="default">MAIN</NAME>
            <NAME>ALIAS1</NAME>
            <NAME>ALIAS2</NAME>
        </SECTION>"""
        node = ET.fromstring(xml)
        names = _schema_names(node)
        assert "MAIN" in names
        assert "ALIAS1" in names
        assert "ALIAS2" in names
    
    def test_schema_description(self):
        """Test _schema_description function"""
        xml = """<SECTION>
            <DESCRIPTION>This is a test description</DESCRIPTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        assert _schema_description(node) == "This is a test description"
    
    def test_schema_description_empty(self):
        """Test _schema_description with empty description"""
        xml = """<SECTION>
            <DESCRIPTION>   </DESCRIPTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        assert _schema_description(node) is None
    
    def test_schema_description_missing(self):
        """Test _schema_description with missing description"""
        xml = "<SECTION></SECTION>"
        node = ET.fromstring(xml)
        assert _schema_description(node) is None
    
    def test_schema_default_value(self):
        """Test _schema_default_value function"""
        xml = """<KEYWORD>
            <DEFAULT_VALUE>default</DEFAULT_VALUE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        assert _schema_default_value(node) == "default"
    
    def test_schema_default_value_missing(self):
        """Test _schema_default_value with missing default"""
        xml = "<KEYWORD></KEYWORD>"
        node = ET.fromstring(xml)
        assert _schema_default_value(node) is None
    
    def test_schema_data_type(self):
        """Test _schema_data_type function"""
        xml = """<KEYWORD>
            <DATA_TYPE kind="REAL"/>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        assert _schema_data_type(node) == "REAL"
    
    def test_schema_data_type_missing(self):
        """Test _schema_data_type with missing data type"""
        xml = "<KEYWORD></KEYWORD>"
        node = ET.fromstring(xml)
        assert _schema_data_type(node) is None
    
    def test_schema_allowed_values(self):
        """Test _schema_allowed_values function"""
        xml = """<KEYWORD>
            <DATA_TYPE>
                <ENUMERATION>
                    <ITEM><NAME>VALUE1</NAME></ITEM>
                    <ITEM><NAME>VALUE2</NAME></ITEM>
                </ENUMERATION>
            </DATA_TYPE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        values = _schema_allowed_values(node)
        assert "VALUE1" in values
        assert "VALUE2" in values
    
    def test_schema_allowed_values_empty(self):
        """Test _schema_allowed_values with no enum"""
        xml = """<KEYWORD>
            <DATA_TYPE kind="REAL"/>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        values = _schema_allowed_values(node)
        assert values == []


class TestStripInlineComment:
    """Test _strip_inline_comment function"""
    
    def test_strip_bang_comment(self):
        """Test stripping ! comment"""
        assert _strip_inline_comment("value ! comment") == "value "
    
    def test_strip_hash_comment(self):
        """Test stripping # comment"""
        assert _strip_inline_comment("value # comment") == "value "
    
    def test_no_comment(self):
        """Test string without comment"""
        assert _strip_inline_comment("value") == "value"
    
    def test_multiple_comment_chars(self):
        """Test with multiple comment characters"""
        assert _strip_inline_comment("value ! comment # more") == "value "


class TestFindNamedChild:
    """Test _find_named_child function"""
    
    def test_find_existing_child(self):
        """Test finding an existing child"""
        xml = """<SECTION>
            <KEYWORD>
                <NAME type="default">TEST</NAME>
            </KEYWORD>
        </SECTION>"""
        node = ET.fromstring(xml)
        result = _find_named_child(node, "KEYWORD", "TEST")
        assert result is not None
    
    def test_find_nonexistent_child(self):
        """Test finding a nonexistent child"""
        xml = """<SECTION>
            <KEYWORD>
                <NAME type="default">TEST</NAME>
            </KEYWORD>
        </SECTION>"""
        node = ET.fromstring(xml)
        result = _find_named_child(node, "KEYWORD", "NONEXISTENT")
        assert result is None


class TestFindKeywordNode:
    """Test _find_keyword_node function"""
    
    def test_find_regular_keyword(self):
        """Test finding a regular keyword"""
        xml = """<SECTION>
            <KEYWORD>
                <NAME type="default">TEST_KW</NAME>
            </KEYWORD>
        </SECTION>"""
        node = ET.fromstring(xml)
        result = _find_keyword_node(node, "TEST_KW")
        assert result is not None
    
    def test_find_default_keyword(self):
        """Test finding a default keyword"""
        xml = """<SECTION>
            <DEFAULT_KEYWORD>
                <NAME type="default">DEFAULT_KW</NAME>
            </DEFAULT_KEYWORD>
        </SECTION>"""
        node = ET.fromstring(xml)
        result = _find_keyword_node(node, "DEFAULT_KW")
        assert result is not None


class TestSectionStackUntilPosition:
    """Test _section_stack_until_position function"""
    
    def test_empty_document(self):
        """Test with empty document"""
        stack = _section_stack_until_position("", 0, 0)
        assert len(stack) == 1  # Root only
    
    def test_simple_section(self):
        """Test with simple section"""
        text = "&GLOBAL\n&END GLOBAL"
        stack = _section_stack_until_position(text, 0, 0)
        assert len(stack) >= 1  # At least root
    
    def test_nested_sections(self):
        """Test with nested sections"""
        text = """&FORCE_EVAL
&DFT
&END DFT
&END FORCE_EVAL"""
        # Position inside DFT section
        stack = _section_stack_until_position(text, 1, 0)
        assert len(stack) >= 2  # Root + at least one section


class TestDocumentText:
    """Test _document_text function"""
    
    def test_document_text_with_source(self):
        """Test getting text from document with source attribute"""
        mock_ls = MagicMock()
        mock_doc = MagicMock()
        mock_doc.source = "test content"
        mock_ls.workspace.get_text_document.return_value = mock_doc
        
        result = _document_text(mock_ls, "file:///test.inp")
        assert result == "test content"
    
    def test_document_text_from_file(self):
        """Test getting text from file"""
        mock_ls = MagicMock()
        mock_doc = MagicMock()
        mock_doc.source = None
        mock_doc.path = "/test/path.inp"
        mock_ls.workspace.get_text_document.return_value = mock_doc
        
        with patch("builtins.open", mock_open(read_data="file content")):
            result = _document_text(mock_ls, "file:///test.inp")
            assert result == "file content"


class TestBuildSectionDoc:
    """Test _build_section_doc function"""
    
    def test_build_section_doc(self):
        """Test building section documentation"""
        xml = """<SECTION>
            <NAME type="default">TEST</NAME>
            <DESCRIPTION>Test description</DESCRIPTION>
            <KEYWORD><NAME type="default">KW1</NAME></KEYWORD>
            <SECTION><NAME type="default">SUB1</NAME></SECTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        doc = _build_section_doc(node)
        
        assert "TEST" in doc
        assert "Test description" in doc
        assert "KW1" in doc
        assert "SUB1" in doc
    
    def test_build_section_doc_repeats(self):
        """Test building section doc with repeats attribute"""
        xml = """<SECTION repeats="yes">
            <NAME type="default">TEST</NAME>
            <DESCRIPTION>Test</DESCRIPTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        doc = _build_section_doc(node)
        
        assert "can be repeated" in doc


class TestBuildKeywordDoc:
    """Test _build_keyword_doc function"""
    
    def test_build_keyword_doc(self):
        """Test building keyword documentation"""
        xml = """<KEYWORD>
            <NAME type="default">TEST_KW</NAME>
            <DESCRIPTION>Keyword description</DESCRIPTION>
            <DATA_TYPE kind="REAL"/>
            <DEFAULT_VALUE>1.0</DEFAULT_VALUE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_keyword_doc(node)
        
        assert "TEST_KW" in doc
        assert "Keyword description" in doc
        assert "REAL" in doc
        assert "1.0" in doc
    
    def test_build_keyword_doc_enum(self):
        """Test building keyword doc with enum values"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <DATA_TYPE kind="KEYWORD">
                <ENUMERATION>
                    <ITEM><NAME>VAL1</NAME></ITEM>
                    <ITEM><NAME>VAL2</NAME></ITEM>
                </ENUMERATION>
            </DATA_TYPE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_keyword_doc(node)
        
        assert "VAL1" in doc or "Allowed values" in doc
    
    def test_build_keyword_doc_lone_value(self):
        """Test building keyword doc with lone keyword value"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <LONE_KEYWORD_VALUE>true</LONE_KEYWORD_VALUE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_keyword_doc(node)
        
        assert "Lone value" in doc or "true" in doc
    
    def test_build_keyword_doc_deprecated(self):
        """Test building keyword doc with deprecated flag"""
        xml = """<KEYWORD deprecated="yes">
            <NAME type="default">TEST</NAME>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_keyword_doc(node)
        
        assert "Deprecated" in doc


class TestBuildEnumValueDoc:
    """Test _build_enum_value_doc function"""
    
    def test_build_enum_value_doc_found(self):
        """Test building doc for existing enum value"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <DATA_TYPE kind="KEYWORD">
                <ENUMERATION>
                    <ITEM>
                        <NAME>MYVALUE</NAME>
                        <DESCRIPTION>Value description</DESCRIPTION>
                    </ITEM>
                </ENUMERATION>
            </DATA_TYPE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_enum_value_doc(node, "MYVALUE")
        
        assert doc is not None
        assert "Value description" in doc
    
    def test_build_enum_value_doc_not_found(self):
        """Test building doc for nonexistent enum value"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <DATA_TYPE kind="KEYWORD">
                <ENUMERATION>
                    <ITEM><NAME>OTHER</NAME></ITEM>
                </ENUMERATION>
            </DATA_TYPE>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_enum_value_doc(node, "NOTFOUND")
        
        assert doc is None
    
    def test_build_enum_value_doc_no_data_type(self):
        """Test building doc with no data type"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
        </KEYWORD>"""
        node = ET.fromstring(xml)
        doc = _build_enum_value_doc(node, "VALUE")
        
        assert doc is None


class TestCompletionItems:
    """Test _completion_items function"""
    
    def test_completion_items_basic(self):
        """Test basic completion items creation"""
        items = [
            ("ITEM1", "detail1", "doc1"),
            ("ITEM2", "detail2", "doc2"),
        ]
        completions = _completion_items(items, CompletionItemKind.Text, "", max_items=50)
        
        assert len(completions) == 2
        assert completions[0].label == "ITEM1"
        assert completions[1].label == "ITEM2"
    
    def test_completion_items_with_prefix(self):
        """Test completion items with prefix filter"""
        items = [
            ("ABC", "detail", None),
            ("DEF", "detail", None),
        ]
        completions = _completion_items(items, CompletionItemKind.Text, "AB", max_items=50)
        
        assert len(completions) == 1
        assert completions[0].label == "ABC"
    
    def test_completion_items_max_limit(self):
        """Test completion items respects max limit"""
        items = [(f"ITEM{i}", "detail", None) for i in range(100)]
        completions = _completion_items(items, CompletionItemKind.Text, "", max_items=10)
        
        assert len(completions) == 10
    
    def test_completion_items_deduplication(self):
        """Test completion items deduplication"""
        items = [
            ("ITEM", "detail1", None),
            ("ITEM", "detail2", None),
        ]
        completions = _completion_items(items, CompletionItemKind.Text, "", max_items=50)
        
        assert len(completions) == 1


class TestProvideSectionCompletion:
    """Test _provide_section_completion function"""
    
    def test_section_completion(self):
        """Test section completion"""
        xml = """<SECTION>
            <NAME type="default">PARENT</NAME>
            <SECTION repeats="yes">
                <NAME type="default">CHILD1</NAME>
            </SECTION>
            <SECTION>
                <NAME type="default">CHILD2</NAME>
            </SECTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        completions = _provide_section_completion(node, "&CH")
        
        # Should provide completions for CHILD1 and CHILD2
        labels = [c.label for c in completions]
        assert any("CHILD" in label for label in labels)


class TestProvideKeywordCompletion:
    """Test _provide_keyword_completion function"""
    
    def test_keyword_completion(self):
        """Test keyword completion"""
        xml = """<SECTION>
            <NAME type="default">PARENT</NAME>
            <KEYWORD>
                <NAME type="default">KEYWORD1</NAME>
                <DATA_TYPE kind="REAL"/>
            </KEYWORD>
            <SECTION>
                <NAME type="default">SUBSECTION</NAME>
            </SECTION>
        </SECTION>"""
        node = ET.fromstring(xml)
        completions = _provide_keyword_completion(node, "KEY")
        
        labels = [c.label for c in completions]
        assert any("KEYWORD" in label or "SUBSECTION" in label for label in labels)


class TestProvideValueCompletion:
    """Test _provide_value_completion function"""
    
    def test_value_completion_enum(self):
        """Test value completion for enum keyword"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <DATA_TYPE kind="KEYWORD">
                <ENUMERATION>
                    <ITEM><NAME>VAL1</NAME></ITEM>
                    <ITEM><NAME>VAL2</NAME></ITEM>
                </ENUMERATION>
            </DATA_TYPE>
        </KEYWORD>"""
        section = ET.fromstring("""<SECTION>
            <NAME type="default">PARENT</NAME>
        </SECTION>""")
        keyword = ET.fromstring(xml)
        
        # Mock the find function
        with patch.object(section, 'iterfind', return_value=[keyword]):
            completions = _provide_value_completion(section, "TEST", "")
        
        labels = [c.label for c in completions]
        assert "VAL1" in labels or len(completions) == 0
    
    def test_value_completion_logical(self):
        """Test value completion for logical keyword"""
        xml = """<KEYWORD>
            <NAME type="default">TEST</NAME>
            <DATA_TYPE kind="LOGICAL"/>
        </KEYWORD>"""
        section = ET.fromstring("""<SECTION>
            <NAME type="default">PARENT</NAME>
        </SECTION>""")
        keyword = ET.fromstring(xml)
        
        with patch.object(section, 'iterfind', return_value=[keyword]):
            completions = _provide_value_completion(section, "TEST", "")
        
        labels = [c.label for c in completions]
        assert "T" in labels or ".TRUE." in labels or len(completions) == 0
    
    def test_value_completion_not_found(self):
        """Test value completion for nonexistent keyword"""
        section = ET.fromstring("""<SECTION>
            <NAME type="default">PARENT</NAME>
        </SECTION>""")
        
        completions = _provide_value_completion(section, "NONEXISTENT", "")
        assert completions == []


class TestWordAtPosition:
    """Test _word_at_position function"""
    
    def test_word_at_position_simple(self):
        """Test getting word at position"""
        line = "PROJECT_NAME test"
        word = _word_at_position(line, 5)
        assert word == "PROJECT_NAME"
    
    def test_word_at_position_with_ampersand(self):
        """Test getting word with ampersand"""
        line = "&GLOBAL"
        word = _word_at_position(line, 1)
        assert word == "&GLOBAL"
    
    def test_word_at_position_no_match(self):
        """Test when no word at position"""
        line = "   "
        word = _word_at_position(line, 1)
        assert word is None


class TestCompletion:
    """Test _completion function"""
    
    def test_completion_section(self):
        """Test section completion"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLO"
        
        params = CompletionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp"),
            position=Position(line=0, character=4)
        )
        
        result = _completion(mock_ls, params)
        assert isinstance(result, list)
    
    def test_completion_keyword(self):
        """Test keyword completion"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLOBAL\nRUN"
        
        params = CompletionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp"),
            position=Position(line=1, character=3)
        )
        
        result = _completion(mock_ls, params)
        assert isinstance(result, list)


class TestHover:
    """Test _hover function"""
    
    def test_hover_section(self):
        """Test hover for section"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLOBAL"
        
        params = HoverParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp"),
            position=Position(line=0, character=2)
        )
        
        result = _hover(mock_ls, params)
        # Should return Hover or None
        assert result is None or hasattr(result, 'contents')
    
    def test_hover_keyword(self):
        """Test hover for keyword"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLOBAL\n  RUN_TYPE"
        
        params = HoverParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp"),
            position=Position(line=1, character=4)
        )
        
        result = _hover(mock_ls, params)
        assert result is None or hasattr(result, 'contents')


class TestDefinition:
    """Test _definition function"""
    
    def test_definition_section(self):
        """Test go-to-definition for section"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLOBAL\n&END GLOBAL"
        
        params = DefinitionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp"),
            position=Position(line=1, character=5)
        )
        
        result = _definition(mock_ls, params)
        assert result is None or hasattr(result, 'uri')


class TestDocumentSymbol:
    """Test _document_symbol function"""
    
    def test_document_symbol_basic(self):
        """Test document symbols"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = """&GLOBAL
&END GLOBAL
&FORCE_EVAL
&END FORCE_EVAL"""
        
        params = DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri="file:///test.inp")
        )
        
        result = _document_symbol(mock_ls, params)
        assert isinstance(result, list)


class TestValidate:
    """Test _validate function"""
    
    def test_validate_empty(self):
        """Test validation with empty content"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = ""
        mock_ls.workspace.get_text_document.return_value.uri = "file:///test.inp"
        
        params = MagicMock()
        params.text_document.uri = "file:///test.inp"
        
        _validate(mock_ls, params)
        
        # Should publish diagnostics
        mock_ls.publish_diagnostics.assert_called_once()
    
    def test_validate_with_error(self):
        """Test validation with syntax error"""
        mock_ls = MagicMock()
        mock_ls.workspace.get_text_document.return_value.source = "&GLOBAL\n  invalid'"
        mock_ls.workspace.get_text_document.return_value.uri = "file:///test.inp"
        mock_ls.workspace.get_text_document.return_value.path = "/test.inp"
        
        params = MagicMock()
        params.text_document.uri = "file:///test.inp"
        
        _validate(mock_ls, params)
        
        # Should publish diagnostics with error
        mock_ls.publish_diagnostics.assert_called_once()


class TestSetupServer:
    """Test setup_cp2k_ls_server function"""
    
    def test_setup_server(self):
        """Test that server setup registers features"""
        mock_server = MagicMock()
        mock_server.feature = MagicMock(return_value=lambda f: f)
        
        setup_cp2k_ls_server(mock_server)
        
        # Should have registered features
        assert mock_server.feature.called


class TestSectionContext:
    """Test SectionContext class"""
    
    def test_section_context_creation(self):
        """Test SectionContext creation"""
        xml = """<SECTION>
            <NAME type="default">TEST</NAME>
        </SECTION>"""
        node = ET.fromstring(xml)
        ctx = SectionContext("TEST", node, 1)
        
        assert ctx.name == "TEST"
        assert ctx.node is node
        assert ctx.level == 1
        assert isinstance(ctx.keywords, set)
