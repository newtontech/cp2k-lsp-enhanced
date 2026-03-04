# CP2K Language Server Protocol (Enhanced)

An enhanced Language Server Protocol implementation for CP2K input files, built with TypeScript/Node.js.

## Python LSP Implementation

In addition to the TypeScript/Node.js implementation, this project now includes a Python-based LSP server in `packages/language-server/`:

```bash
# Install the Python LSP
pip install -e packages/language-server

# Run the Python LSP server
cp2k-language-server
```

### Python LSP Features
- **Full LSP Protocol Support** via `pygls`
- **Parser** - Custom lexer and parser for CP2K input files
- **Auto-completion** - Context-aware completions powered by keyword database
- **Diagnostics** - Real-time error detection and reporting
- **Hover** - Documentation on hover for keywords and sections
- **Formatting** - Code formatting with configurable options
- **Code Actions** - Quick fixes for common issues

### Python LSP Architecture
```
packages/language-server/cp2k_lsp/
├── server.py           # Main LSP server
├── parser/
│   ├── lexer.py        # Tokenizer/lexer
│   ├── parser.py       # CP2K input parser
│   ├── ast.py          # AST node definitions
│   └── errors.py       # Error types
├── features/
│   ├── completion.py   # Auto-completion
│   ├── diagnostics.py  # Error diagnostics
│   ├── hover.py        # Hover documentation
│   ├── formatting.py   # Code formatting
│   └── code_action.py  # Quick fixes
└── data/
    ├── keywords.py     # Keyword definitions
    └── sections.py     # Section definitions
```

## TypeScript LSP Implementation

### Features

- **Syntax Highlighting** - Full support for CP2K input file syntax
- **Auto-completion** - Intelligent completions for sections, keywords, and values
- **Error Diagnostics** - Real-time validation of input files
- **Go to Definition** - Navigate to section definitions and variable references
- **Hover Documentation** - Contextual help for keywords and sections
- **Code Formatting** - Automatic formatting with configurable indentation

## Installation

### From npm (when published)

```bash
npm install -g cp2k-lsp-enhanced
```

### From source

```bash
git clone https://github.com/newtontech/cp2k-lsp-enhanced.git
cd cp2k-lsp-enhanced
npm install
npm run build
npm link
```

## Usage

### Command Line

```bash
# Start the language server
cp2k-lsp-enhanced --stdio
```

### VS Code Extension

The language server is designed to work with the OpenQC-VSCode extension.

Add to your VS Code settings:

```json
{
  "cp2k.languageServer.path": "cp2k-lsp-enhanced"
}
```

## Supported CP2K Versions

- CP2K 7.1
- CP2K 8.1
- CP2K 9.1
- CP2K 2025.1

### Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Watch mode
npm run watch

# Run tests
npm test

# Run tests with coverage
npm run test -- --coverage

# Lint
npm run lint

# Format
npm run format
```

### Architecture

```
src/
├── server.ts           # Main LSP server entry
├── parser/
│   ├── cp2k-parser.ts  # CP2K input file parser
│   └── index.ts
├── features/
│   ├── diagnostics.ts  # Error/warning diagnostics
│   ├── completion.ts   # Auto-completion provider
│   ├── hover.ts        # Hover documentation
│   ├── definition.ts   # Go to definition
│   └── formatting.ts   # Code formatting
└── data/
    └── keyword-database.ts  # CP2K keyword definitions
```

### Testing (TypeScript)

The project includes comprehensive unit tests with 78%+ coverage:

```bash
# Run all tests
npm test

# Run with coverage
npm run test -- --coverage

# Run in watch mode
npm run test:watch
```

### Test Coverage (2026-03-02)

| Component | Coverage |
|-----------|----------|
| keyword-database.ts | 98.6% |
| diagnostics.ts | 97.1% |
| definition.ts | 95.2% |
| formatting.ts | 93.3% |
| hover.ts | 90.6% |
| cp2k-parser.ts | 94.6% |
| completion.ts | 82.5% |
| **Overall** | **78.4%** |

### LSP Features (TypeScript)

### Auto-completion
- Section names (e.g., `&GLOBAL`, `&FORCE_EVAL`)
- Keywords within sections
- Allowed values for enumeration keywords
- Context-aware suggestions

### Diagnostics
- Unclosed section detection
- Mismatched section warnings
- Required section validation
- Variable reference validation

### Hover Documentation
- Keyword descriptions
- Data type information
- Default values
- Allowed values

### Go to Definition
- Section definitions
- Variable definitions (`@SET`)
- Include file navigation

### Formatting
- Automatic indentation
- Keyword normalization to uppercase
- Comment preservation
- Directive handling


### Testing (Python)

The Python LSP includes comprehensive tests:

```bash
# Run Python tests
python -m pytest tests/test_lsp_server_full_coverage.py -v

# Run with coverage
python -m pytest tests/ --cov=cp2k_input_tools --cov-report=html
```

#### Test Coverage Goals
- Target: 100% code coverage
- Current: 60%+ (work in progress)
- Key areas: Parser, Lexer, AST, Feature providers

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built on top of the [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- Inspired by the original [cp2k-input-tools](https://github.com/cp2k/cp2k-input-tools) Python implementation
- Uses [vscode-languageserver](https://www.npmjs.com/package/vscode-languageserver) library
