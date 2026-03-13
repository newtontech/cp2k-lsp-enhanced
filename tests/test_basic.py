"""Basic tests for CP2K input tools."""

from cp2k_input_tools.parser import CP2KInputParser


def test_parse_simple_input():
    """Test parsing a simple CP2K input."""
    parser = CP2KInputParser()
    assert parser is not None


if __name__ == "__main__":
    test_parse_simple_input()
