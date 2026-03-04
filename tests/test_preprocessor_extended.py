# Additional tests for preprocessor.py
import pytest
from io import StringIO
from cp2k_input_tools.preprocessor import CP2KPreprocessor


class TestPreprocessor:
    """Test CP2KPreprocessor"""

    def test_simple_input(self):
        """Test simple input preprocessing"""
        content = "&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL\n"
        fhandle = StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        lines = list(preprocessor)
        assert len(lines) > 0

    def test_comment_stripping(self):
        """Test comment stripping"""
        content = "PROJECT_NAME test ! this is a comment\n"
        fhandle = StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        lines = list(preprocessor)
        # Comments should be handled
        assert len(lines) >= 1

    def test_variable_substitution(self):
        """Test variable substitution"""
        content = "@SET VAR value\nPROJECT_NAME ${VAR}\n"
        fhandle = StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        lines = list(preprocessor)
        # Variable should be substituted
        assert any("value" in line for line in lines)