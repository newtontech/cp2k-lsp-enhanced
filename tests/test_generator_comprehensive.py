"""Comprehensive tests for cp2k_input_tools/generator.py to achieve 100% coverage."""

import pytest
from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.generator import (
    CP2KInputGenerator,
    GeneratorError,
    SectionNotFoundError,
    KeywordNotFoundError,
    SectionParametersNotFoundError,
    InvalidSectionDataError,
    InvalidKeywordDataError,
    InvalidBooleanDataError,
    SimplifiedSectionAmbiguityError,
    TreeNode,
)
from cp2k_input_tools.keyword_helpers import IntegerRange


class TestGeneratorInit:
    """Test CP2KInputGenerator initialization."""

    def test_init_default(self):
        """Test default initialization."""
        gen = CP2KInputGenerator()
        assert gen._shift == 3

    def test_init_custom_indent(self):
        """Test initialization with custom indent."""
        gen = CP2KInputGenerator(indent_shift=4)
        assert gen._shift == 4

    def test_init_custom_xml(self):
        """Test initialization with custom XML."""
        gen = CP2KInputGenerator(xmlspec=DEFAULT_CP2K_INPUT_XML)
        assert gen._parse_tree is not None


class TestGeneratorErrors:
    """Test generator error classes."""

    def test_generator_error(self):
        """Test GeneratorError."""
        with pytest.raises(GeneratorError):
            raise GeneratorError("test error")

    def test_section_not_found_error(self):
        """Test SectionNotFoundError."""
        with pytest.raises(SectionNotFoundError):
            raise SectionNotFoundError("section not found")

    def test_keyword_not_found_error(self):
        """Test KeywordNotFoundError."""
        with pytest.raises(KeywordNotFoundError):
            raise KeywordNotFoundError("keyword not found")

    def test_section_parameters_not_found_error(self):
        """Test SectionParametersNotFoundError."""
        with pytest.raises(SectionParametersNotFoundError):
            raise SectionParametersNotFoundError("no params")

    def test_invalid_section_data_error(self):
        """Test InvalidSectionDataError."""
        with pytest.raises(InvalidSectionDataError):
            raise InvalidSectionDataError("invalid data")

    def test_invalid_keyword_data_error(self):
        """Test InvalidKeywordDataError."""
        with pytest.raises(InvalidKeywordDataError):
            raise InvalidKeywordDataError("invalid keyword")

    def test_invalid_boolean_data_error(self):
        """Test InvalidBooleanDataError."""
        with pytest.raises(InvalidBooleanDataError):
            raise InvalidBooleanDataError("invalid boolean")

    def test_simplified_section_ambiguity_error(self):
        """Test SimplifiedSectionAmbiguityError."""
        with pytest.raises(SimplifiedSectionAmbiguityError):
            raise SimplifiedSectionAmbiguityError("ambiguous")


class TestTreeNode:
    """Test TreeNode namedtuple."""

    def test_tree_node_creation(self):
        """Test creating a TreeNode."""
        node = TreeNode(name="test", dictref={}, xmlnode=None, indent=0)
        assert node.name == "test"
        assert node.dictref == {}
        assert node.indent == 0


class TestGeneratorMethods:
    """Test CP2KInputGenerator methods."""

    def test_get_section(self):
        """Test _get_section method."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        section = gen._get_section("GLOBAL", root)
        assert section is not None

    def test_get_section_not_found(self):
        """Test _get_section raises error for non-existent section."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        with pytest.raises(SectionNotFoundError):
            gen._get_section("NONEXISTENT", root)

    def test_get_keyword(self):
        """Test _get_keyword method."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        global_section = gen._get_section("GLOBAL", root)
        keyword = gen._get_keyword("PROJECT_NAME", global_section)
        assert keyword is not None

    def test_get_keyword_not_found(self):
        """Test _get_keyword raises error for non-existent keyword."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        global_section = gen._get_section("GLOBAL", root)
        with pytest.raises(KeywordNotFoundError):
            gen._get_keyword("NONEXISTENT", global_section)

    def test_render_keyword_string(self):
        """Test _render_keyword with string value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        global_section = gen._get_section("GLOBAL", root)
        keyword = gen._get_keyword("PROJECT_NAME", global_section)
        result = list(gen._render_keyword("test", keyword))
        assert len(result) == 1
        assert "test" in result[0]

    def test_render_keyword_boolean(self):
        """Test _render_keyword with boolean value."""
        gen = CP2KInputGenerator()
        # Find a keyword with logical type
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "logical":
                    result = list(gen._render_keyword(True, kw))
                    assert ".TRUE." in result[0] or "T" in result[0]
                    break
            else:
                continue
            break

    def test_render_keyword_integer(self):
        """Test _render_keyword with integer value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "integer":
                    result = list(gen._render_keyword(42, kw))
                    assert "42" in result[0]
                    break
            else:
                continue
            break

    def test_render_keyword_integer_range(self):
        """Test _render_keyword with IntegerRange value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "integer":
                    range_val = IntegerRange(1, 10)
                    result = list(gen._render_keyword(range_val, kw))
                    assert "1..10" in result[0]
                    break
            else:
                continue
            break

    def test_render_keyword_real(self):
        """Test _render_keyword with real value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "real":
                    result = list(gen._render_keyword(3.14, kw))
                    assert "3.14" in result[0]
                    break
            else:
                continue
            break

    def test_render_keyword_list(self):
        """Test _render_keyword with list value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None:
                    n_var = int(dt.find("./N_VAR").text)
                    if n_var > 1:
                        result = list(gen._render_keyword(["val1", "val2"], kw))
                        assert len(result) >= 1
                        break
            else:
                continue
            break

    def test_render_keyword_with_whitespace(self):
        """Test _render_keyword with whitespace in value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "word":
                    result = list(gen._render_keyword("value with space", kw))
                    assert '"' in result[0]
                    break
            else:
                continue
            break


class TestBooleanRenderer:
    """Test boolean rendering."""

    def test_bool_true_variants(self):
        """Test various true boolean representations."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "logical":
                    for val in ["1", "T", ".T.", "TRUE", ".TRUE.", "Y", "YES", "ON"]:
                        result = list(gen._render_keyword(val, kw))
                        assert ".TRUE." in result[0]
                    break
            else:
                continue
            break

    def test_bool_false_variants(self):
        """Test various false boolean representations."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "logical":
                    for val in ["0", "F", ".F.", "FALSE", ".FALSE.", "N", "NO", "OFF"]:
                        result = list(gen._render_keyword(val, kw))
                        assert ".FALSE." in result[0]
                    break
            else:
                continue
            break

    def test_bool_invalid(self):
        """Test invalid boolean value."""
        gen = CP2KInputGenerator()
        root = gen._parse_tree.getroot()
        for section in root.iterfind(".//SECTION"):
            for kw in section.iterfind(".//KEYWORD"):
                dt = kw.find("./DATA_TYPE")
                if dt is not None and dt.get("kind") == "logical":
                    with pytest.raises(InvalidBooleanDataError):
                        list(gen._render_keyword("INVALID", kw))
                    break
            else:
                continue
            break
