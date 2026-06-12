"""Tests for CP2K input file formatter."""

from cp2k_input_tools.formatter import format_document, format_range


def _apply_edits(text, edits):
    """Apply TextEdit list to text and return result."""
    if not edits:
        return text
    for edit in edits:
        start = edit.range.start
        end = edit.range.end
        lines = text.split("\n")
        # For full document edits (start=0,0 to end=last,0), replace entire text
        if start.line == 0 and end.line >= len(lines):
            return edit.new_text
        # For range edits, replace the specific lines
        if start.line < len(lines):
            before = lines[: start.line]
            after = lines[end.line :] if end.line < len(lines) else []
            new_lines = edit.new_text.split("\n")
            return "\n".join(before + new_lines + after)
    return text


class TestFormatDocument:
    """Tests for full document formatting."""

    def test_basic_section_indentation(self):
        text = """&GLOBAL
PROJECT test
RUN_TYPE ENERGY
&END GLOBAL
&FORCE_EVAL
METHOD QS
&DFT
BASIS_SET_FILE_NAME BASIS_MOLOPT
&END DFT
&END FORCE_EVAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        lines = result.split("\n")
        # Lines: 0=&GLOBAL, 1=  PROJECT, 2=  RUN_TYPE, 3=&END GLOBAL,
        #        4=&FORCE_EVAL, 5=  METHOD, 6=  &DFT, 7=    BASIS_SET, ...
        assert lines[1].startswith("  ")  # PROJECT indented under GLOBAL
        assert lines[5].startswith("  ")  # METHOD indented under FORCE_EVAL
        assert lines[6].startswith("  &DFT")  # DFT nested in FORCE_EVAL
        assert lines[7].startswith("    BASIS_SET_FILE_NAME")  # Double nested

    def test_section_end_alignment(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "&END GLOBAL" in result

    def test_comments_preserved(self):
        text = """! This is a comment
&GLOBAL
  # Another comment
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! This is a comment" in result
        assert "# Another comment" in result

    def test_inline_comments_preserved(self):
        text = """&GLOBAL
  PROJECT test ! project name
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "!" in result

    def test_directives_preserved(self):
        text = """@SET MY_VAR value
&GLOBAL
  PROJECT ${MY_VAR}
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "@SET MY_VAR value" in result

    def test_keyword_uppercase(self):
        text = """&GLOBAL
  project test
  run_type ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "PROJECT test" in result
        assert "RUN_TYPE ENERGY" in result

    def test_idempotent(self):
        text = """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL
"""
        edits1 = format_document(text)
        result1 = _apply_edits(text, edits1)
        edits2 = format_document(result1)
        result2 = _apply_edits(result1, edits2)
        assert result1 == result2

    def test_blank_lines_collapsed(self):
        text = """&GLOBAL


  PROJECT test


&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        # Should not have consecutive blank lines
        assert "\n\n\n" not in result

    def test_deeply_nested_sections(self):
        text = """&FORCE_EVAL
&DFT
&MGRID
CUTOFF 400
&END MGRID
&END DFT
&END FORCE_EVAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        lines = result.split("\n")
        # Lines: 0=&FORCE_EVAL, 1=  &DFT, 2=    &MGRID, 3=      CUTOFF, ...
        assert lines[3].startswith("      CUTOFF")  # Triple nested

    def test_invalid_document_no_crash(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL
&INVALID_SECTION
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert result  # Should not crash


class TestFormatRange:
    """Tests for range formatting."""

    def test_format_single_section(self):
        text = """&GLOBAL
PROJECT test
RUN_TYPE ENERGY
&END GLOBAL
"""
        edits = format_range(text, 0, 4)
        result = _apply_edits(text, edits)
        assert "  PROJECT" in result


def test_format_empty():
    edits = format_document("")
    assert len(edits) == 1
