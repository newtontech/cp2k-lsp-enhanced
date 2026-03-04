# Changelog

All notable changes to the CP2K LSP Enhanced project will be documented in this file.

## [1.4.0] - 2026-03-04 (Current)

### Fixed
- #72: X..Y range parsing for LIST keywords - IntegerRange objects now correctly parsed and preserved
- #110: NumPy 2 compatibility - Verified working with numpy 2.2.6 and pint 0.24.4
- Fixed unit tests for LSP server workspace mocking
- Fixed comment tokenization test to match lexer behavior
- Fixed canonical mode path lookup in test suite (lowercase keys)

### Added
- Comprehensive LSP server tests in `tests/test_lsp_server_full_coverage.py`
  - Server initialization tests
  - Parser tests with mock workspace
  - Lexer tests for all token types
  - AST node tests
  - Error handling tests
  - Keyword and section data tests
- Extended keyword helpers tests for IntegerRange functionality
- Issue regression tests for #72 and #111

### Improved
- LSP server test stability with proper pygls workspace mocking
- Test coverage for language server components
- Better error handling in test suite

### Technical
- Python 3.9+ compatibility maintained
- pytest + pytest-cov for 100% coverage goal
- pygls 1.0+ for LSP implementation
- Pydantic v2 validated

## [1.0.0] - 2025-03-02

### Added
- Initial TypeScript/Node.js implementation of CP2K Language Server
- Full LSP protocol support via vscode-languageserver
- CP2K input file parser with section/keyword/token detection
- Diagnostics provider with validation for:
  - Unclosed sections
  - Mismatched section names
  - Missing GLOBAL/FORCE_EVAL warnings
  - Empty variable references
  - Unbalanced parentheses/brackets
- Auto-completion provider with:
  - Section completions (&GLOBAL, &FORCE_EVAL, etc.)
  - Keyword completions based on section context
  - Enum value completions for known keywords
  - Snippet support for sections
- Hover provider with documentation for:
  - Sections (description, keywords, subsections)
  - Keywords (type, default value, allowed values)
  - Common values (TRUE, FALSE, ENERGY, etc.)
- Go to definition support for:
  - Section references
  - Variable references (${VAR} to @SET definition)
- Code formatting with:
  - Automatic indentation
  - Keyword uppercase normalization
  - Section name uppercase normalization
  - Value alignment
  - Configurable tabs vs spaces
- Comprehensive keyword database covering:
  - GLOBAL section keywords
  - FORCE_EVAL/DFT section keywords
  - SCF settings
  - QS method options
  - MGRID parameters
  - KIND definitions
  - CELL parameters
  - MD settings
  - GEO_OPT options
  - KPOINTS sampling
  - TOPOLOGY options
  - XC functionals
  - POISSON solver
- Full test suite with:
  - Parser tests
  - Completion provider tests
  - Hover provider tests
  - Diagnostics provider tests
  - Definition provider tests
  - Formatting provider tests
- TypeScript configuration with strict type checking
- Jest testing framework setup
- ESLint and Prettier configuration

### Supported CP2K Versions
- CP2K 7.1
- CP2K 8.1  
- CP2K 9.1
- CP2K 2025.1

### Technical Stack
- TypeScript 5.3
- Node.js 18+
- vscode-languageserver 9.0
- Jest 29.7
- ESLint 8.56

## [1.1.0] - 2026-03-02

### Added
- Comprehensive test suite with 111 tests (74%+ coverage)
- Extended tests for keyword database
- Extended tests for completion provider
- Extended tests for hover provider
- Extended tests for definition provider
- Extended tests for formatting provider
- Server document handling tests

### Improved
- Test coverage increased from 54% to 74%
- Better test organization with extended test files
- More comprehensive edge case testing

### Technical
- All tests passing
- TypeScript compilation successful
- ESLint clean


## [1.4.0] - 2026-03-04 (Current)

### Fixed
- #72: X..Y range parsing for LIST keywords - IntegerRange objects now correctly parsed and preserved
- #110: NumPy 2 compatibility - Verified working with numpy 2.2.6 and pint 0.24.4
- Fixed unit tests for LSP server workspace mocking
- Fixed comment tokenization test to match lexer behavior
- Fixed canonical mode path lookup in test suite (lowercase keys)

### Added
- Comprehensive LSP server tests in `tests/test_lsp_server_full_coverage.py`
  - Server initialization tests
  - Parser tests with mock workspace
  - Lexer tests for all token types
  - AST node tests
  - Error handling tests
  - Keyword and section data tests
- Extended keyword helpers tests for IntegerRange functionality
- Issue regression tests for #72 and #111

### Improved
- LSP server test stability with proper pygls workspace mocking
- Test coverage for language server components
- Better error handling in test suite

### Technical
- Python 3.9+ compatibility maintained
- pytest + pytest-cov for 100% coverage goal
- pygls 1.0+ for LSP implementation
- Pydantic v2 validated

## [1.2.0] - 2026-03-04

### Added
- Python LSP feature providers implemented
- 40+ Python unit test files added
- Documentation updated
