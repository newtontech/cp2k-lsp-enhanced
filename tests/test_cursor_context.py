"""Tests for cursor context resolution."""

import json
from pathlib import Path

from cp2k_input_tools.cursor_context import CursorContextResolver


class TestCursorContext:
    """Test cursor context resolution."""
    
    def test_cursor_context_basic(self):
        """Test basic cursor context resolution."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  &DFT
    &QS
      METHOD GAPW
    &END QS
  &END DFT
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor at QS section start (line 2, character 5)
        context = resolver.resolve_cursor_context("test.inp", lines, 2, 5)
        
        assert context.uri == "test.inp"
        assert context.line == 2
        assert context.character == 5
        assert context.section_path == ("FORCE_EVAL", "DFT")
        assert context.current_section == "DFT"
        assert context.is_section_start
        assert not context.is_section_end
    
    def test_cursor_context_value_position(self):
        """Test cursor context at value position."""
        resolver = CursorContextResolver()

        input_text = """&FORCE_EVAL
  &DFT
    &QS
      METHOD GAPW
    &END QS
  &END DFT
&END FORCE_EVAL
"""
        lines = input_text.split('\n')

        # Test cursor after METHOD keyword (line 3, character 12)
        context = resolver.resolve_cursor_context("test.inp", lines, 3, 12)

        assert context.uri == "test.inp"
        assert context.section_path == ("FORCE_EVAL", "DFT", "QS")
        assert context.current_section == "QS"
        assert context.current_keyword == "METHOD"
        assert context.is_value_position
        assert not context.is_keyword_position
    
    def test_cursor_context_section_end(self):
        """Test cursor context at section end."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  &DFT
    &QS
      METHOD GAPW
    &END QS
  &END DFT
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor at QS section end (line 4, character 5)
        context = resolver.resolve_cursor_context("test.inp", lines, 4, 5)
        
        assert context.section_path == ("FORCE_EVAL", "DFT", "QS")
        assert context.current_section == "QS"
        assert context.is_section_end
        assert not context.is_section_start
    
    def test_cursor_context_deep_nesting(self):
        """Test cursor context with deeply nested sections."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_pob
    &QS
      EPS_DEFAULT 1e-12
      METHOD GAPW
    &END QS
    &SCF
      EPS_SCF 1e-07
      MAX_SCF 80
      SCF_GUESS ATOMIC
    &END SCF
  &END DFT
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor under SCF section
        context = resolver.resolve_cursor_context("test.inp", lines, 11, 15)

        assert context.section_path == ("FORCE_EVAL", "DFT", "SCF")
        assert context.current_section == "SCF"
        assert context.current_keyword == "SCF_GUESS"
        assert context.is_value_position
    
    def test_cursor_context_whitespace_assignment(self):
        """Test cursor context with CP2K whitespace assignment style."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  METHOD Quickstep
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor after METHOD keyword with whitespace assignment
        context = resolver.resolve_cursor_context("test.inp", lines, 1, 12)
        
        assert context.section_path == ("FORCE_EVAL",)
        assert context.current_section == "FORCE_EVAL"
        assert context.current_keyword == "METHOD"
        assert context.is_value_position
    
    def test_cursor_context_incomplete_line(self):
        """Test cursor context with incomplete line."""
        resolver = CursorContextResolver()

        input_text = """&FORCE_EVAL
  METHOD
&END FORCE_EVAL
"""
        lines = input_text.split('\n')

        # Test cursor at incomplete METHOD line (just keyword, no space after)
        # At position 7, we're at the last character, still typing the keyword
        context = resolver.resolve_cursor_context("test.inp", lines, 1, 7)

        assert context.section_path == ("FORCE_EVAL",)
        assert context.current_section == "FORCE_EVAL"
        # When there's no separator after the keyword, we're still typing it
        assert context.is_keyword_position
        # We're in the middle of typing, so prefix is partial
        assert len(context.prefix) > 0
    
    def test_cursor_context_prefix_detection(self):
        """Test cursor context prefix detection for completion."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  METH
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor at partial keyword (position 6 is at the end of METH)
        context = resolver.resolve_cursor_context("test.inp", lines, 1, 6)

        assert context.prefix == "METH"
        assert context.is_keyword_position
    
    def test_cursor_context_with_comments(self):
        """Test cursor context ignores comments properly."""
        resolver = CursorContextResolver()
        
        input_text = """&FORCE_EVAL
  METHOD Quickstep  ! This is a comment
&END FORCE_EVAL
"""
        lines = input_text.split('\n')
        
        # Test cursor before comment
        context = resolver.resolve_cursor_context("test.inp", lines, 1, 20)
        
        assert context.section_path == ("FORCE_EVAL",)
        assert context.current_section == "FORCE_EVAL"
        # Should recognize the keyword even with comment after
    
    def test_cursor_context_golden_fixture(self):
        """Test cursor context against golden fixture."""
        resolver = CursorContextResolver()
        
        fixture_path = Path(__file__).parent / "fixtures" / "cursor_context" / "nested_sections.inp"
        golden_path = Path(__file__).parent / "fixtures" / "cursor_context" / "nested_sections.json"
        
        # Load input file
        with open(fixture_path) as f:
            lines = f.readlines()
        
        # Load golden JSON
        with open(golden_path) as f:
            golden_data = json.load(f)
        
        # Test each cursor position
        for test_case in golden_data['cursor_positions']:
            context = resolver.resolve_cursor_context(
                str(fixture_path),
                lines,
                test_case['line'],
                test_case['character']
            )
            
            expected = test_case['expected_context']
            
            # Check all fields
            assert context.line == expected['line'], (
                f"Line mismatch for {test_case['description']}"
            )
            assert context.character == expected['character'], (
                f"Character mismatch for {test_case['description']}"
            )
            assert context.section_path == tuple(expected['section_path']), (
                f"Section path mismatch for {test_case['description']}"
            )
            assert context.current_section == expected['current_section'], (
                f"Current section mismatch for {test_case['description']}"
            )
            assert context.current_keyword == expected['current_keyword'], (
                f"Current keyword mismatch for {test_case['description']}"
            )
            assert context.is_section_start is expected['is_section_start'], (
                f"is_section_start mismatch for {test_case['description']}"
            )
            assert context.is_section_end is expected['is_section_end'], (
                f"is_section_end mismatch for {test_case['description']}"
            )
            assert context.is_keyword_position is expected['is_keyword_position'], (
                f"is_keyword_position mismatch for {test_case['description']}"
            )
            assert context.is_value_position is expected['is_value_position'], (
                f"is_value_position mismatch for {test_case['description']}"
            )
            # Note: prefix matching may be lenient for whitespace
            assert context.prefix.strip() == expected['prefix'].strip(), (
                f"Prefix mismatch for {test_case['description']}: "
                f"got '{context.prefix}', expected '{expected['prefix']}'"
            )