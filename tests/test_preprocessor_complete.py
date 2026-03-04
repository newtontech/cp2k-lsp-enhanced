"""
Comprehensive unit tests for cp2k_input_tools/preprocessor.py
Target: 100% code coverage
"""

import io
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from cp2k_input_tools.preprocessor import CP2KPreprocessor, _Variable, _ConditionalBlock
from cp2k_input_tools.parser_errors import PreprocessorError
from cp2k_input_tools.tokenizer import TokenizerError


class TestVariableAndConditionalBlock:
    """Test _Variable and _ConditionalBlock named tuples"""
    
    def test_variable_creation(self):
        """Test _Variable named tuple creation"""
        from collections import defaultdict
        ctx = defaultdict(list)
        var = _Variable("test_value", ctx)
        assert var.value == "test_value"
        assert var.ctx is ctx
    
    def test_conditional_block_creation(self):
        """Test _ConditionalBlock named tuple creation"""
        from collections import defaultdict
        ctx = defaultdict(list)
        block = _ConditionalBlock("condition_string", ctx)
        assert block.condition == "condition_string"
        assert block.ctx is ctx


class TestCP2KPreprocessorInit:
    """Test CP2KPreprocessor initialization"""
    
    def test_init_with_str_base_dir(self):
        """Test initialization with string base_dir"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, "/base/dir")
        assert len(preprocessor._inc_dirs) == 1
        assert isinstance(preprocessor._inc_dirs[0], Path)
        assert str(preprocessor._inc_dirs[0]) == "/base/dir"
    
    def test_init_with_path_base_dir(self):
        """Test initialization with Path base_dir"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, Path("/base/dir"))
        assert len(preprocessor._inc_dirs) == 1
        assert preprocessor._inc_dirs[0] == Path("/base/dir")
    
    def test_init_with_bytes_base_dir(self):
        """Test initialization with bytes base_dir"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, b"/base/dir")
        assert len(preprocessor._inc_dirs) == 1
        assert str(preprocessor._inc_dirs[0]) == "/base/dir"
    
    def test_init_with_sequence_base_dir(self):
        """Test initialization with sequence of base_dirs"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ["/dir1", "/dir2", Path("/dir3")])
        assert len(preprocessor._inc_dirs) == 3
        assert str(preprocessor._inc_dirs[0]) == "/dir1"
        assert str(preprocessor._inc_dirs[1]) == "/dir2"
        assert str(preprocessor._inc_dirs[2]) == "/dir3"
    
    def test_init_with_invalid_base_dir_type(self):
        """Test initialization with invalid base_dir type"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        with pytest.raises(TypeError, match="invalid type passed for base_dir"):
            CP2KPreprocessor(fhandle, 12345)
    
    def test_init_with_initial_variable_values(self):
        """Test initialization with initial variable values"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        initial_vars = {"VAR1": "value1", "VAR2": "value2"}
        preprocessor = CP2KPreprocessor(fhandle, ".", initial_vars)
        
        assert "VAR1" in preprocessor._varstack
        assert "VAR2" in preprocessor._varstack
        assert preprocessor._varstack["VAR1"].value == "value1"
        assert preprocessor._varstack["VAR2"].value == "value2"


class TestVariableResolution:
    """Test _resolve_variables method"""
    
    def test_resolve_simple_brace_variable(self):
        """Test resolving ${VAR} style variable"""
        content = "@SET VAR test_value\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        # Process the SET line
        next(preprocessor)
        
        # Now test variable resolution
        result = preprocessor._resolve_variables("VALUE: ${VAR}")
        assert result == "VALUE: test_value"
    
    def test_resolve_simple_dollar_variable(self):
        """Test resolving $VAR style variable"""
        content = "@SET VAR test_value\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        next(preprocessor)
        
        result = preprocessor._resolve_variables("VALUE: $VAR")
        assert result == "VALUE: test_value"
    
    def test_resolve_variable_with_default(self):
        """Test resolving ${VAR-default} style variable with default"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        # Variable UNDEFINED doesn't exist, should use default
        result = preprocessor._resolve_variables("VALUE: ${UNDEFINED-default_value}")
        assert result == "VALUE: default_value"
    
    def test_resolve_undefined_variable_no_default(self):
        """Test resolving undefined variable without default"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="undefined variable"):
            preprocessor._resolve_variables("VALUE: ${UNDEFINED}")
    
    def test_resolve_unterminated_brace_variable(self):
        """Test unterminated ${variable"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="unterminated variable"):
            preprocessor._resolve_variables("VALUE: ${UNTERMINATED")
    
    def test_resolve_invalid_variable_name_brace(self):
        """Test invalid variable name with ${}"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="invalid variable name"):
            preprocessor._resolve_variables("VALUE: ${123invalid}")
    
    def test_resolve_invalid_variable_name_dollar(self):
        """Test invalid variable name with $"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="invalid variable name"):
            preprocessor._resolve_variables("VALUE: $123invalid")
    
    def test_resolve_multiple_variables(self):
        """Test resolving multiple variables in one line"""
        content = "@SET VAR1 hello\n@SET VAR2 world\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        next(preprocessor)
        next(preprocessor)
        
        result = preprocessor._resolve_variables("${VAR1} ${VAR2}")
        assert result == "hello world"
    
    def test_resolve_variable_case_insensitive(self):
        """Test that variable names are case-insensitive"""
        content = "@SET VAR test_value\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        next(preprocessor)
        
        result = preprocessor._resolve_variables("${var}")
        assert result == "test_value"
        
        result = preprocessor._resolve_variables("${Var}")
        assert result == "test_value"


class TestPreprocessorInstructions:
    """Test _parse_preprocessor_instruction method"""
    
    def test_set_instruction(self):
        """Test @SET instruction"""
        content = "@SET MYVAR myvalue\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert "MYVAR" in preprocessor._varstack
        assert preprocessor._varstack["MYVAR"].value == "myvalue"
    
    def test_set_with_variable_substitution(self):
        """Test @SET with variable substitution in value"""
        content = "@SET VAR1 hello\n@SET VAR2 ${VAR1}world\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert preprocessor._varstack["VAR2"].value == "helloworld"
    
    def test_set_invalid_variable_name(self):
        """Test @SET with invalid variable name"""
        content = "@SET 123invalid value\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="invalid variable name"):
            list(preprocessor)
    
    def test_if_true_condition(self):
        """Test @IF with true condition"""
        content = """@IF 1
PROJECT_NAME test
@ENDIF
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert any("PROJECT_NAME" in line for line in lines)
    
    def test_if_false_condition(self):
        """Test @IF with false condition (0)"""
        content = """@IF 0
PROJECT_NAME should_not_appear
@ENDIF
PROJECT_NAME should_appear
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert not any("should_not_appear" in line for line in lines)
        assert any("should_appear" in line for line in lines)
    
    def test_if_empty_condition(self):
        """Test @IF with empty condition"""
        content = """@IF
PROJECT_NAME should_not_appear
@ENDIF
PROJECT_NAME should_appear
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert not any("should_not_appear" in line for line in lines)
        assert any("should_appear" in line for line in lines)
    
    def test_if_equality_condition(self):
        """Test @IF with == condition"""
        content = """@SET VAR test
@IF ${VAR} == test
PROJECT_NAME equal
@ENDIF
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert any("equal" in line for line in lines)
    
    def test_if_inequality_condition(self):
        """Test @IF with /= condition"""
        content = """@SET VAR test
@IF ${VAR} /= other
PROJECT_NAME different
@ENDIF
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert any("different" in line for line in lines)
    
    def test_nested_if_error(self):
        """Test that nested @IF raises error"""
        content = """@IF 1
@IF 1
PROJECT_NAME test
@ENDIF
@ENDIF
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="nested @IF are not allowed"):
            list(preprocessor)
    
    def test_endif_without_if(self):
        """Test @ENDIF without previous @IF"""
        content = """@ENDIF
PROJECT_NAME test
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="found @ENDIF without a previous @IF"):
            list(preprocessor)
    
    def test_endif_with_garbage(self):
        """Test @ENDIF with garbage after it"""
        content = """@IF 1
PROJECT_NAME test
@ENDIF garbage
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="garbage found after @ENDIF"):
            list(preprocessor)
    
    def test_endif_with_comment(self):
        """Test @ENDIF with comment (should work)"""
        content = """@IF 1
PROJECT_NAME test
@ENDIF ! this is a comment
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert any("test" in line for line in lines)
    
    def test_unclosed_conditional(self):
        """Test unclosed @IF block"""
        content = """@IF 1
PROJECT_NAME test
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="conditional block not closed"):
            list(preprocessor)


class TestIncludeInstruction:
    """Test @INCLUDE and @XCTYPE instructions"""
    
    def test_include_single_quoted_file(self):
        """Test @INCLUDE with single quoted filename"""
        content = "@INCLUDE 'test.inc'\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        # Should not raise, but won't find the file
        with pytest.raises(PreprocessorError, match="could not be opened"):
            list(preprocessor)
    
    def test_include_double_quoted_file(self):
        """Test @INCLUDE with double quoted filename"""
        content = '@INCLUDE "test.inc"\n'
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="could not be opened"):
            list(preprocessor)
    
    def test_include_without_quotes(self):
        """Test @INCLUDE without quotes"""
        content = "@INCLUDE test.inc\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="could not be opened"):
            list(preprocessor)
    
    def test_include_empty_filename(self):
        """Test @INCLUDE with empty filename"""
        content = "@INCLUDE\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="requires exactly one argument"):
            list(preprocessor)
    
    def test_include_with_multiple_tokens(self):
        """Test @INCLUDE with multiple tokens"""
        content = "@INCLUDE 'file1' 'file2'\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="requires exactly one argument"):
            list(preprocessor)
    
    def test_include_unterminated_quote(self):
        """Test @INCLUDE with unterminated quote"""
        content = "@INCLUDE 'unterminated\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(TokenizerError):
            list(preprocessor)
    
    def test_xctype_instruction(self):
        """Test @XCTYPE instruction"""
        content = "@XCTYPE 'test.sec'\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        # Should look for xc_section/test.sec
        with pytest.raises(PreprocessorError, match="could not be opened"):
            list(preprocessor)
    
    def test_unknown_preprocessor_directive(self):
        """Test unknown @ directive"""
        content = "@UNKNOWN directive\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        with pytest.raises(PreprocessorError, match="unknown preprocessor directive"):
            list(preprocessor)


class TestPreprocessorProperties:
    """Test CP2KPreprocessor properties"""
    
    def test_line_range_property(self):
        """Test line_range property"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        # Initially not available until iteration
        line = next(preprocessor)
        assert preprocessor.line_range is not None
    
    def test_colnrs_property(self):
        """Test colnrs property"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        line = next(preprocessor)
        assert preprocessor.colnrs is not None
    
    def test_starts_property(self):
        """Test starts property"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        line = next(preprocessor)
        assert preprocessor.starts is not None
    
    def test_fname_property(self):
        """Test fname property"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        fhandle.name = "test.inp"
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        line = next(preprocessor)
        assert preprocessor.fname is not None


class TestPreprocessorIterator:
    """Test CP2KPreprocessor as iterator"""
    
    def test_empty_input(self):
        """Test with empty input"""
        content = ""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert len(lines) == 0
    
    def test_comment_only_input(self):
        """Test with comment-only input"""
        content = """# This is a comment
! This is also a comment
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert len(lines) == 0
    
    def test_simple_lines(self):
        """Test simple line processing"""
        content = """PROJECT_NAME test1
PROJECT_NAME test2
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert len(lines) == 2
        assert "test1" in lines[0]
        assert "test2" in lines[1]
    
    def test_variable_in_content(self):
        """Test variable substitution in content lines"""
        content = """@SET VAR substituted
PROJECT_NAME ${VAR}
"""
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        lines = list(preprocessor)
        assert any("substituted" in line for line in lines)
    
    def test_stop_iteration(self):
        """Test StopIteration at end of input"""
        content = "PROJECT_NAME test\n"
        fhandle = io.StringIO(content)
        preprocessor = CP2KPreprocessor(fhandle, ".")
        
        next(preprocessor)  # First line
        with pytest.raises(StopIteration):
            next(preprocessor)  # Should raise StopIteration
