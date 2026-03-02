import io

from cp2k_input_tools import DEFAULT_CP2K_INPUT_XML
from cp2k_input_tools.generator import CP2KInputGenerator
from cp2k_input_tools.keyword_helpers import IntegerRange
from cp2k_input_tools.parser import CP2KInputParserSimplified


def test_issue_72_integer_range_values_are_parsed():
    """Regression test for https://github.com/cp2k/cp2k-input-tools/issues/72."""

    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    tree = parser.parse(
        io.StringIO(
            """
            &GLOBAL
              RUN_TYPE ENERGY
            &END GLOBAL
            &FORCE_EVAL
              &SUBSYS
                &TOPOLOGY
                  &GENERATE
                    &ISOLATED_ATOMS
                      LIST 1..5 8 10..12
                    &END ISOLATED_ATOMS
                  &END GENERATE
                &END TOPOLOGY
              &END SUBSYS
            &END FORCE_EVAL
            """
        )
    )

    assert tree["force_eval"]["subsys"]["topology"]["generate"]["isolated_atoms"]["list"] == (
        IntegerRange(1, 5),
        8,
        IntegerRange(10, 12),
    )


def test_issue_72_generator_preserves_integer_range_tokens():
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    generator = CP2KInputGenerator(DEFAULT_CP2K_INPUT_XML)

    tree = parser.parse(
        io.StringIO(
            """
            &GLOBAL
              RUN_TYPE ENERGY
            &END GLOBAL
            &FORCE_EVAL
              &SUBSYS
                &TOPOLOGY
                  &GENERATE
                    &ISOLATED_ATOMS
                      LIST 2..4 7
                    &END ISOLATED_ATOMS
                  &END GENERATE
                &END TOPOLOGY
              &END SUBSYS
            &END FORCE_EVAL
            """
        )
    )

    lines = list(generator.line_iter(tree))
    assert any("LIST 2..4 7" in line for line in lines)


def test_issue_111_quotes_inside_comment_do_not_crash_tokenizer():
    """Regression test for https://github.com/cp2k/cp2k-input-tools/issues/111."""

    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    tree = parser.parse(
        io.StringIO(
            """
            &GLOBAL
              PROJECT demo ! comment contains "quotes"
              RUN_TYPE ENERGY
            &END GLOBAL
            &FORCE_EVAL
            &END FORCE_EVAL
            """
        )
    )

    assert tree["global"]["project"] == "demo"


def test_issue_111_lone_keyword_with_inline_comment_uses_lone_value():
    parser = CP2KInputParserSimplified(DEFAULT_CP2K_INPUT_XML)
    tree = parser.parse(
        io.StringIO(
            """
            &GLOBAL
              RUN_TYPE ENERGY
            &END GLOBAL
            &FORCE_EVAL
              &SUBSYS
                &COLVAR
                  &XYZ_DIAG
                    ATOM 1
                    COMPONENT X
                    ABSOLUTE_POSITION ! use the instant position
                  &END XYZ_DIAG
                &END COLVAR
              &END SUBSYS
            &END FORCE_EVAL
            """
        )
    )

    assert tree["force_eval"]["subsys"]["colvar"]["xyz_diag"]["absolute_position"] is True
