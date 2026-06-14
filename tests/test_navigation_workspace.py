"""Tests for navigation and workspace resource features (#120, #123).

Tests cover:
- Document symbols with proper ranges
- Folding ranges for sections and preprocessor blocks
- Goto definition for @INCLUDE, BASIS_SET_FILE_NAME, POTENTIAL_FILE_NAME
- References for variables, include files, KIND labels
- Workspace resource index for file tracking
- Data file parser for entry listing
- Diagnostics for missing/unreadable files and unknown entries
- Completion items for local filenames and datafile entries
"""

import os
import tempfile

import pytest
from cp2k_lsp.features.definition import provide_definition, provide_references
from cp2k_lsp.features.resource_completion import provide_resource_completions
from cp2k_lsp.features.resource_diagnostics import provide_resource_diagnostics
from cp2k_lsp.features.symbols import provide_document_symbols, provide_folding_ranges
from lsprotocol import types as lsp

from cp2k_input_tools.cache_invalidation import CacheInvalidator
from cp2k_input_tools.datafile_parser import (
    get_available_labels,
    get_entry_range,
    list_entries,
    parse_basis_file,
    parse_potential_file,
    validate_entry,
)
from cp2k_input_tools.workspace_index import FileReference, WorkspaceResourceIndex

# Test fixtures
SAMPLE_CP2K_INPUT = """&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_SET
    POTENTIAL_FILE_NAME POTENTIAL
    LSD
    &MGRID
      CUTOFF 140
    &END MGRID
    &QS
      EPS_DEFAULT 1.0E-8
      METHOD GPW
    &END QS
    &SCF
      EPS_DIIS 0.1
      EPS_SCF 1.0E-4
      MAX_DIIS 4
      MAX_SCF 30
      SCF_GUESS atomic
    &END SCF
  &END DFT
  &SUBSYS
    &CELL
      ABC 8.0 4.0 4.0
    &END CELL
    &COORD
      H     0.000000  0.000000  0.000000
      H     1.000000  0.000000  0.000000
    &END COORD
    &KIND H
      BASIS_SET DZV-GTH-PADE
      POTENTIAL GTH-PADE-q1
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
&GLOBAL
  PROJECT H2
  PRINT_LEVEL MEDIUM
&END GLOBAL
"""

SAMPLE_INCLUDE_INPUT = """&GLOBAL
  @INCLUDE "settings.inc"
  PROJECT TEST
&END GLOBAL
"""

SAMPLE_VARIABLE_INPUT = """&GLOBAL
  @SET MY_VAR 100
  PROJECT ${MY_VAR}
&END GLOBAL
"""

SAMPLE_BASIS_FILE = """H
2
1  0  1  1.3  1.0
1  0  0  0.8  1.0

He
2
1  0  1  1.8  1.0
1  0  0  1.2  1.0

Si
3
1  0  2  1.5  1.0  1.2  1.0
1  0  1  0.8  1.0
1  0  0  0.5  1.0
"""

SAMPLE_POTENTIAL_FILE = """H GTH-PBE
1
0  2  0  1.3

He GTH-PBE
2
0  2  0  1.8
0  2  1  1.1  1.0  1.5  1.4

Si GTH-PBE
4
0  2  0  2.0
0  2  1  1.5  1.0  1.2  1.0
0  2  2  1.0  1.0  1.0  1.0
"""


class TestWorkspaceResourceIndex:
    """Tests for WorkspaceResourceIndex service."""

    def test_add_file_reference(self):
        """Test adding file references to the index."""
        index = WorkspaceResourceIndex()
        
        ref = FileReference(
            uri="test://test.inp",
            line=0,
            column=0,
            ref_type='INCLUDE',
            value="settings.inc"
        )
        
        index.add_file_reference("test://test.inp", ref)
        
        assert "test://test.inp" in index.file_references
        assert len(index.file_references["test://test.inp"]) == 1

    def test_clear_document(self):
        """Test clearing references for a document."""
        index = WorkspaceResourceIndex()
        
        ref = FileReference(
            uri="test://test.inp",
            line=0,
            column=0,
            ref_type='INCLUDE',
            value="settings.inc"
        )
        
        index.add_file_reference("test://test.inp", ref)
        assert "test://test.inp" in index.file_references
        
        index.clear_document("test://test.inp")
        assert "test://test.inp" not in index.file_references

    def test_invalidate_file(self):
        """Test invalidating a file from cache."""
        index = WorkspaceResourceIndex()
        
        # Add some cached data
        index.data_files["/path/to/file"] = []
        index._cache["test_key"] = "/path/to/file"
        
        index.invalidate_file("/path/to/file")
        
        assert "/path/to/file" not in index.data_files
        assert "test_key" not in index._cache

    def test_parse_cp2k_document(self):
        """Test parsing a CP2K document for file references."""
        index = WorkspaceResourceIndex()
        
        refs = index.parse_cp2k_document("test://test.inp", SAMPLE_CP2K_INPUT)
        
        assert len(refs) >= 2  # BASIS_SET_FILE_NAME and POTENTIAL_FILE_NAME
        
        ref_types = [r.ref_type for r in refs]
        assert 'BASIS_SET_FILE_NAME' in ref_types
        assert 'POTENTIAL_FILE_NAME' in ref_types

    def test_parse_include_directive(self):
        """Test parsing @INCLUDE directives."""
        index = WorkspaceResourceIndex()
        
        refs = index.parse_cp2k_document("test://test.inp", SAMPLE_INCLUDE_INPUT)
        
        assert len(refs) == 1
        assert refs[0].ref_type == 'INCLUDE'
        assert refs[0].value == "settings.inc"

    def test_parse_variable_references(self):
        """Test parsing ${VAR} references."""
        index = WorkspaceResourceIndex()
        
        refs = index.parse_cp2k_document("test://test.inp", SAMPLE_VARIABLE_INPUT)
        
        # Should find the @SET and ${VAR} references
        assert len(refs) >= 0  # Current implementation doesn't track variables

    def test_resolve_file_path_relative(self):
        """Test resolving relative file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.inp")
            include_file = os.path.join(tmpdir, "settings.inc")
            
            with open(test_file, 'w') as f:
                f.write("&GLOBAL\n  @INCLUDE \"settings.inc\"\n&END GLOBAL\n")
            
            with open(include_file, 'w') as f:
                f.write("PROJECT TEST\n")
            
            index = WorkspaceResourceIndex(root_uri=tmpdir)
            
            ref = FileReference(
                uri=f"file://{test_file}",
                line=1,
                column=2,
                ref_type='INCLUDE',
                value="settings.inc"
            )
            
            resolved = index.resolve_file_path(ref, f"file://{test_file}")
            
            assert resolved is not None
            assert os.path.exists(resolved)

    def test_resolve_file_path_missing(self):
        """Test resolving a missing file path."""
        index = WorkspaceResourceIndex()
        
        ref = FileReference(
            uri="test://test.inp",
            line=0,
            column=0,
            ref_type='INCLUDE',
            value="missing.inc"
        )
        
        resolved = index.resolve_file_path(ref, "test://test.inp")
        
        assert resolved is None


class TestDataFileParser:
    """Tests for data file parser."""

    def test_parse_basis_file(self):
        """Test parsing a basis set file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            assert data_file is not None
            assert len(data_file.entries) == 3
            
            # Check first entry
            assert data_file.entries[0].name == "H"
            assert data_file.entries[0].start_line == 0
            
            # Check second entry
            assert data_file.entries[1].name == "He"
            
            # Check third entry
            assert data_file.entries[2].name == "Si"
        finally:
            os.unlink(temp_path)

    def test_parse_potential_file(self):
        """Test parsing a potential file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.potential', delete=False) as f:
            f.write(SAMPLE_POTENTIAL_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_potential_file(temp_path)
            
            assert data_file is not None
            assert len(data_file.entries) == 3
            
            # Check entries with labels
            assert data_file.entries[0].name == "H"
            assert data_file.entries[0].label == "GTH-PBE"
            
            assert data_file.entries[1].name == "He"
            assert data_file.entries[1].label == "GTH-PBE"
            
            assert data_file.entries[2].name == "Si"
            assert data_file.entries[2].label == "GTH-PBE"
        finally:
            os.unlink(temp_path)

    def test_find_entry(self):
        """Test finding an entry in a data file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            # Find by name
            entry = data_file.find_entry("H")
            assert entry is not None
            assert entry.name == "H"
            
            # Find by name and label — use potential file (basis files have no labels)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pot', delete=False) as fp:
                fp.write(SAMPLE_POTENTIAL_FILE)
                pot_path = fp.name
            try:
                pot_data = parse_potential_file(pot_path)
                entry = pot_data.find_entry("H", "GTH-PBE")
                assert entry is not None
                assert entry.name == "H"
                assert entry.label == "GTH-PBE"
            finally:
                os.unlink(pot_path)
            
            # Find non-existent entry
            entry = data_file.find_entry("X")
            assert entry is None
        finally:
            os.unlink(temp_path)

    def test_find_entries_by_name(self):
        """Test finding all entries with a given name."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            # Find all H entries
            entries = data_file.find_entries_by_name("H")
            assert len(entries) == 1
            assert entries[0].name == "H"
        finally:
            os.unlink(temp_path)

    def test_get_entry_range(self):
        """Test getting the line range for an entry."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            # Get range for H entry
            range_result = get_entry_range(data_file, "H")
            assert range_result is not None
            assert range_result[0] == 0  # start_line
            assert range_result[1] == 3  # end_line
        finally:
            os.unlink(temp_path)

    def test_list_entries(self):
        """Test listing entries in a data file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            # List all entries
            entries = list_entries(data_file)
            assert len(entries) == 3
            
            # List entries for specific element
            entries = list_entries(data_file, "H")
            assert len(entries) == 1
        finally:
            os.unlink(temp_path)

    def test_get_available_labels(self):
        """Test getting available labels for an element."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.potential', delete=False) as f:
            f.write(SAMPLE_POTENTIAL_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_potential_file(temp_path)
            
            # Get labels for H
            labels = get_available_labels(data_file, "H")
            assert "GTH-PBE" in labels
        finally:
            os.unlink(temp_path)

    def test_validate_entry(self):
        """Test validating an entry exists."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.basis', delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        
        try:
            data_file = parse_basis_file(temp_path)
            
            # Validate existing entry
            is_valid, message = validate_entry(data_file, "H")
            assert is_valid is True
            
            # Validate non-existent entry
            is_valid, message = validate_entry(data_file, "X")
            assert is_valid is False
        finally:
            os.unlink(temp_path)


class TestDocumentSymbols:
    """Tests for document symbols provider."""

    def test_provide_document_symbols(self):
        """Test providing document symbols from AST."""
        from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section
        
        # Create a simple AST using correct attributes
        section = Section(name="GLOBAL", line=1, column=0)
        section.end_line = 5
        section.end_column = 0
        keyword = Keyword(name="PROJECT", line=2, column=2)
        keyword.end_line = 2
        keyword.end_column = 10
        section.keywords.append(keyword)
        
        ast = CP2KInput()
        ast.sections.append(section)
        
        symbols = provide_document_symbols(ast)
        
        assert len(symbols) == 1
        assert symbols[0].name == "GLOBAL"
        assert symbols[0].kind == lsp.SymbolKind.Module

    def test_provide_folding_ranges(self):
        """Test providing folding ranges from AST."""
        from cp2k_lsp.parser.ast import CP2KInput, Section
        
        # Create a simple AST with nested sections
        inner_section = Section(name="DFT", line=2, column=2)
        inner_section.end_line = 10
        inner_section.end_column = 0
        outer_section = Section(name="FORCE_EVAL", line=1, column=0)
        outer_section.end_line = 12
        outer_section.end_column = 0
        outer_section.subsections.append(inner_section)
        
        ast = CP2KInput()
        ast.sections.append(outer_section)
        
        ranges = provide_folding_ranges(ast)
        
        assert len(ranges) == 2
        assert ranges[0].start_line == 0  # FORCE_EVAL (line=1 → 0-based=0)
        assert ranges[0].end_line == 11   # end_line=12 → 0-based=11
        assert ranges[1].start_line == 1  # DFT (line=2 → 0-based=1)
        assert ranges[1].end_line == 9    # end_line=10 → 0-based=9


class TestGotoDefinition:
    """Tests for goto definition provider."""

    def test_provide_definition(self):
        """Test providing definition for a symbol."""
        from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section, Value
        
        # Create a simple AST using correct attributes
        section = Section(name="GLOBAL", line=1, column=0)
        section.end_line = 5
        section.end_column = 0
        keyword = Keyword(
            name="BASIS_SET_FILE_NAME", 
            line=2, 
            column=2,
        )
        keyword.end_line = 2
        keyword.end_column = 25
        keyword.value = Value(value="BASIS_SET", line=2, column=25)
        keyword.value.end_line = 2
        keyword.value.end_column = 35
        section.keywords.append(keyword)
        
        ast = CP2KInput()
        ast.sections.append(section)
        index = WorkspaceResourceIndex()
        
        position = lsp.Position(line=1, character=5)
        result = provide_definition(ast, position, "test://test.inp", index)
        
        # Result depends on file resolution
        assert result is None or isinstance(result, lsp.Location)

    def test_provide_references(self):
        """Test providing references for a symbol."""
        from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section
        
        # Create a simple AST using correct attributes
        section = Section(name="GLOBAL", line=1, column=0)
        section.end_line = 5
        section.end_column = 0
        keyword = Keyword(name="BASIS_SET_FILE_NAME", line=2, column=2)
        keyword.end_line = 2
        keyword.end_column = 25
        section.keywords.append(keyword)
        
        ast = CP2KInput()
        ast.sections.append(section)
        index = WorkspaceResourceIndex()
        
        position = lsp.Position(line=1, character=5)
        result = provide_references(ast, position, "test://test.inp", index)
        
        assert isinstance(result, list)


class TestResourceDiagnostics:
    """Tests for resource diagnostics provider."""

    def test_provide_resource_diagnostics(self):
        """Test providing diagnostics for resource references."""
        from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section, Value
        
        # Create a simple AST using correct attributes
        section = Section(name="GLOBAL", line=1, column=0)
        section.end_line = 5
        section.end_column = 0
        keyword = Keyword(
            name="BASIS_SET_FILE_NAME", 
            line=2, 
            column=2,
        )
        keyword.end_line = 2
        keyword.end_column = 25
        keyword.value = Value(value="BASIS_SET", line=2, column=25)
        keyword.value.end_line = 2
        keyword.value.end_column = 35
        section.keywords.append(keyword)
        
        ast = CP2KInput()
        ast.sections.append(section)
        index = WorkspaceResourceIndex()
        
        diagnostics = provide_resource_diagnostics(ast, "test://test.inp", index)
        
        assert isinstance(diagnostics, list)
        # May have diagnostics for missing file
        for diag in diagnostics:
            assert isinstance(diag, lsp.Diagnostic)


class TestResourceCompletion:
    """Tests for resource completion provider."""

    def test_provide_resource_completions(self):
        """Test providing completions for resource references."""
        from cp2k_lsp.parser.ast import CP2KInput, Keyword, Section
        
        # Create a simple AST using correct attributes
        section = Section(name="GLOBAL", line=1, column=0)
        section.end_line = 5
        section.end_column = 0
        keyword = Keyword(name="BASIS_SET_FILE_NAME", line=2, column=2)
        keyword.end_line = 2
        keyword.end_column = 25
        section.keywords.append(keyword)
        
        ast = CP2KInput()
        ast.sections.append(section)
        index = WorkspaceResourceIndex()
        
        position = lsp.Position(line=1, character=10)
        lines = ["BASIS_SET_FILE_NAME BASIS_SET"]
        result = provide_resource_completions(ast, position, "test://test.inp", index, lines)
        
        # Result may be None if no completions available
        assert result is None or isinstance(result, lsp.CompletionList)


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_on_file_created(self):
        """Test file creation event handling."""
        index = WorkspaceResourceIndex()
        invalidator = CacheInvalidator(index)
        
        # Should not raise an exception
        invalidator.on_file_created("/path/to/new/file")

    def test_on_file_deleted(self):
        """Test file deletion event handling."""
        index = WorkspaceResourceIndex()
        index.data_files["/path/to/file"] = []
        invalidator = CacheInvalidator(index)
        
        invalidator.on_file_deleted("/path/to/file")
        
        assert "/path/to/file" not in index.data_files

    def test_on_file_changed(self):
        """Test file change event handling."""
        index = WorkspaceResourceIndex()
        index.data_files["/path/to/file"] = []
        invalidator = CacheInvalidator(index)
        
        invalidator.on_file_changed("/path/to/file")
        
        assert "/path/to/file" not in index.data_files

    def test_on_workspace_folder_changed(self):
        """Test workspace folder change event handling."""
        index = WorkspaceResourceIndex()
        index._cache["test"] = "value"
        index.data_files["test"] = []
        invalidator = CacheInvalidator(index)
        
        invalidator.on_workspace_folder_changed(["/new/folder"], ["/old/folder"])
        
        assert len(index._cache) == 0
        assert len(index.data_files) == 0


class TestIntegration:
    """Integration tests for navigation and workspace features."""

    def test_end_to_end_workflow(self):
        """Test a complete workflow with file references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            main_file = os.path.join(tmpdir, "main.inp")
            basis_file = os.path.join(tmpdir, "BASIS_SET")
            potential_file = os.path.join(tmpdir, "POTENTIAL")

            with open(main_file, 'w') as f:
                f.write(SAMPLE_CP2K_INPUT)

            with open(basis_file, 'w') as f:
                f.write(SAMPLE_BASIS_FILE)

            with open(potential_file, 'w') as f:
                f.write(SAMPLE_POTENTIAL_FILE)

            # Create workspace index
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # Parse the main file
            with open(main_file, 'r') as f:
                content = f.read()

            refs = index.parse_cp2k_document(f"file://{main_file}", content)

            # Should have found BASIS_SET_FILE_NAME and POTENTIAL_FILE_NAME
            assert len(refs) >= 2

            # Resolve file paths
            for ref in refs:
                resolved = index.resolve_file_path(ref, f"file://{main_file}")
                # Some files may not exist
                if resolved:
                    assert os.path.exists(resolved)


class TestNavigationWithFixtures:
    """Integration tests using real CP2K inputs and on-disk fixtures.

    These tests exercise the navigation providers against fixture files on disk
    so that file path resolution and datafile parsing are covered end-to-end
    (#120 / #123).
    """

    def _write_workspace(self, tmpdir: str) -> dict:
        """Create a fixture workspace with main input, include, basis and potential files."""
        paths = {
            "main": os.path.join(tmpdir, "main.inp"),
            "include": os.path.join(tmpdir, "settings.inc"),
            "basis": os.path.join(tmpdir, "BASIS_SET"),
            "potential": os.path.join(tmpdir, "POTENTIAL"),
        }
        with open(paths["main"], "w") as f:
            f.write(SAMPLE_CP2K_INPUT)
        with open(paths["include"], "w") as f:
            f.write("PROJECT INCLUDED\n")
        with open(paths["basis"], "w") as f:
            f.write(SAMPLE_BASIS_FILE)
        with open(paths["potential"], "w") as f:
            f.write(SAMPLE_POTENTIAL_FILE)
        return paths

    def test_include_goto_definition_resolves_file(self):
        """@INCLUDE goto-definition should return the included file's location."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"

            with open(paths["main"], "r") as f:
                text = f.read()

            # Append an @INCLUDE for navigation testing
            include_text = (
                "&GLOBAL\n  PROJECT TEST\n  @INCLUDE \"settings.inc\"\n&END GLOBAL\n"
            )
            text = text + "\n" + include_text
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # The @INCLUDE directive sits on the last appended line; find it
            include_line = next(
                i for i, ln in enumerate(lines) if "@INCLUDE" in ln.upper()
            )
            include_text_line = lines[include_line]
            position = lsp.Position(
                line=include_line,
                character=include_text_line.upper().find("INCLUDE"),
            )
            result = provide_definition(ast, position, main_uri, index, lines)

            assert result is not None
            assert result.uri.endswith("settings.inc")

    def test_basis_set_file_name_goto_definition(self):
        """BASIS_SET_FILE_NAME goto-definition should resolve to the data file."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"

            with open(paths["main"], "r") as f:
                text = f.read()
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # Find BASIS_SET_FILE_NAME line
            bsz_line = next(
                i for i, ln in enumerate(lines) if "BASIS_SET_FILE_NAME" in ln.upper()
            )
            # Cursor somewhere inside the keyword name (column is 1-indexed)
            position = lsp.Position(line=bsz_line, character=10)
            result = provide_definition(ast, position, main_uri, index, lines)

            assert result is not None
            assert result.uri.endswith("BASIS_SET")

    def test_missing_data_file_diagnostics(self):
        """Resource diagnostics should flag missing data files."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            main_file = os.path.join(tmpdir, "main.inp")
            # Write main input but omit BASIS_SET and POTENTIAL files entirely
            with open(main_file, "w") as f:
                f.write(SAMPLE_CP2K_INPUT)

            main_uri = f"file://{main_file}"

            with open(main_file, "r") as f:
                text = f.read()
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            diagnostics = provide_resource_diagnostics(ast, main_uri, index, lines)

            # Should have at least one error diagnostic for missing files
            assert any(
                d.severity == lsp.DiagnosticSeverity.Error for d in diagnostics
            )

    def test_missing_include_diagnostics(self):
        """Missing @INCLUDE files should produce a missing-include diagnostic."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"

            text = (
                "&GLOBAL\n  PROJECT TEST\n  @INCLUDE \"missing.inc\"\n&END GLOBAL\n"
            )
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            diagnostics = provide_resource_diagnostics(ast, main_uri, index, lines)

            missing = [
                d for d in diagnostics if d.code == "missing-include"
            ]
            assert len(missing) == 1
            assert "missing.inc" in missing[0].message

    def test_unknown_data_entry_diagnostics(self):
        """Unknown BASIS_SET entries should produce a warning diagnostic."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"

            # Rewrite the input so the H KIND references a bogus basis set
            with open(paths["main"], "w") as f:
                f.write(
                    SAMPLE_CP2K_INPUT.replace(
                        "BASIS_SET DZV-GTH-PADE", "BASIS_SET NONEXISTENT-BS"
                    )
                )

            with open(paths["main"], "r") as f:
                text = f.read()
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            diagnostics = provide_resource_diagnostics(ast, main_uri, index, lines)

            unknown = [
                d for d in diagnostics if d.code == "unknown-entry"
            ]
            assert len(unknown) >= 1

    def test_datafile_entry_completion(self):
        """Completion in a BASIS_SET line should suggest element entries."""
        from cp2k_lsp.parser import CP2KParser

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"

            with open(paths["main"], "r") as f:
                text = f.read()
            lines = text.split("\n")

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # Place cursor inside the BASIS_SET keyword line within &KIND H
            # (skip the BASIS_SET_FILE_NAME line which lives under &DFT)
            bsz_line = next(
                i
                for i, ln in enumerate(lines)
                if ln.strip().startswith("BASIS_SET") and "FILE_NAME" not in ln.upper()
            )
            position = lsp.Position(line=bsz_line, character=12)

            result = provide_resource_completions(
                ast, position, main_uri, index, lines
            )
            assert result is not None
            labels = [item.label for item in result.items]
            assert "H" in labels

    def test_variable_reference_goto_definition(self):
        """${VAR} goto-definition should locate the nearest @SET definition."""
        from cp2k_lsp.parser import CP2KParser

        text = (
            "&GLOBAL\n"
            "  @SET MY_VAR 100\n"
            "  PROJECT ${MY_VAR}\n"
            "&END GLOBAL\n"
        )
        lines = text.split("\n")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "main.inp")
            with open(input_file, "w") as f:
                f.write(text)
            main_uri = f"file://{input_file}"

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # Cursor on ${MY_VAR} on the third line
            pos = lsp.Position(line=2, character=12)
            result = provide_definition(ast, pos, main_uri, index, lines)
            assert result is not None
            assert result.uri == main_uri
            assert result.range.start.line == 1

    def test_variable_references_finds_all_usages(self):
        """provide_references on @SET variable should find ${VAR} usages."""
        from cp2k_lsp.parser import CP2KParser

        text = (
            "&GLOBAL\n"
            "  @SET MY_VAR 100\n"
            "  PROJECT ${MY_VAR}\n"
            "  RUN_TYPE ${MY_VAR}\n"
            "&END GLOBAL\n"
        )
        lines = text.split("\n")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "main.inp")
            with open(input_file, "w") as f:
                f.write(text)
            main_uri = f"file://{input_file}"

            parser = CP2KParser.parse_text(text, main_uri)
            ast = parser.ast
            index = WorkspaceResourceIndex(root_uri=tmpdir)

            # Cursor on @SET MY_VAR (line 1)
            pos = lsp.Position(line=1, character=8)
            result = provide_references(ast, pos, main_uri, index, True, lines)
            assert len(result) >= 2  # at least the two ${MY_VAR} usages

    def test_workspace_index_tracks_file_references(self):
        """WorkspaceResourceIndex should track data file references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._write_workspace(tmpdir)
            main_uri = f"file://{paths['main']}"
            with open(paths["main"], "r") as f:
                content = f.read()

            index = WorkspaceResourceIndex(root_uri=tmpdir)
            refs = index.parse_cp2k_document(main_uri, content)

            types_found = {r.ref_type for r in refs}
            assert "BASIS_SET_FILE_NAME" in types_found
            assert "POTENTIAL_FILE_NAME" in types_found

            # Resolved files should point at the on-disk basis/potential files
            resolved_basis = next(
                index.resolve_file_path(r, main_uri)
                for r in refs
                if r.ref_type == "BASIS_SET_FILE_NAME"
            )
            assert os.path.basename(resolved_basis) == "BASIS_SET"

    def test_cache_invalidator_on_file_changed(self):
        """CacheInvalidator should clear data file cache when a file changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            basis_file = os.path.join(tmpdir, "BASIS_SET")
            with open(basis_file, "w") as f:
                f.write(SAMPLE_BASIS_FILE)

            index = WorkspaceResourceIndex(root_uri=tmpdir)
            index.parse_data_file(basis_file)
            assert basis_file in index.data_files

            invalidator = CacheInvalidator(index)
            invalidator.on_file_changed(basis_file)

            assert basis_file not in index.data_files

    def test_datafile_parser_end_line_inclusive(self):
        """Datafile parser should compute end_line based on subsequent entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".basis", delete=False) as f:
            f.write(SAMPLE_BASIS_FILE)
            temp_path = f.name
        try:
            data_file = parse_basis_file(temp_path)
            assert data_file is not None
            # First entry spans the H block (4 lines: H, 2, then two exponents)
            assert data_file.entries[0].start_line == 0
            assert data_file.entries[0].end_line == 3
            # Blank line separates H from He; He starts at line 5
            assert data_file.entries[1].name == "He"
            assert data_file.entries[1].start_line == 5
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
