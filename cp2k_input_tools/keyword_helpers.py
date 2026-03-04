import collections
import pathlib
import re
import xml.etree.ElementTree as ET
import warnings
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple, Union

import pint

from .parser_errors import (
    DeprecatedKeywordWarning,
    InvalidParameterError,
    IntegerRangeError,
)
from .tokenizer import COMMENT_CHARS, tokenize

UREG = pint.UnitRegistry()
UREG.load_definitions(str(pathlib.Path(__file__).resolve().parent.joinpath("pint_units.txt")))

# Global configuration: if True, parse X..Y integer ranges as strings instead of IntegerRange
KEEP_RANGE_AS_STRING = False

# Registry for deprecated keywords: name -> (replacement, deprecation_message)
DEPRECATED_KEYWORDS: Dict[str, Tuple[Optional[str], str]] = {}

# Registry for deprecated sections: name -> (replacement, deprecation_message)
DEPRECATED_SECTIONS: Dict[str, Tuple[Optional[str], str]] = {}


def register_deprecated_keyword(name: str, replacement: Optional[str] = None, message: Optional[str] = None):
    """Register a keyword as deprecated.
    
    Args:
        name: The deprecated keyword name
        replacement: The recommended replacement keyword (if any)
        message: Custom deprecation message
    """
    default_msg = f"Keyword '{name}' is deprecated and may be removed in a future version"
    DEPRECATED_KEYWORDS[name.upper()] = (replacement, message or default_msg)


def register_deprecated_section(name: str, replacement: Optional[str] = None, message: Optional[str] = None):
    """Register a section as deprecated.
    
    Args:
        name: The deprecated section name
        replacement: The recommended replacement section (if any)
        message: Custom deprecation message
    """
    default_msg = f"Section '{name}' is deprecated and may be removed in a future version"
    DEPRECATED_SECTIONS[name.upper()] = (replacement, message or default_msg)


def check_deprecated_keyword(name: str) -> Optional[DeprecatedKeywordWarning]:
    """Check if a keyword is deprecated and return warning if so."""
    name_upper = name.upper()
    if name_upper in DEPRECATED_KEYWORDS:
        replacement, message = DEPRECATED_KEYWORDS[name_upper]
        return DeprecatedKeywordWarning(name, message, replacement)
    return None


def check_deprecated_section(name: str) -> Optional[DeprecatedKeywordWarning]:
    """Check if a section is deprecated and return warning if so."""
    name_upper = name.upper()
    if name_upper in DEPRECATED_SECTIONS:
        replacement, message = DEPRECATED_SECTIONS[name_upper]
        return DeprecatedSectionWarning(name, message, replacement)
    return None


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
INTEGER_RANGE = re.compile(r"^(?P<start>[+-]?\d+)\.\.(?P<end>[+-]?\d+)$")


def kw_converter_float(string):
    """convert a given string to a Python float

    :param string: string with the float, can be in Fortran scientific notation or as fraction
    """
    string = FORTRAN_REAL.sub(r"\1e\2", string)

    if "/" in string:
        return float(Fraction(string))

    return float(string)


@dataclass(frozen=True)
class IntegerRange:
    """Represents an integer range in X..Y format."""
    start: int
    end: int

    def __iter__(self):
        """Allow iteration over the range."""
        return iter(range(self.start, self.end + 1))

    def __len__(self):
        """Return the number of integers in the range."""
        return max(0, self.end - self.start + 1)

    def __contains__(self, value):
        """Check if value is in range."""
        return self.start <= value <= self.end

    def __str__(self):
        return f"{self.start}..{self.end}"

    def to_list(self):
        """Convert range to list of integers."""
        return list(range(self.start, self.end + 1))


def parse_integer_range(string: str) -> Union[int, IntegerRange, str]:
    """Parse a string that may contain an integer range (X..Y).
    
    Args:
        string: The string to parse
        
    Returns:
        IntegerRange if X..Y format detected, int if simple integer, 
        or original string if KEEP_RANGE_AS_STRING is True
        
    Raises:
        IntegerRangeError: If the range format is invalid
    """
    if KEEP_RANGE_AS_STRING:
        return string

    match = INTEGER_RANGE.match(string.strip())
    if match:
        start = int(match.group("start"))
        end = int(match.group("end"))
        
        if start > end:
            raise IntegerRangeError(
                f"Invalid integer range '{string}': start ({start}) must be <= end ({end})"
            )
        
        return IntegerRange(start, end)

    # Try to parse as simple integer
    try:
        return int(string)
    except ValueError:
        pass

    return string


def kw_converter_int(string, keep_range_as_string=None):
    """Convert string to integer or IntegerRange.

    Args:
        string: The string to convert
        keep_range_as_string: If True, return X..Y range as string instead of IntegerRange.
                              If None, uses global KEEP_RANGE_AS_STRING setting.
    """
    if keep_range_as_string is None:
        keep_range_as_string = KEEP_RANGE_AS_STRING

    match = INTEGER_RANGE.match(string)
    if match:
        if keep_range_as_string:
            return string
        start = int(match.group("start"))
        end = int(match.group("end"))
        if start > end:
            raise IntegerRangeError(
                f"Invalid integer range '{string}': start ({start}) must be <= end ({end})"
            )
        return IntegerRange(start, end)

    return int(string)


def kw_converter_keyword(string, allowed_values):
    string = string.upper()

    if string in allowed_values:
        return string

    raise InvalidParameterError(f"invalid keyword '{string}'")


KW_VALUE_CONVERTERS = {
    "logical": kw_converter_bool,
    "integer": kw_converter_int,
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
        try:
            default_unit = kw_node.find("./DEFAULT_UNIT").text
        except AttributeError:
            pass

        if default_unit and default_unit == "internal_cp2k":
            default_unit = None  # we can't do any conversion for hat

        if default_unit:
            default_unit = UREG.parse_expression(default_unit)

        current_unit = default_unit

        values = []

        for token in tokens:
            if token.startswith("["):
                if not default_unit:
                    raise InvalidParameterError(
                        "unit specified for value in keyword, but no default unit available or default unit is 'internal_cp2k'"
                    )
                current_unit = UREG.parse_expression(token.strip("[]"), case_sensitive=False)
                continue

            if token.startswith(COMMENT_CHARS):
                assert token == tokens[-1], "found inline comment which is not the last token"
                continue  # ignore inline comments

            value = datatype.parser(token)

            if datatype.type == "keyword":
                # keywords are also matched case insensitive, apply the same rules as for the keys
                value = key_trafo(value)

            if current_unit != default_unit:
                # interpret the given value in the specified unit, convert it and get the raw value
                value = (value * current_unit).to(default_unit).magnitude

            values += [value]

        if not values and lone_keyword_value and all(token.startswith(COMMENT_CHARS) for token in tokens):
            values = [datatype.parser(token) for token in lone_keyword_value]

            if datatype.type == "keyword":
                values = [key_trafo(value) for value in values]

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


# Pre-register some commonly deprecated CP2K keywords/sections
# These can be loaded from XML or configuration in the future

def _load_builtin_deprecations():
    """Load built-in deprecations for common CP2K keywords."""
    # Example deprecations - these should be updated based on CP2K changelog
    common_deprecations = [
        # (name, replacement, message)
        ("WF_CORRELATION", None, "Use RI_MP2 or RI_RPA instead"),
        ("MP2", "RI_MP2", "Direct MP2 is deprecated, use RI-MP2"),
    ]
    
    for name, replacement, message in common_deprecations:
        register_deprecated_keyword(name, replacement, message)


# Initialize built-in deprecations
_load_builtin_deprecations()
