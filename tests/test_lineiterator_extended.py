# Extended tests for cp2k_input_tools/lineiterator.py
# Target: 100% coverage

import io
import pytest

from cp2k_input_tools.lineiterator import (
    ContinuationLineIterator,
    MultiFileLineIterator,
    LineContinuationError,
)


class TestContinuationLineIterator:
    """Test ContinuationLineIterator class"""

    def test_simple_lines(self):
        """Test iterating over simple lines"""
        content = "line1\nline2\nline3\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        lines = list(it)
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

    def test_line_continuation(self):
        """Test line continuation with backslash"""
        content = "line1\\\ncontinued\nline2\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        lines = list(it)
        assert len(lines) == 2
        assert lines[0] == "line1continued"
        assert lines[1] == "line2"

    def test_line_range(self):
        """Test line_range property - returns (start, end) tuple"""
        content = "line1\nline2\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        next(it)
        # line_range is (start, end) where start may be -1 for first line
        assert it.line_range is not None
        assert len(it.line_range) == 2

    def test_line_range_with_continuation(self):
        """Test line_range with continuation"""
        content = "line1\\\ncontinued\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        next(it)
        # line_range is (start, end) where start may be -1 for first line
        assert it.line_range is not None
        assert len(it.line_range) == 2

    def test_colnrs(self):
        """Test colnrs property"""
        content = "line1\n  line2\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        next(it)
        assert it.colnrs is not None
        
        next(it)
        assert len(it.colnrs) >= 1

    def test_starts(self):
        """Test starts property"""
        content = "line1\nline2\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        next(it)
        assert it.starts is not None
        assert len(it.starts) >= 1

    def test_empty_file(self):
        """Test empty file"""
        content = ""
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        with pytest.raises(StopIteration):
            next(it)

    def test_whitespace_handling(self):
        """Test leading whitespace is stripped"""
        content = "  line1\n\tline2\n"
        fhandle = io.StringIO(content)
        it = ContinuationLineIterator(fhandle)
        
        lines = list(it)
        assert lines[0] == "line1"
        assert lines[1] == "line2"


class TestMultiFileLineIterator:
    """Test MultiFileLineIterator class"""

    def test_single_file(self):
        """Test with single file"""
        content = "line1\nline2\n"
        fhandle = io.StringIO(content)
        it = MultiFileLineIterator()
        it.add_file(fhandle)
        
        lines = list(it)
        assert len(lines) == 2
        assert lines[0] == "line1"
        assert lines[1] == "line2"

    def test_multiple_files(self):
        """Test with multiple files"""
        content1 = "file1_line1\n"
        content2 = "file2_line1\n"
        fhandle1 = io.StringIO(content1)
        fhandle2 = io.StringIO(content2)
        it = MultiFileLineIterator()
        it.add_file(fhandle1)
        it.add_file(fhandle2)
        
        lines = list(it)
        assert len(lines) == 2
        assert lines[0] == "file2_line1"
        assert lines[1] == "file1_line1"

    def test_line_range(self):
        """Test line_range property"""
        content = "line1\nline2\n"
        fhandle = io.StringIO(content)
        it = MultiFileLineIterator()
        it.add_file(fhandle)
        
        next(it)
        # line_range returns a tuple
        assert it.line_range is not None
        assert len(it.line_range) == 2

    def test_empty_file_list(self):
        """Test with empty file list"""
        it = MultiFileLineIterator()
        
        with pytest.raises(StopIteration):
            next(it)


class TestLineContinuationError:
    """Test LineContinuationError exception"""

    def test_exception_creation(self):
        """Test creating the exception"""
        exc = LineContinuationError("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)
