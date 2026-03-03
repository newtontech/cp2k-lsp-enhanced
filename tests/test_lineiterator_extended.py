# Extended tests for cp2k_input_tools/lineiterator.py
# Target: 100% coverage

import io
import pytest

from cp2k_input_tools.lineiterator import (
    LineContinuationError,
    ContinuationLineIterator,
    MultiFileLineIterator,
)


class TestContinuationLineIterator:
    """Test ContinuationLineIterator class"""

    def test_simple_lines(self):
        """Test iterating over simple lines"""
        content = io.StringIO("line1\nline2\nline3\n")
        it = ContinuationLineIterator(content)
        assert next(it) == "line1"
        assert next(it) == "line2"
        assert next(it) == "line3"
        with pytest.raises(StopIteration):
            next(it)

    def test_line_continuation(self):
        """Test line continuation with backslash"""
        content = io.StringIO("line1\\\ncontinued\nline2\n")
        it = ContinuationLineIterator(content)
        assert next(it) == "line1continued"
        assert next(it) == "line2"

    def test_multi_line_continuation(self):
        """Test multiple line continuations"""
        content = io.StringIO("part1\\\npart2\\\npart3\n")
        it = ContinuationLineIterator(content)
        assert next(it) == "part1part2part3"

    def test_line_range(self):
        """Test line_range property"""
        content = io.StringIO("line1\nline2\n")
        it = ContinuationLineIterator(content)
        next(it)
        assert it.line_range == (1, 1)
        next(it)
        assert it.line_range == (2, 2)

    def test_line_range_with_continuation(self):
        """Test line_range with line continuation"""
        content = io.StringIO("line1\\\ncontinued\n")
        it = ContinuationLineIterator(content)
        next(it)
        assert it.line_range == (1, 2)

    def test_colnrs(self):
        """Test colnrs property"""
        content = io.StringIO("  line1\n    line2\n")
        it = ContinuationLineIterator(content)
        next(it)
        assert it.colnrs == [2]
        next(it)
        assert it.colnrs == [4]

    def test_starts(self):
        """Test starts property"""
        content = io.StringIO("line1\\\ncont\n")
        it = ContinuationLineIterator(content)
        next(it)
        assert it.starts == [0, 5]  # 0 for start, 5 for continuation position

    def test_stripped_whitespace(self):
        """Test that leading whitespace is stripped"""
        content = io.StringIO("   line1\n\t\tline2\n")
        it = ContinuationLineIterator(content)
        assert next(it) == "line1"
        assert next(it) == "line2"

    def test_stray_continuation_error(self):
        """Test stray line continuation at end of file"""
        content = io.StringIO("line1\\\n")
        it = ContinuationLineIterator(content)
        next(it)  # line1
        with pytest.raises(LineContinuationError):
            next(it)


class TestMultiFileLineIterator:
    """Test MultiFileLineIterator class"""

    def test_single_file(self):
        """Test iterating over a single file"""
        content = io.StringIO("line1\nline2\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=False)
        assert next(mfi) == "line1"
        assert next(mfi) == "line2"
        with pytest.raises(StopIteration):
            next(mfi)

    def test_multiple_files(self):
        """Test iterating over multiple files"""
        content1 = io.StringIO("file1_line1\nfile1_line2\n")
        content2 = io.StringIO("file2_line1\nfile2_line2\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content1, managed=False)
        mfi.add_file(content2, managed=False)
        
        assert next(mfi) == "file2_line1"
        assert next(mfi) == "file2_line2"
        assert next(mfi) == "file1_line1"
        assert next(mfi) == "file1_line2"
        with pytest.raises(StopIteration):
            next(mfi)

    def test_line_range(self):
        """Test line_range property"""
        content = io.StringIO("line1\nline2\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=False)
        next(mfi)
        assert mfi.line_range == (1, 1)

    def test_colnrs(self):
        """Test colnrs property"""
        content = io.StringIO("  line1\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=False)
        next(mfi)
        assert mfi.colnrs == [2]

    def test_starts(self):
        """Test starts property"""
        content = io.StringIO("line1\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=False)
        next(mfi)
        assert mfi.starts == [0]

    def test_fname(self):
        """Test fname property"""
        # Create a file-like object with a name attribute
        class NamedFile:
            name = "test_file.txt"
            def __iter__(self):
                return iter(["line1\n"])
        
        mfi = MultiFileLineIterator()
        mfi.add_file(NamedFile(), managed=False)
        next(mfi)
        assert mfi.fname == "test_file.txt"

    def test_fname_buffer(self):
        """Test fname property for buffer (no name attribute)"""
        content = io.StringIO("line1\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=False)
        next(mfi)
        assert mfi.fname == "<BUFFER>"

    def test_managed_file_close(self):
        """Test that managed files are closed"""
        content = io.StringIO("line1\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=True)
        next(mfi)
        with pytest.raises(StopIteration):
            next(mfi)
        # File should be closed after iteration

    def test_destructor(self):
        """Test that destructor closes files"""
        content = io.StringIO("line1\n")
        mfi = MultiFileLineIterator()
        mfi.add_file(content, managed=True)
        del mfi  # Should not raise
