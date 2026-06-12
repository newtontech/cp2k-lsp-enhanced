import collections
import pathlib
import re
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import pint

from .parser_errors import InvalidParameterError
from .tokenizer import COMMENT_CHARS, tokenize

UREG = pint.UnitRegistry()
UREG.load_definitions(str(pathlib.Path(__file__).resolve().parent.joinpath("pint_units.txt")))


# Built-in registry of deprecated CP2K keywords mapped to their replacements.
# Since the upstream CP2K XML schema does not include deprecation markers,
# this registry captures known deprecations from CP2K release notes and docs.
DEPRECATED_KEYWORDS: dict[str, str] = {
    # CP2K 2024.1 deprecated keywords
    "MOTION/PRINT/TRAJECTORY::FORCE_EVAL": None,
    "DFT/SCF::BROYDEN_MIXING_NEW": "Use MIXING/TYPE BROYDEN_MIXING instead",
    "DFT/QS::KP_RI_EXTENSION_FACTOR": None,
    "FORCE_EVAL::SINGLE_PRECISION_MATRICES": None,
    "FORCE_EVAL/SUBSYS/TOPOLOGY::COORD_FILE_NAME": "Use COORD_FILE_NAME in SUBSYS directly",
    # CP2K 2023.x deprecated keywords
    "DFT/SCF::OT_MINIMIZER": "Use OT/MINIMIZER instead",
    "DFT/SCF::OT_ENERGIES": None,
    "DFT/SCF::DIAG_METHOD": "Use DIAGONALIZATION/METHOD instead",
}

# Built-in registry of deprecated CP2K sections mapped to their replacements.
DEPRECATED_SECTIONS: dict[str, str] = {
    "FORCE_EVAL::FIST": "Use FORCE_EVAL METHOD=FIST instead",
    "DFT/SCF::BROYDEN": "Use MIXING section with TYPE BROYDEN_MIXING instead",
}


class DeprecatedKeywordWarning(UserWarning):
    """Warning emitted when a deprecated keyword is encountered during parsing."""

    def __init__(self, keyword: str, replacement: str | None, section: str):
        if replacement:
            msg = f"Keyword '{keyword}' is deprecated in section '{section}'. Use '{replacement}' instead."
        else:
            msg = f"Keyword '{keyword}' is deprecated in section '{section}' and will be removed in a future CP2K version."
        super().__init__(msg)


class DeprecatedSectionWarning(UserWarning):
    """Warning emitted when a deprecated section is encountered during parsing."""

    def __init__(self, section: str, replacement: str | None, parent_section: str):
        if replacement:
            msg = f"Section '{section}' is deprecated under '{parent_section}'. Use '{replacement}' instead."
        else:
            msg = f"Section '{section}' under '{parent_section}' is deprecated and will be removed in a future CP2K version."
        super().__init__(msg)


def register_deprecated(keyword: str, section: str, replacement: str | None = None):
    """Register a keyword as deprecated."""
    DEPRECATED_KEYWORDS[f"{section.upper()}::{keyword.upper()}"] = replacement


def check_deprecated(keyword_name: str, section_name: str) -> bool:
    """Check if a keyword is deprecated and emit a warning. Returns True if deprecated."""
    key = f"{section_name.upper()}::{keyword_name.upper()}"
    replacement = DEPRECATED_KEYWORDS.get(key)
    if replacement is not None or key in DEPRECATED_KEYWORDS:
        warnings.warn(DeprecatedKeywordWarning(keyword_name, replacement, section_name), stacklevel=4)
        return True
    return False


def register_deprecated_section(section: str, parent_section: str, replacement: str | None = None):
    """Register a section as deprecated."""
    DEPRECATED_SECTIONS[f"{parent_section.upper()}::{section.upper()}"] = replacement


def check_deprecated_section(section_name: str, parent_section: str) -> bool:
    """Check if a section is deprecated and emit a warning. Returns True if deprecated."""
    key = f"{parent_section.upper()}::{section_name.upper()}"
    replacement = DEPRECATED_SECTIONS.get(key)
    if replacement is not None or key in DEPRECATED_SECTIONS:
        warnings.warn(DeprecatedSectionWarning(section_name, replacement, parent_section), stacklevel=4)
        return True
    return False


def kw_converter_bool(string):
    string = string.upper()

    if string in ("0", "F", ".F.", "FALSE", ".FALSE.", "N", "NO", "OFF"):
        return False

    if string in ("1", "T", ".T.", "TRUE", ".TRUE.", "Y", "YES", "ON"):
        return True

    raise InvalidParameterError(f"invalid value given for a boolean: '{string}'")


def kw_converter_str(string):
    return string.strip("'\"")


FORTRAN_REAL = re.compile(r"(\d*\.\d+)[dD]([-+]?\d+)")

RANGE_PATTERN = re.compile(r"^(-?\d+)\.\.(-?\d+)$")
RANGE_PATTERN_REAL = re.compile(r"^(-?[\d.]+(?:[eE][-+]?\d+)?)\.\.(-?[\d.]+(?:[eE][-+]?\d+)?)$")


def kw_converter_float(string):
    """convert a given string to a Python float

    :param string: string with the float, can be in Fortran scientific notation or as fraction
    """
    string = FORTRAN_REAL.sub(r"\1e\2", string)

    if "/" in string:
        return float(Fraction(string))

    return float(string)


def kw_converter_keyword(string, allowed_values):
    string = string.upper()

    if string in allowed_values:
        return string

    raise InvalidParameterError(f"invalid keyword '{string}'")


KW_VALUE_CONVERTERS = {
    "logical": kw_converter_bool,
    "integer": int,
    "real": kw_converter_float,
    "word": kw_converter_str,
    "string": kw_converter_str,
}

KWDataType = collections.namedtuple("KWDataType", ["type", "n_var", "parser"])


def get_datatype(kw_node):
    dt = kw_node.find("./DATA_TYPE")
    kind = dt.get("kind")

    if kind == "keyword":
        # the keywords parser needs the list of valid keywords for verification
        valid_keywords = [e.text for e in dt.iterfind(".//NAME")]
        parser = lambda v: kw_converter_keyword(v, valid_keywords)  # noqa
    else:
        parser = KW_VALUE_CONVERTERS[kind]

    return KWDataType(kind, int(dt.find("./N_VAR").text), parser)


@dataclass
class Keyword:
    name: str
    values: Any
    repeats: bool
    node: ET.Element

    @staticmethod
    def from_string(kw_node, vstring, key_trafo=str):
        datatype = get_datatype(kw_node)

        # for a string datatype, no tokenization shall be done
        if datatype.type == "string":
            if vstring.startswith(("'", '"')):
                # if the content is actually a string, employ the tokenizer do correctly determine the end of it
                tokens = tokenize(vstring)
            else:
                tokens = [vstring.rstrip()]  # strip trailing whitespace
            # in case of no value, this will lead to an empty string, which is intentional
            # since we can't distinguish between an empty string and a lone keyword for a string datatype
            # -> inline comments for strings which are not escaped will be treated as part of the string, reproducing CP2K-behaviour
        else:
            tokens = tokenize(vstring)

        lone_keyword_value = None
        try:
            lone_keyword_value = tokenize(kw_node.find("./LONE_KEYWORD_VALUE").text)
        except AttributeError:
            pass

        if not tokens:
            if not lone_keyword_value:
                raise InvalidParameterError("keyword expects at least one value")

            tokens = lone_keyword_value

        default_unit = None
        is_internal_cp2k = False
        try:
            default_unit = kw_node.find("./DEFAULT_UNIT").text
        except AttributeError:
            pass

        # For internal_cp2k units, we cannot convert to/from the abstract unit.
        # Store values as-is when no explicit unit is given; when an explicit unit
        # is given, store the value with the unit as a string to preserve information.
        if default_unit and default_unit == "internal_cp2k":
            is_internal_cp2k = True
            default_unit = None

        if default_unit:
            default_unit = UREG.parse_expression(default_unit)

        current_unit = default_unit

        values = []

        for token in tokens:
            if token.startswith("["):
                if is_internal_cp2k:
                    # We can't convert to/from internal_cp2k. Store subsequent
                    # values as "[unit] value" strings to preserve the unit info.
                    current_unit = token.strip("[]")
                    continue
                if not default_unit:
                    raise InvalidParameterError(
                        "unit specified for value in keyword, but no default unit available or default unit is 'internal_cp2k'"
                    )
                current_unit = UREG.parse_expression(token.strip("[]"), case_sensitive=False)
                continue

            if token.startswith(COMMENT_CHARS):
                assert token == tokens[-1], "found inline comment which is not the last token"
                continue  # ignore inline comments

            # For internal_cp2k with explicit unit, store as string with unit
            if is_internal_cp2k and current_unit and isinstance(current_unit, str):
                values += [f"[{current_unit}] {token}"]
                continue

            # Expand X..Y ranges for integer and real types (issue #72)
            range_values = None
            if datatype.type == "integer":
                range_match = RANGE_PATTERN.match(token)
                if range_match:
                    start_val = int(range_match.group(1))
                    end_val = int(range_match.group(2))
                    range_values = list(range(start_val, end_val + 1))
            elif datatype.type == "real":
                range_match = RANGE_PATTERN_REAL.match(token)
                if range_match:
                    start_val = kw_converter_float(range_match.group(1))
                    end_val = kw_converter_float(range_match.group(2))
                    # For real ranges, generate values with step 1.0
                    n_steps = int(end_val - start_val)
                    if n_steps >= 0:
                        range_values = [start_val + i for i in range(n_steps + 1)]

            if range_values is not None:
                values += range_values
                continue

            value = datatype.parser(token)

            if datatype.type == "keyword":
                # keywords are also matched case insensitive, apply the same rules as for the keys
                value = key_trafo(value)

            if current_unit != default_unit:
                # interpret the given value in the specified unit, convert it and get the raw value
                value = (value * current_unit).to(default_unit).magnitude

            values += [value]

        if not values:
            raise InvalidParameterError("keyword expects at least one value, only a unit spec was given")

        if (datatype.n_var > 0) and (datatype.n_var != len(values)):
            raise InvalidParameterError(f"keyword expects exactly {datatype.n_var} values, {len(values)} were given")

        # simplify the value if only one is given/requested
        if len(values) == 1:
            values = values[0]
        else:
            values = tuple(values)

        key_name = kw_node.find("./NAME[@type='default']").text
        if key_name == "DEFAULT_KEYWORD":
            key_name = "*"

        return Keyword(key_name, values, True if kw_node.get("repeats") == "yes" else False, kw_node)
