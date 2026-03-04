import itertools
import re
import warnings
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterator, List, Optional, Tuple, Union

from . import DEFAULT_CP2K_INPUT_XML
from .keyword_helpers import (
    UREG,
    Keyword,
    check_deprecated_keyword,
    check_deprecated_section,
)
from .parser_errors import (
    ErrorContext,
    InvalidNameError,
    InvalidParameterError,
    InvalidSectionError,
    NameRepetitionError,
    NestedSectionError,
    ParserError,
    SectionMismatchError,
)
from .preprocessor import CP2KPreprocessor
from .tokenizer import COMMENT_CHARS, TokenizerError

_SECTION_MATCH = re.compile(r"&(?P<name>[\w\-_]+)\s*(?P<param>.*)")
_KEYWORD_MATCH = re.compile(r"(?P<name>[\w\-_]+)\s*(?P<value>.*)")


@dataclass
class Section:
    name: str
    node: ET.Element
    subsections: List["Section"] = field(default_factory=list)
    keywords: List[Keyword] = field(default_factory=list)
    param: Union[int, float, str, bool, None] = None
    repeats: bool = False
    line_number: Optional[int] = None

    def subsections_by_name(self, name) -> Iterator["Section"]:
        yield from (s for s in self.subsections if s.name == name)

    def keywords_by_name(self, name) -> Iterator[Keyword]:
        yield from (k for k in self.keywords if k.name == name)

    @property
    def keyword_names(self) -> Iterator[Optional[str]]:
        yield from (n.text for n in self.node.iterfind("./KEYWORD/NAME"))

    @property
    def section_names(self) -> Iterator[Optional[str]]:
        yield from (n.text for n in self.node.iterfind("./SECTION/NAME"))

    def find_node_by_name(self, tag, name):
        """return the node matching the given name or None"""
        for node in self.node.iterfind(f"./{tag}"):
            # ElementTree does not have a parent relationship,
            # hence the double loop
            for sub in node.iterfind("./NAME"):
                if sub.text == name.upper():
                    return node

        return None
    
    def get_section_stack(self) -> List[str]:
        """Get the full section stack path."""
        stack = []
        # This would need parent references to work fully
        # For now, return just this section's name
        return [self.name] if self.name != "/" else []


class CP2KInputParser:
    def __init__(self, xmlspec=DEFAULT_CP2K_INPUT_XML, base_dir=".", key_trafo=str.lower):
        """
        The CP2K input parser.

        :param xmlspec: Path to the `cp2k_input.xml` file generated with `cp2k --xml`
        :param base_dir: The base directory to be used for resolving `@include` directives
        :param key_trafo: A function object used for mangling key names, must treat input case-insensitive
        """

        # schema:
        self._spec = ET.parse(xmlspec)

        # datatree being generated:
        self._tree = None
        self._treerefs = []  # initializing to empty will make nested_dict return {} if nothing was parsed yet

        self._key_trafo = key_trafo
        self._base_inc_dir = base_dir
        
        # Track warnings
        self._warnings = []
        
        # Enhanced error tracking
        self._last_error_context = None

    def _add_tree_section(self, section_name, repeats, node, line_number=None):
        if not repeats and any(s.name == section_name for s in self._treerefs[-1].subsections):
            # TODO: the user possibly specified an alias, but here we only return the matching key
            ctx = ErrorContext(
                line=None,  # Will be set by caller
                section=self._treerefs[-1],
                section_stack=self._get_current_section_stack()
            )
            raise InvalidNameError(
                f"the section '{section_name}' can not be defined multiple times",
                ctx
            )

        # Check for deprecated sections
        deprecation_warning = check_deprecated_section(section_name)
        if deprecation_warning:
            warnings.warn(deprecation_warning)
            self._warnings.append(str(deprecation_warning))

        self._treerefs[-1].subsections += [Section(section_name, repeats=repeats, node=node, line_number=line_number)]
        self._treerefs += [self._treerefs[-1].subsections[-1]]

    def _get_current_section_stack(self) -> List[str]:
        """Get the current section stack for error reporting."""
        return [s.name for s in self._treerefs if s.name != "/"]

    def _parse_as_section(self, line, line_number=None):
        match = _SECTION_MATCH.match(line)
        
        if not match:
            ctx = ErrorContext(
                line=line,
                linenr=line_number,
                section_stack=self._get_current_section_stack()
            )
            raise InvalidSectionError(f"invalid section syntax: {line}", ctx)

        section_name = match.group("name").upper()
        section_param = match.group("param")

        if section_name == "END":
            section_param = section_param.rstrip()

            if section_param and section_param.upper() not in [e.text for e in self._treerefs[-1].node.iterfind("./NAME")]:
                ctx = ErrorContext(
                    line=line,
                    linenr=line_number,
                    section=self._treerefs[-1],
                    section_stack=self._get_current_section_stack(),
                    suggestion=f"Did you mean to close section '{self._treerefs[-1].name}'?"
                )
                raise SectionMismatchError(
                    f"could not match open section with name: {section_param}",
                    ctx
                )

            # if the END param was a match or none was specified, go a level up
            if len(self._treerefs) > 1:  # Don't pop root
                self._treerefs.pop()
            return

        # check all section nodes for matching names or aliases
        section_node = self._treerefs[-1].find_node_by_name("SECTION", section_name)
        if section_node is None:
            # Try to find similar section names for better error messages
            available_sections = list(self._treerefs[-1].section_names)
            suggestion = None
            if available_sections:
                # Simple fuzzy match - find sections with similar prefix
                similar = [s for s in available_sections if s and (section_name in s or s in section_name)]
                if similar:
                    suggestion = f"Did you mean: {', '.join(similar[:3])}?"
            
            ctx = ErrorContext(
                line=line,
                linenr=line_number,
                section_stack=self._get_current_section_stack(),
                suggestion=suggestion
            )
            raise InvalidSectionError(f"invalid section '{section_name}'", ctx)

        repeats = True if section_node.get("repeats") == "yes" else False

        self._add_tree_section(section_name, repeats, section_node, line_number)

        # check whether we got a parameter for the section and validate it
        if section_param and not section_param.startswith(COMMENT_CHARS):
            param_node = section_node.find("./SECTION_PARAMETERS")
            if param_node:  # validate the section parameter like a kw datatype
                # there is no way we get a second section parameter, assign directly
                try:
                    self._treerefs[-1].param = Keyword.from_string(param_node, section_param).values
                except InvalidParameterError as exc:
                    ctx = ErrorContext(
                        line=line,
                        linenr=line_number,
                        section=self._treerefs[-1],
                        section_stack=self._get_current_section_stack()
                    )
                    raise InvalidParameterError(
                        f"invalid parameter for section '{section_name}': {exc.message}",
                        ctx
                    ) from exc
            else:
                ctx = ErrorContext(
                    line=line,
                    linenr=line_number,
                    section=self._treerefs[-1],
                    section_stack=self._get_current_section_stack()
                )
                raise InvalidParameterError(
                    f"section parameters given for non-parametrized section '{section_name}': {section_param}",
                    ctx
                )

    def _add_tree_keyword(self, kw, line_number=None):
        if not kw.repeats and any(k.name == kw.name for k in self._treerefs[-1].keywords):
            # TODO: the user possibly specified an alias, but here we only return the matching key
            ctx = ErrorContext(
                line=None,
                linenr=line_number,
                section=self._treerefs[-1],
                section_stack=self._get_current_section_stack()
            )
            raise NameRepetitionError(
                f"the keyword '{kw.name}' can only be mentioned once",
                ctx
            )

        self._treerefs[-1].keywords += [kw]

    def _parse_as_keyword(self, line, line_number=None):
        match = _KEYWORD_MATCH.match(line)
        
        if not match:
            ctx = ErrorContext(
                line=line,
                linenr=line_number,
                section_stack=self._get_current_section_stack()
            )
            raise InvalidNameError(f"invalid keyword syntax: {line}", ctx)

        kw_name = match.group("name").upper()
        kw_value = match.group("value")

        kw_node = self._treerefs[-1].find_node_by_name("KEYWORD", kw_name)

        # if no keyword with the given name has been found, check for a default keyword for this section
        if kw_node is None:
            kw_node = self._treerefs[-1].find_node_by_name("DEFAULT_KEYWORD", "DEFAULT_KEYWORD")
            if kw_node is not None:  # for default keywords, the whole line is the value
                kw_value = line

        if kw_node is None:
            # Try to find similar keyword names for better error messages
            available_keywords = list(self._treerefs[-1].keyword_names)
            suggestion = None
            if available_keywords:
                similar = [k for k in available_keywords if k and (kw_name in k or k in kw_name)]
                if similar:
                    suggestion = f"Did you mean: {', '.join(similar[:3])}?"
            
            ctx = ErrorContext(
                line=line,
                linenr=line_number,
                section=self._treerefs[-1],
                section_stack=self._get_current_section_stack(),
                suggestion=suggestion
            )
            raise InvalidNameError(
                f"invalid keyword '{kw_name}' specified and no default keyword for this section",
                ctx
            )

        # Check for deprecated keywords
        deprecation_warning = check_deprecated_keyword(kw_name)
        if deprecation_warning:
            warnings.warn(deprecation_warning)
            self._warnings.append(str(deprecation_warning))

        try:
            kw = Keyword.from_string(kw_node, kw_value, self._key_trafo)  # the key_trafo is needed to mangle keywords
        except InvalidParameterError as exc:
            ctx = ErrorContext(
                line=line,
                linenr=line_number,
                section=self._treerefs[-1],
                section_stack=self._get_current_section_stack()
            )
            raise InvalidParameterError(
                f"invalid values for keyword '{kw_name}': {exc.message}",
                ctx
            ) from exc

        self._add_tree_keyword(kw, line_number)

    @property
    def nested_dict(self):
        stack = self._treerefs.copy()
        tree = {}
        treerefs = [tree]

        while stack:
            currsec = stack.pop(-1)
            treeref = treerefs.pop(-1)

            for section in currsec.subsections:
                section_name = f"+{self._key_trafo(section.name)}"

                if section.repeats:
                    try:
                        treeref[section_name] += [{}]
                    except KeyError:
                        treeref[section_name] = [{}]

                    treerefs += [treeref[section_name][-1]]

                else:
                    treeref[section_name] = {}
                    treerefs += [treeref[section_name]]

                stack += [section]

            for keyword in currsec.keywords:
                keyword_name = self._key_trafo(keyword.name)

                if keyword.repeats:
                    try:
                        treeref[keyword_name] += [keyword.values]
                    except KeyError:
                        treeref[keyword_name] = [keyword.values]
                else:
                    treeref[keyword_name] = keyword.values

            if currsec.param is not None:
                treeref["_"] = currsec.param

        return tree

    def parse(self, fhandle, initial_variable_values=None):
        """Parse a CP2K input file
        :param fhandle: An open file handle. Included files will be opened/closed transparently.
        :param initial_variable_values: optional dictionary with preprocessor variable names and their initial values
        :return: A nested dictionary, the parsed option "tree"
        """

        preprocessor = CP2KPreprocessor(fhandle, self._base_inc_dir, initial_variable_values)
        self._tree = Section("/", node=self._spec.getroot())
        self._treerefs = [self._tree]
        self._warnings = []

        for line in preprocessor:
            line_number = preprocessor.line_range[1] if hasattr(preprocessor, 'line_range') else None
            try:
                if line.startswith("&"):
                    self._parse_as_section(line, line_number)
                    continue

                self._parse_as_keyword(line, line_number)

            except (TokenizerError, InvalidParameterError, InvalidSectionError, InvalidNameError) as exc:
                # Enhance error context with preprocessor information
                if hasattr(exc, 'context') and exc.context:
                    exc.context.filename = preprocessor.fname
                    exc.context.linenr = preprocessor.line_range[1]
                    exc.context.colnrs = preprocessor.colnrs
                    exc.context.line = line
                    exc.context.section = self._treerefs[-1]
                    exc.context.section_stack = self._get_current_section_stack()
                raise

        if len(self._treerefs) > 1:
            unclosed = self._treerefs[-1]
            ctx = ErrorContext(
                line=None,
                section=unclosed,
                section_stack=self._get_current_section_stack(),
                suggestion=f"Add '&END {unclosed.name}' to close the section"
            )
            raise SectionMismatchError(
                f"section '{unclosed.name}' not closed",
                ctx
            )

        # returning the nested dictionary representation for convenience
        return self.nested_dict

    def coords(self, force_eval=0) -> Iterator[Tuple[str, Tuple[float, ...], Optional[str]]]:
        """
        Return an iterator to coordinates given in a FORCE_EVAL/SUBSYS/COORD section
        where the coordinates are proper float values and converted to Angstrom if specified in
        a different unit
        """

        try:
            coord = next(
                next(
                    next(
                        itertools.islice(self._tree.subsections_by_name("FORCE_EVAL"), force_eval, force_eval + 1)
                    ).subsections_by_name("SUBSYS")
                ).subsections_by_name("COORD")
            )
        except StopIteration:
            return

        scaled = next(coord.keywords_by_name("SCALED"), False)
        current_unit = UREG.parse_expression(next(coord.keywords_by_name("UNIT"), "ANGSTROM"), case_sensitive=False)

        for coordline in coord.keywords_by_name("*"):
            # coordinates are a series of strings according to the CP2K schema
            fields = coordline.values.split()

            name = fields[0]
            position = (float(Fraction(f)) for f in fields[1:4])  # positions can be fractions
            molname = fields[4] if len(fields) > 4 else None

            if not scaled and current_unit != UREG.angstrom:
                position = ((p * current_unit).to(UREG.angstrom).magnitude for p in position)

            yield (name, tuple(position), molname)

    @property
    def warnings(self) -> List[str]:
        """Return list of warnings generated during parsing."""
        return self._warnings.copy()


class CP2KInputParserSimplified(CP2KInputParser):
    """Implement structured output simplification."""

    def __init__(
        self,
        multi_value_unpack=True,
        repeated_section_unpack=True,
        level_reduction_blacklist=None,
        default_keyword_symbol="*",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._multi_value_unpack = multi_value_unpack
        self._repeated_section_unpack = repeated_section_unpack
        self._no_lvl_reduction = level_reduction_blacklist if (level_reduction_blacklist is not None) else []
        self._default_keyword_symbol = default_keyword_symbol

    def _get_value(self, keyword):
        """Conditionally unpack values"""
        if isinstance(keyword.values, (list, tuple)) and not self._multi_value_unpack:
            # this is the mode as currently employed by the aiida-cp2k plugin:
            # keywords with multiple arguments are treated as simple strings
            return " ".join(str(v) for v in keyword.values)

        return keyword.values

    @property
    def nested_dict(self):
        stack = self._treerefs.copy()
        tree = {}
        treerefs = [tree]

        while stack:
            currsec = stack.pop(-1)
            treeref = treerefs.pop(-1)

            for section in currsec.subsections:
                section_name = self._key_trafo(section.name)

                # if the section can be repeated and has a string parameter, we can possible simplify the structure
                if section.repeats:
                    # if the section is not already there, check whether to add as list or as dict with the param as subkey
                    if section_name not in treeref:
                        param_counts = Counter(s.param for s in currsec.subsections if s.name == section.name)
                        valid_keys = [n for n in itertools.chain(section.keyword_names, section.section_names)]
                        # check that the parameters are unique, strings and do not match any keywords or sections valid in that section
                        if self._repeated_section_unpack and all(
                            c == 1 and isinstance(p, str) and p.upper() not in valid_keys for p, c in param_counts.items()
                        ):
                            treeref[section_name] = {}
                        else:
                            treeref[section_name] = []

                    if isinstance(treeref[section_name], dict):
                        # if the already present section type is a section, we're using section params as keys
                        treeref[section_name][section.param] = {}
                        treerefs += [treeref[section_name][section.param]]
                    elif not any(s.name == section.name for s in currsec.subsections if s is not section) and (
                        section.name not in self._no_lvl_reduction
                    ):
                        # if the section would become a list of sections, but this is the only section with that name in
                        # the current level of the parsed tree, remove one level of the list as well
                        treeref[section_name] = {"_": section.param} if section.param is not None else {}
                        treerefs += [treeref[section_name]]
                    else:
                        treeref[section_name] += [{"_": section.param}] if section.param is not None else [{}]
                        treerefs += [treeref[section_name][-1]]

                else:
                    treeref[section_name] = {"_": section.param} if section.param is not None else {}
                    treerefs += [treeref[section_name]]

                stack += [section]

            for keyword in currsec.keywords:
                keyword_name = self._key_trafo(keyword.name)

                if keyword_name == "*":
                    keyword_name = self._default_keyword_symbol

                # if the keyword already exists as a section:
                if (keyword_name in treeref) and (
                    isinstance(treeref[keyword_name], dict)
                    or (isinstance(treeref[keyword_name], list) and isinstance(treeref[keyword_name][0], dict))
                ):
                    # prefix that sections key with a '+'
                    treeref[f"+{keyword_name}"] = treeref.pop(keyword_name)

                if keyword_name in treeref:
                    # NOTE: we don't have to check for mistakenly repeated keywords, that was already done while parsing
                    #       we are therefore not risking to append to a keyword with multiple values
                    if not isinstance(treeref[keyword_name], list):
                        # if the value is not yet a list, make it one
                        treeref[keyword_name] = [treeref[keyword_name]]

                    treeref[keyword_name] += [self._get_value(keyword)]
                else:
                    treeref[keyword_name] = self._get_value(keyword)

        return tree


class CP2KInputParserAiiDA(CP2KInputParserSimplified):
    """Implement structured output simplification as expected by aiida-cp2k as input parameter"""

    def __init__(self, *args, **kwargs):
        # aiida-cp2k uses a limited dict-based representation of the CP2K input,
        # and the simplified parser needs to be tweaked:
        # * avoid that something like "BASIS_SET ORB DZVP-MOLOPT-GTH" is unpacked
        #   into {"BASIS_SET": ("ORB", "DZVP-MOLOPT-GTH")}
        # * prevents the unpacking of repeated sections (removing the list)
        # * prevents that "KIND H" is turned into {"KIND": {"H": {"BASIS_SET": ...}}}
        #   but kept as {"KIND": {"_": "H", "BASIS_SET": ...}}} and with the option above
        #   makes it compatible with aiida-cp2k's way of CP2K input representation
        # NOTE: some CP2K input files can not be represented in this form

        super().__init__(
            *args,
            key_trafo=str.upper,
            multi_value_unpack=False,
            repeated_section_unpack=False,
            level_reduction_blacklist=["KIND"],
            default_keyword_symbol=" ",
            **kwargs,
        )
