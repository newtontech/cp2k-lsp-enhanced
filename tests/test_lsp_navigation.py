"""Tests for LSP navigation features: document symbols, go-to-definition, rename preparation."""

from cp2k_lsp.parser import CP2KInput, CP2KParser

# =============================================================================
# Helper
# =============================================================================


def _parse(text: str):
    """Parse text and return (ast, errors)."""
    parser = CP2KParser.parse_text(text)
    return parser.ast, parser.errors


# =============================================================================
# Document symbol extraction
# =============================================================================


class TestDocumentSymbolExtraction:
    """Test extracting document symbols from parsed AST for outline view."""

    def _walk_sections(self, ast: CP2KInput):
        """Return list of (name, line, level, parent) tuples."""
        result = []

        def _walk(section, level, parent):
            result.append((section.name, section.line, level, parent))
            for sub in section.subsections:
                _walk(sub, level + 1, section.name)

        if ast.global_section:
            _walk(ast.global_section, 0, "")
        for sec in ast.sections:
            _walk(sec, 0, "")
        return result

    def test_symbols_from_realistic_input(self):
        """Realistic input should produce correct symbol hierarchy."""
        inp = """\
&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
  METHOD QS
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    &MGRID
      CUTOFF 400
      REL_CUTOFF 50
    &END MGRID
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
    &END SCF
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  &SUBSYS
    &KIND H
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &CELL
      ABC 10.0 10.0 10.0
    &END CELL
    &COORD
      O  0.0  0.0  0.0
      H  0.9  0.0  0.0
      H -0.9  0.0  0.0
    &END COORD
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        symbols = self._walk_sections(ast)

        # Top level
        names = [s[0] for s in symbols]
        assert "GLOBAL" in names
        assert "FORCE_EVAL" in names

        # GLOBAL is at level 0
        global_sym = next(s for s in symbols if s[0] == "GLOBAL")
        assert global_sym[2] == 0

        # DFT is inside FORCE_EVAL
        dft_sym = next(s for s in symbols if s[0] == "DFT")
        assert dft_sym[2] == 1
        assert dft_sym[3] == "FORCE_EVAL"

        # MGRID is inside DFT
        mgrid_sym = next(s for s in symbols if s[0] == "MGRID")
        assert mgrid_sym[2] == 2
        assert mgrid_sym[3] == "DFT"

        # KIND appears twice
        kind_symbols = [s for s in symbols if s[0] == "KIND"]
        assert len(kind_symbols) == 2

    def test_symbols_line_numbers_accurate(self):
        """Symbol line numbers should match source positions."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        symbols = self._walk_sections(ast)

        global_sym = next(s for s in symbols if s[0] == "GLOBAL")
        assert global_sym[1] == 1

        fe_sym = next(s for s in symbols if s[0] == "FORCE_EVAL")
        assert fe_sym[1] == 5

    def test_symbols_with_comments(self):
        """Comments between sections shouldn't break symbol extraction."""
        inp = """\
# This is a header comment
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL

# FORCE_EVAL section
&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, errors = _parse(inp)
        symbols = self._walk_sections(ast)
        names = [s[0] for s in symbols]
        assert "GLOBAL" in names
        assert "FORCE_EVAL" in names


# =============================================================================
# AST navigation helpers
# =============================================================================


class TestASTNavigation:
    """Test AST query methods for navigation support."""

    def test_get_section_by_name(self):
        """get_section should find sections case-insensitively."""
        inp = """\
&FORCE_EVAL
  METHOD QS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        assert ast.get_section("FORCE_EVAL") is not None
        assert ast.get_section("force_eval") is not None
        assert ast.get_section("FORCE_eval") is not None

    def test_get_subsection_by_name(self):
        """get_subsection should find subsections case-insensitively."""
        inp = """\
&FORCE_EVAL
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
  &END DFT
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        fe = ast.get_section("FORCE_EVAL")
        assert fe.get_subsection("DFT") is not None
        assert fe.get_subsection("dft") is not None

    def test_get_keyword_by_name(self):
        """get_keyword should find keywords case-insensitively."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
"""
        ast, _ = _parse(inp)
        kw = ast.global_section.get_keyword("RUN_TYPE")
        assert kw is not None
        assert kw.value.value == "ENERGY"

    def test_keyword_iteration(self):
        """Iterating over keywords should give correct count."""
        inp = """\
&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
  PRINT_LEVEL LOW
&END GLOBAL
"""
        ast, _ = _parse(inp)
        assert len(ast.global_section.keywords) == 3

    def test_subsection_iteration(self):
        """Iterating over subsections should give correct count."""
        inp = """\
&FORCE_EVAL
  &DFT
  &END DFT
  &SUBSYS
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        fe = ast.get_section("FORCE_EVAL")
        assert len(fe.subsections) == 2


# =============================================================================
# AST representation
# =============================================================================


class TestASTRepresentation:
    """Test AST __repr__ methods for debugging/logging."""

    def test_cp2k_input_repr(self):
        """CP2KInput repr should show section count."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
"""
        ast, _ = _parse(inp)
        r = repr(ast)
        assert "CP2KInput" in r
        assert "1 sections" in r

    def test_section_repr(self):
        """Section repr should show keyword and subsection counts."""
        inp = """\
&FORCE_EVAL
  METHOD QS
  &DFT
  &END DFT
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        fe = ast.sections[0]
        r = repr(fe)
        assert "FORCE_EVAL" in r
        assert "1 keywords" in r
        assert "1 subsections" in r

    def test_keyword_repr(self):
        """Keyword repr should show name and value."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
"""
        ast, _ = _parse(inp)
        kw = ast.global_section.get_keyword("RUN_TYPE")
        r = repr(kw)
        assert "RUN_TYPE" in r
        assert "ENERGY" in r

    def test_value_repr_with_unit(self):
        """Value with unit should show unit in repr."""
        from cp2k_lsp.parser.ast import Value, ValueType

        v = Value(value=4.07419, value_type=ValueType.NUMBER, unit="angstrom", line=1, column=1)
        r = repr(v)
        assert "angstrom" in r


# =============================================================================
# Rename preparation (finding all references to a section/keyword)
# =============================================================================


class TestRenamePreparation:
    """Test finding all references for rename support."""

    def _find_keyword_references(self, ast: CP2KInput, keyword_name: str) -> list:
        """Find all occurrences of a keyword in the AST."""
        refs = []

        def _walk(section):
            for kw in section.keywords:
                if kw.name.upper() == keyword_name.upper():
                    refs.append((section.name, kw.name, kw.line))
            for sub in section.subsections:
                _walk(sub)

        if ast.global_section:
            _walk(ast.global_section)
        for sec in ast.sections:
            _walk(sec)
        return refs

    def test_find_keyword_references(self):
        """Should find all references to a keyword across sections."""
        inp = """\
&FORCE_EVAL
  METHOD QS
  &DFT
    &SCF
      EPS_SCF 1.0E-6
      MAX_SCF 50
    &END SCF
  &END DFT
  &SUBSYS
    &KIND H
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      BASIS_SET DZVP
      POTENTIAL GTH-PBE
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        # Find all BASIS_SET references
        refs = self._find_keyword_references(ast, "BASIS_SET")
        assert len(refs) == 2
        assert all(r[1] == "BASIS_SET" for r in refs)

    def test_find_potential_references(self):
        """Should find all POTENTIAL keyword references."""
        inp = """\
&FORCE_EVAL
  &SUBSYS
    &KIND H
      POTENTIAL GTH-PBE
    &END KIND
    &KIND O
      POTENTIAL GTH-PBE
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
"""
        ast, _ = _parse(inp)
        refs = self._find_keyword_references(ast, "POTENTIAL")
        assert len(refs) == 2

    def test_no_false_positive_references(self):
        """Should not find references that don't exist."""
        inp = """\
&GLOBAL
  RUN_TYPE ENERGY
&END GLOBAL
"""
        ast, _ = _parse(inp)
        refs = self._find_keyword_references(ast, "BASIS_SET")
        assert len(refs) == 0
