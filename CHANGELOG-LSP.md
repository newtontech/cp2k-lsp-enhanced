# Changelog

All notable changes to the CP2K LSP Enhanced project will be documented in this file.

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
