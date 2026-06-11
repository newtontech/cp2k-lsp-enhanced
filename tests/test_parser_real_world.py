import pytest

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.parser_errors import ParserError
from cp2k_input_tools.tokenizer import TokenizerError

from . import TEST_DIR

REAL_WORLD_INPUT_DIR = TEST_DIR.joinpath("inputs/real_world")


def test_real_world_cp2k_inputs_parse():
    input_files = sorted(REAL_WORLD_INPUT_DIR.glob("*.inp"))

    assert len(input_files) >= 3

    for input_file in input_files:
        parser = CP2KInputParser(DEFAULT_CP2K_INPUT_XML, base_dir=REAL_WORLD_INPUT_DIR)

        try:
            with input_file.open() as fhandle:
                tree = parser.parse(fhandle)
        except (ParserError, TokenizerError) as exc:
            pytest.fail(f"{input_file.name} failed to parse: {exc}")

        assert tree, f"{input_file.name} produced an empty parse tree"
