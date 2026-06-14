"""Tests for CP2K input file formatter."""


from cp2k_input_tools.formatter import format_document, format_range


def _apply_edits(text, edits):
    """Apply TextEdit list to text and return result."""
    if not edits:
        return text
    for edit in edits:
        start = edit.range.start
        end = edit.range.end
        lines = text.split('\n')
        # For full document edits (start=0,0 to end=last,0), replace entire text
        if start.line == 0 and end.line >= len(lines):
            return edit.new_text
        # For range edits, replace the specific lines
        if start.line < len(lines):
            before = lines[:start.line]
            after = lines[end.line:] if end.line < len(lines) else []
            new_lines = edit.new_text.split('\n')
            return '\n'.join(before + new_lines + after)
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
        lines = result.split('\n')
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
        lines = result.split('\n')
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


# =============================================================================
# Comment Preservation Tests
# =============================================================================


class TestCommentPreservation:
    """Test that comments are preserved during formatting."""

    def test_standalone_comment_preserved(self):
        text = """&GLOBAL
  ! This is a comment
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! This is a comment" in result

    def test_hash_comment_preserved(self):
        text = """&GLOBAL
  # Hash comment
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "# Hash comment" in result

    def test_inline_comment_preserved(self):
        text = """&GLOBAL
  PROJECT test ! inline comment
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! inline comment" in result

    def test_comment_between_keywords_preserved(self):
        text = """&GLOBAL
  PROJECT test
  ! Separate sections
  RUN_TYPE ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! Separate sections" in result

    def test_comment_after_section_start_preserved(self):
        text = """&GLOBAL
  ! Section-level comment
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! Section-level comment" in result


# =============================================================================
# Preprocessor Directive Tests
# =============================================================================


class TestPreprocessorDirectives:
    """Test that preprocessor directives are preserved."""

    def test_set_directive_preserved(self):
        text = """@SET MY_VAR value
&GLOBAL
  PROJECT ${MY_VAR}
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "@SET MY_VAR value" in result

    def test_include_directive_preserved(self):
        text = """@INCLUDE common_settings.inc
&GLOBAL
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "@INCLUDE common_settings.inc" in result

    def test_if_directive_preserved(self):
        text = """@IF ${DO_DFT}
&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
  &END DFT
&END FORCE_EVAL
@ENDIF
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "@IF ${DO_DFT}" in result
        assert "@ENDIF" in result

    def test_directive_not_reformatted(self):
        text = """@SET   MY_VAR   value
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "@SET   MY_VAR   value" in result


# =============================================================================
# Minimal TextEdit Tests
# =============================================================================


class TestMinimalTextEdits:
    """Test that formatting produces minimal diff-based TextEdits."""

    def test_no_edits_when_already_formatted(self):
        text = """&GLOBAL
  PROJECT test
  RUN_TYPE ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) == 0

    def test_single_edit_for_single_change(self):
        text = """&GLOBAL
project test
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) == 1

    def test_multiple_edits_for_scattered_changes(self):
        text = """&GLOBAL
project test
run_type ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) <= 2

    def test_edit_range_covers_changed_lines(self):
        text = """&GLOBAL
project test
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) >= 1
        for edit in edits:
            assert edit.range.start.line <= edit.range.end.line

    def test_full_replacement_mode(self):
        text = """&GLOBAL
project test
&END GLOBAL
"""
        edits = format_document(text, minimal_edits=False)
        assert len(edits) == 1
        assert edits[0].range.start.line == 0


# =============================================================================
# Refuse Unsafe Tests
# =============================================================================


class TestRefuseUnsafe:
    """Test that formatting refuses unsafe constructs."""

    def test_refuses_with_directives(self):
        text = """@SET X value
&GLOBAL
  PROJECT ${X}
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) == 0

    def test_safe_without_directives(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        assert len(edits) == 0


# =============================================================================
# Blank Line Handling Tests
# =============================================================================


class TestBlankLineHandling:
    """Test blank line handling in formatting."""

    def test_single_blank_line_preserved(self):
        text = """&GLOBAL
  PROJECT test

  RUN_TYPE ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "\n  PROJECT test\n\n  RUN_TYPE ENERGY" in result

    def test_multiple_blank_lines_collapsed(self):
        text = """&GLOBAL
  PROJECT test



  RUN_TYPE ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "\n\n\n" not in result

    def test_blank_lines_between_sections(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "&END GLOBAL" in result
        assert "&FORCE_EVAL" in result


# =============================================================================
# Indentation Tests
# =============================================================================


class TestIndentation:
    """Test indentation handling in formatting."""

    def test_single_level_indentation(self):
        text = """&GLOBAL
PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "  PROJECT" in result

    def test_double_level_indentation(self):
        text = """&FORCE_EVAL
  &DFT
CUTOFF 400
  &END DFT
&END FORCE_EVAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "    CUTOFF" in result

    def test_custom_indent(self):
        text = """&GLOBAL
PROJECT test
&END GLOBAL
"""
        edits = format_document(text, indent_str="    ")
        result = _apply_edits(text, edits)
        assert "    PROJECT" in result


# =============================================================================
# Keyword Normalization Tests
# =============================================================================


class TestKeywordNormalization:
    """Test keyword casing normalization."""

    def test_lowercase_keyword_uppercased(self):
        text = """&GLOBAL
  project test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "PROJECT" in result

    def test_mixed_case_keyword_uppercased(self):
        text = """&GLOBAL
  Run_Type ENERGY
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "RUN_TYPE" in result

    def test_section_name_uppercased(self):
        text = """&global
  PROJECT test
&end global
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "&GLOBAL" in result
        assert "&END GLOBAL" in result


# =============================================================================
# Idempotency Tests
# =============================================================================


class TestIdempotency:
    """Test that formatting is idempotent."""

    def test_single_format_idempotent(self):
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

    def test_idempotent_with_comments(self):
        text = """&GLOBAL
  ! Comment
  PROJECT test
&END GLOBAL
"""
        edits1 = format_document(text)
        result1 = _apply_edits(text, edits1)
        edits2 = format_document(result1)
        result2 = _apply_edits(result1, edits2)
        assert result1 == result2


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases in formatting."""

    def test_empty_document(self):
        edits = format_document("")
        assert isinstance(edits, list)

    def test_only_comments(self):
        text = """! Comment 1
# Comment 2
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert "! Comment 1" in result
        assert "# Comment 2" in result

    def test_only_blank_lines(self):
        text = "\n\n\n"
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert result is not None

    def test_trailing_newline_preserved(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL
"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert result.endswith("\n")

    def test_no_trailing_newline(self):
        text = """&GLOBAL
  PROJECT test
&END GLOBAL"""
        edits = format_document(text)
        result = _apply_edits(text, edits)
        assert not result.endswith("\n\n")
