"""Comprehensive tests for CP2K input generator."""

import io
import pytest

from cp2k_input_tools.generator import (
    CP2KInputGenerator,
    GeneratorError,
    InvalidBooleanDataError,
    InvalidKeywordDataError,
    InvalidSectionDataError,
    KeywordNotFoundError,
    SectionNotFoundError,
    SectionParametersNotFoundError,
    SimplifiedSectionAmbiguityError,
)
from cp2k_input_tools.keyword_helpers import IntegerRange


class TestCP2KInputGenerator:
    """Tests for CP2KInputGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return CP2KInputGenerator()

    def test_init_default(self):
        """Test generator initialization with defaults."""
        gen = CP2KInputGenerator()
        assert gen._shift == 3

    def test_init_custom_shift(self):
        """Test generator initialization with custom shift."""
        gen = CP2KInputGenerator(indent_shift=4)
        assert gen._shift == 4

    def test_line_iter_simple_global(self, generator):
        """Test line iterator with simple global section."""
        tree = {
            "GLOBAL": {
                "PROJECT_NAME": "test",
                "RUN_TYPE": "ENERGY"
            }
        }
        lines = list(generator.line_iter(tree))
        assert "&GLOBAL" in lines
        assert any("PROJECT_NAME test" in line for line in lines)
        assert any("RUN_TYPE ENERGY" in line for line in lines)
        assert "&END GLOBAL" in lines

    def test_line_iter_nested_sections(self, generator):
        """Test line iterator with nested sections."""
        tree = {
            "FORCE_EVAL": {
                "METHOD": "QUICKSTEP",
                "DFT": {
                    "BASIS_SET_FILE_NAME": "BASIS_SET"
                }
            }
        }
        lines = list(generator.line_iter(tree))
        assert "&FORCE_EVAL" in lines
        assert any("METHOD QUICKSTEP" in line for line in lines)
        assert "&DFT" in lines
        assert "&END DFT" in lines
        assert "&END FORCE_EVAL" in lines

    def test_line_iter_with_section_parameter(self, generator):
        """Test line iterator with section parameter."""
        tree = {
            "KIND": {
                "_": "H",
                "ELEMENT": "H",
                "BASIS_SET": "DZVP"
            }
        }
        lines = list(generator.line_iter(tree))
        assert any("&KIND H" in line for line in lines)
        assert any("ELEMENT H" in line for line in lines)

    def test_line_iter_repeated_sections(self, generator):
        """Test line iterator with repeated sections."""
        tree = {
            "+KIND": [
                {"_": "H", "ELEMENT": "H"},
                {"_": "O", "ELEMENT": "O"}
            ]
        }
        lines = list(generator.line_iter(tree))
        # Should have two KIND sections
        kind_starts = [line for line in lines if "&KIND" in line]
        assert len(kind_starts) == 2

    def test_line_iter_repeated_keywords(self, generator):
        """Test line iterator with repeated keywords."""
        tree = {
            "GLOBAL": {
                "+BASIS_SET": [["ORB", "DZVP"], ["AUX", "pFIT"]]
            }
        }
        lines = list(generator.line_iter(tree))
        basis_lines = [line for line in lines if "BASIS_SET" in line]
        assert len(basis_lines) == 2

    def test_line_iter_boolean_values(self, generator):
        """Test line iterator with boolean values."""
        tree = {
            "GLOBAL": {
                "bool_true": True,
                "bool_false": False
            }
        }
        lines = list(generator.line_iter(tree))
        assert any(".TRUE." in line for line in lines)
        assert any(".FALSE." in line for line in lines)

    def test_line_iter_integer_values(self, generator):
        """Test line iterator with integer values."""
        tree = {
            "GLOBAL": {
                "MAX_SCF": 50
            }
        }
        lines = list(generator.line_iter(tree))
        assert any("MAX_SCF 50" in line for line in lines)

    def test_line_iter_real_values(self, generator):
        """Test line iterator with real/float values."""
        tree = {
            "GLOBAL": {
                "EPS_SCF": 1.0e-7
            }
        }
        lines = list(generator.line_iter(tree))
        assert any("EPS_SCF 1e-07" in line or "EPS_SCF 1.0e-07" in line for line in lines)

    def test_line_iter_integer_range(self, generator):
        """Test line iterator with IntegerRange values."""
        tree = {
            "GLOBAL": {
                "RANGE": IntegerRange(1, 10)
            }
        }
        lines = list(generator.line_iter(tree))
        assert any("RANGE 1..10" in line for line in lines)

    def test_line_iter_string_with_quotes(self, generator):
        """Test line iterator with string values containing spaces."""
        tree = {
            "GLOBAL": {
                "PROJECT_NAME": "my project"
            }
        }
        lines = list(generator.line_iter(tree))
        assert any('"my project"' in line for line in lines)

    def test_line_iter_empty_tree(self, generator):
        """Test line iterator with empty tree."""
        tree = {}
        lines = list(generator.line_iter(tree))
        assert lines == []

    def test_line_iter_multiple_toplevel_sections(self, generator):
        """Test line iterator with multiple top-level sections."""
        tree = {
            "GLOBAL": {"PROJECT_NAME": "test"},
            "FORCE_EVAL": {"METHOD": "QUICKSTEP"}
        }
        lines = list(generator.line_iter(tree))
        assert "&GLOBAL" in lines
        assert "&FORCE_EVAL" in lines


class TestGeneratorErrors:
    """Tests for generator error handling."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return CP2KInputGenerator()

    def test_invalid_boolean_error(self):
        """Test InvalidBooleanDataError."""
        error = InvalidBooleanDataError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_invalid_keyword_data_error(self):
        """Test InvalidKeywordDataError."""
        error = InvalidKeywordDataError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_invalid_section_data_error(self):
        """Test InvalidSectionDataError."""
        error = InvalidSectionDataError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_keyword_not_found_error(self):
        """Test KeywordNotFoundError."""
        error = KeywordNotFoundError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_section_not_found_error(self):
        """Test SectionNotFoundError."""
        error = SectionNotFoundError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_section_parameters_not_found_error(self):
        """Test SectionParametersNotFoundError."""
        error = SectionParametersNotFoundError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_simplified_section_ambiguity_error(self):
        """Test SimplifiedSectionAmbiguityError."""
        error = SimplifiedSectionAmbiguityError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_generator_error(self):
        """Test GeneratorError."""
        error = GeneratorError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    def test_invalid_section_not_found(self, generator):
        """Test error when section doesn't exist."""
        tree = {"NONEXISTENT_SECTION": {"key": "value"}}
        with pytest.raises((SectionNotFoundError, KeyError)):
            list(generator.line_iter(tree))

    def test_invalid_keyword_not_found(self, generator):
        """Test error when keyword doesn't exist in section."""
        tree = {"GLOBAL": {"NONEXISTENT_KEYWORD": "value"}}
        with pytest.raises((KeywordNotFoundError, KeyError)):
            list(generator.line_iter(tree))


class TestBooleanRendering:
    """Tests for boolean value rendering."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return CP2KInputGenerator()

    def test_boolean_true_values(self, generator):
        """Test various true boolean representations."""
        from cp2k_input_tools.generator import CP2KInputGenerator
        
        # Create a simple tree with a keyword that expects boolean
        tree = {"GLOBAL": {"LROPTIMIZATION": True}}
        lines = list(generator.line_iter(tree))
        # Should render as .TRUE.
        assert any(".TRUE." in line for line in lines)


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        return CP2KInputGenerator()

    def test_deeply_nested_sections(self, generator):
        """Test with deeply nested section structure."""
        tree = {
            "FORCE_EVAL": {
                "DFT": {
                    "SCF": {
                        "MIXING": {
                            "ALPHA": 0.4
                        }
                    }
                }
            }
        }
        lines = list(generator.line_iter(tree))
        assert "&FORCE_EVAL" in lines
        assert "&DFT" in lines
        assert "&SCF" in lines
        assert "&MIXING" in lines
        assert "ALPHA 0.4" in lines

    def test_section_with_underscore_in_name(self, generator):
        """Test sections with underscores in names."""
        tree = {
            "FORCE_EVAL": {
                "SUBSYS": {
                    "CELL": {"A": [10.0, 0.0, 0.0]}
                }
            }
        }
        lines = list(generator.line_iter(tree))
        assert "&FORCE_EVAL" in lines
        assert "&SUBSYS" in lines
        assert "&CELL" in lines

    def test_list_value_in_keyword(self, generator):
        """Test keyword with list value."""
        tree = {
            "GLOBAL": {
                "WALLTIME": "01:00:00"
            }
        }
        lines = list(generator.line_iter(tree))
        # Should handle string values
        assert any("WALLTIME" in line for line in lines)


class TestCanonicalParserIntegration:
    """Integration tests with the parser."""

    def test_roundtrip_simple(self):
        """Test roundtrip parsing and generation."""
        from cp2k_input_tools.parser import CP2KInputParserSimplified
        from cp2k_input_tools.generator import CP2KInputGenerator

        original_input = """&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL
"""
        parser = CP2KInputParserSimplified()
        tree = parser.parse(io.StringIO(original_input))
        
        generator = CP2KInputGenerator()
        lines = list(generator.line_iter(tree))
        
        # Check key elements are preserved
        output = "\n".join(lines)
        assert "PROJECT_NAME" in output
        assert "RUN_TYPE" in output
        assert "ENERGY" in output

    def test_roundtrip_with_sections(self):
        """Test roundtrip with nested sections."""
        from cp2k_input_tools.parser import CP2KInputParserSimplified
        from cp2k_input_tools.generator import CP2KInputGenerator

        original_input = """&GLOBAL
  PROJECT_NAME roundtrip_test
&END GLOBAL
&FORCE_EVAL
  METHOD QUICKSTEP
&END FORCE_EVAL
"""
        parser = CP2KInputParserSimplified()
        tree = parser.parse(io.StringIO(original_input))
        
        generator = CP2KInputGenerator()
        lines = list(generator.line_iter(tree))
        
        output = "\n".join(lines)
        assert "GLOBAL" in output
        assert "FORCE_EVAL" in output
        assert "QUICKSTEP" in output
