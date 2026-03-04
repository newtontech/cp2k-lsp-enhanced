"""Unit tests for lineiterator module."""

import pytest
from io import StringIO
from cp2k_input_tools.lineiterator import (
    LineContinuationError,
    ContinuationLineIterator,
    MultiFileLineIterator,
)


class TestContinuationLineIterator:
    """Tests for ContinuationLineIterator class."""

    def test_simple_lines(self):
        """Test with simple lines."""
        fhandle = StringIO("line1\nline2\nline3")
        iterator = ContinuationLineIterator(fhandle)
        
        assert next(iterator) == "line1"
        assert next(iterator) == "line2"
        assert next(iterator) == "line3"
        
        with pytest.raises(StopIteration):
            next(iterator)

    def test_line_continuation(self):
        """Test with line continuation."""
        fhandle = StringIO("line1 \\\n  continuation\nline2")
        iterator = ContinuationLineIterator(fhandle)
        
        result = next(iterator)
        assert "line1" in result
        assert "continuation" in result

    def test_line_range_property(self):
        """Test line_range property."""
        fhandle = StringIO("line1\nline2")
        iterator = ContinuationLineIterator(fhandle)
        
        next(iterator)
        line_range = iterator.line_range
        assert isinstance(line_range, tuple)
        assert len(line_range) == 2

    def test_colnrs_property(self):
        """Test colnrs property."""
        fhandle = StringIO("  line1\n    line2")
        iterator = ContinuationLineIterator(fhandle)
        
        next(iterator)
        colnrs = iterator.colnrs
        assert isinstance(colnrs, list)

    def test_starts_property(self):
        """Test starts property."""
        fhandle = StringIO("line1\nline2")
        iterator = ContinuationLineIterator(fhandle)
        
        next(iterator)
        starts = iterator.starts
        assert isinstance(starts, list)

    def test_unterminated_continuation(self):
        """Test unterminated line continuation raises error at end."""
        fhandle = StringIO("line1 \\")
        iterator = ContinuationLineIterator(fhandle)
        
        # The error is raised when trying to iterate after a line ending with \
        # The first next() will try to find the continuation
        with pytest.raises(LineContinuationError):
            next(iterator)


class TestMultiFileLineIterator:
    """Tests for MultiFileLineIterator class."""

    def test_single_file(self):
        """Test with single file."""
        fhandle = StringIO("line1\nline2")
        iterator = MultiFileLineIterator()
        iterator.add_file(fhandle)
        
        assert next(iterator) == "line1"
        assert next(iterator) == "line2"
        
        with pytest.raises(StopIteration):
            next(iterator)

    def test_line_range_property(self):
        """Test line_range property."""
        fhandle = StringIO("line1\nline2")
        iterator = MultiFileLineIterator()
        iterator.add_file(fhandle)
        
        next(iterator)
        line_range = iterator.line_range
        assert isinstance(line_range, tuple)

    def test_colnrs_property(self):
        """Test colnrs property."""
        fhandle = StringIO("line1")
        iterator = MultiFileLineIterator()
        iterator.add_file(fhandle)
        
        next(iterator)
        colnrs = iterator.colnrs
        assert isinstance(colnrs, list)

    def test_fname_property(self):
        """Test fname property."""
        fhandle = StringIO("line1")
        fhandle.name = "test.inp"
        iterator = MultiFileLineIterator()
        iterator.add_file(fhandle)
        
        next(iterator)
        assert iterator.fname == "test.inp"

    def test_fname_buffer(self):
        """Test fname property with buffer."""
        fhandle = StringIO("line1")
        iterator = MultiFileLineIterator()
        iterator.add_file(fhandle)
        
        next(iterator)
        assert iterator.fname == "<BUFFER>"
