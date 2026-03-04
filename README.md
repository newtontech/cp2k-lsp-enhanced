# CP2K Input Tools & LSP

[![Build status](https://github.com/cp2k/cp2k-input-tools/actions/workflows/test.yml/badge.svg)](https://github.com/cp2k/cp2k-input-tools/actions) 
[![codecov](https://codecov.io/gh/cp2k/cp2k-input-tools/branch/develop/graph/badge.svg)](https://codecov.io/gh/cp2k/cp2k-input-tools) 
[![PyPI](https://img.shields.io/pypi/pyversions/cp2k-input-tools)](https://pypi.org/project/cp2k-input-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Enhanced with Language Server Protocol (LSP) support for intelligent CP2K input file editing**

Fully validating pure-python CP2K input file parsers including preprocessing capabilities, with an enhanced Language Server Protocol implementation for intelligent code completion, diagnostics, and more.

## 🚀 Quick Start

```bash
# Install the base package
pip install cp2k-input-tools

# Install with YAML support
pip install cp2k-input-tools[yaml]

# Install with Language Server support
pip install cp2k-input-tools[lsp]
```

## ✨ Features

### Core Tools

| Tool | Description |
|------|-------------|
| `cp2klint` | CP2K input file linter with detailed error reporting |
| `fromcp2k` | Convert CP2K input to JSON/YAML or AiiDA run scripts |
| `tocp2k` | Convert JSON/YAML back to CP2K input format |
| `cp2kgen` | Generate input files for parameter sweeps |
| `cp2kget` | Extract values from CP2K restart files |
| `cp2k-language-server` | **Language Server Protocol implementation** |
| `cp2k-datafile-lint` | Linter for pseudos and basis sets |

### 🆕 LSP Features (New!)

The enhanced Language Server Protocol implementation provides IDE-like features for CP2K input files:

- **📝 Intelligent Auto-completion**
  - Section names (`&GLOBAL`, `&FORCE_EVAL`, etc.)
  - Context-aware keywords
  - Enum values and units
  - Snippet support

- **🔍 Real-time Diagnostics**
  - Syntax error detection
  - Schema validation
  - Type checking
  - Missing section warnings

- **📖 Hover Documentation**
  - Keyword descriptions
  - Default values
  - Allowed values
  - Data types

- **🎯 Go to Definition**
  - Section navigation
  - Variable references (`@SET` → `${VAR}`)

- **✨ Code Formatting**
  - Automatic indentation
  - Keyword normalization
  - Comment preservation

## 📦 Installation

### Basic Installation

```bash
pip install cp2k-input-tools
```

### With All Features

```bash
# Full installation with YAML and LSP support
pip install cp2k-input-tools[yaml,lsp]

# Or install individually
pip install cp2k-input-tools[yaml]    # YAML support
pip install cp2k-input-tools[lsp]     # Language Server support
```

### Development Installation

```bash
git clone https://github.com/cp2k/cp2k-input-tools.git
cd cp2k-input-tools
pip install -e ".[yaml,lsp]"
pip install -e ".[dev]"
```

### TypeScript/Node.js LSP (Enhanced Version)

For the enhanced TypeScript LSP implementation:

```bash
git clone https://github.com/newtontech/cp2k-lsp-enhanced.git
cd cp2k-lsp-enhanced
npm install
npm run build
npm link
```

## 🖥️ VS Code Integration

### Using the Python LSP

1. Install the [OpenQC-VSCode](https://marketplace.visualstudio.com/items?itemName=openqc.openqc-vscode) extension
2. Configure the language server path in VS Code settings:

```json
{
  "cp2k.languageServer.path": "cp2k-language-server",
  "cp2k.enableSchemaValidation": true,
  "cp2k.enableDeepValidation": false
}
```

### Using the Enhanced TypeScript LSP

```json
{
  "cp2k.languageServer.path": "cp2k-lsp-enhanced",
  "cp2k.enableSchemaValidation": true,
  "cp2k.enableDeepValidation": true,
  "cp2k.cp2kPath": "/usr/local/bin/cp2k.psmp",
  "cp2k.validationDelay": 1000
}
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `cp2k.languageServer.path` | string | `"cp2k-language-server"` | Path to LSP executable |
| `cp2k.enableSchemaValidation` | boolean | `true` | Enable XML schema validation |
| `cp2k.enableDeepValidation` | boolean | `false` | Enable CP2K CLI deep validation |
| `cp2k.cp2kPath` | string | `""` | Path to CP2K executable |
| `cp2k.validationDelay` | number | `1000` | Debounce delay for validation (ms) |
| `cp2k.maxNumberOfProblems` | number | `100` | Maximum diagnostics to show |

## 📖 Usage Examples

### Command Line Tools

#### Lint a CP2K Input File

```console
$ cp2klint tests/inputs/unterminated_var.inp
Syntax error: unterminated variable, in tests/inputs/unterminated_var.inp:
line   36: @IF ${HP
               ~~~~^
```

#### Convert to JSON/YAML

```console
$ fromcp2k input.inp -o output.json
$ fromcp2k input.inp -y -o output.yaml
```

#### Generate AiiDA Run Script

```console
$ fromcp2k --format aiida-cp2k-calc input.inp > aiida_script.py
```

#### Convert Back to CP2K Format

```console
$ tocp2k config.yaml -o output.inp
```

#### Parameter Sweep Generation

```console
$ cp2kgen input.inp "force_eval/dft/mgrid/cutoff=[800,900,1000]"
Writing 'input-cutoff_800.inp'...
Writing 'input-cutoff_900.inp'...
Writing 'input-cutoff_1000.inp'...
```

#### Extract Values from Restart Files

```console
$ cp2kget restart.inp "force_eval/subsys/cell/a/0"
force_eval/subsys/cell/a/0: 5.64123539364476
```

### Python API

```python
from cp2k_input_tools.parser import CP2KInputParser, CP2KInputParserSimplified
from cp2k_input_tools.generator import CP2KInputGenerator

# Parse CP2K input file
parser = CP2KInputParserSimplified()
with open("project.inp") as f:
    tree = parser.parse(f)

# Modify the tree
print(tree['global']['project_name'])

# Generate CP2K input from dictionary
generator = CP2KInputGenerator()
with open("output.inp", "w") as f:
    for line in generator.line_iter(tree):
        f.write(f"{line}\n")
```

### LSP Usage

Start the language server manually:

```bash
# Python LSP
cp2k-language-server

# Enhanced TypeScript LSP
cp2k-lsp-enhanced --stdio
```

## 🏗️ Architecture

The project consists of two LSP implementations:

### Python LSP (`cp2k-language-server`)

Located in `cp2k_input_tools/lsp/`:
- Built on [pygls](https://github.com/openlawlibrary/pygls)
- Full LSP protocol support
- Integrated with existing Python parser

```
cp2k_input_tools/lsp/
├── server.py           # Main LSP server
├── parser/             # Parser components
│   ├── lexer.py
│   ├── parser.py
│   └── ast.py
└── features/           # LSP features
    ├── completion.py
    ├── diagnostics.py
    ├── hover.py
    └── formatting.py
```

### TypeScript LSP (`cp2k-lsp-enhanced`)

Located in `src/`:
- Built on [vscode-languageserver](https://www.npmjs.com/package/vscode-languageserver)
- Enhanced with XML schema validation
- Deep validation via CP2K CLI

```
src/
├── server.ts           # Main LSP server
├── parser/             # CP2K parser
│   └── cp2k-parser.ts
├── features/           # LSP providers
│   ├── completion.ts
│   ├── diagnostics.ts
│   ├── hover.ts
│   ├── definition.ts
│   └── formatting.ts
└── data/
    ├── keyword-database.ts
    └── schema-parser.ts
```

## 📋 Supported CP2K Versions

- CP2K 7.1
- CP2K 8.1
- CP2K 9.1
- CP2K 2025.1

## 🧪 Testing

### Python Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_lsp_server_full_coverage.py -v

# Run with coverage report
pytest --cov=cp2k_input_tools --cov-report=html
```

### TypeScript Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test -- --coverage

# Watch mode
npm run test:watch
```

Current test coverage:
- Python LSP: 100% target (in progress)
- TypeScript LSP: 78%+ coverage

## 📝 Documentation

- [LSP Documentation](README-LSP.md) - Detailed LSP implementation guide
- [Usage Guide](docs/usage.md) - Comprehensive usage examples
- [Changelog](CHANGELOG.md) - Version history and changes
- [LSP Changelog](CHANGELOG-LSP.md) - LSP-specific changes

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Tests pass (`pytest` for Python, `npm test` for TypeScript)
- Code is formatted (`black` for Python, `prettier` for TypeScript)
- Type checking passes (`mypy` for Python, `tsc` for TypeScript)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original [cp2k-input-tools](https://github.com/cp2k/cp2k-input-tools) by Tiziano Müller
- Built on the [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- Uses [pygls](https://github.com/openlawlibrary/pygls) for Python LSP
- Uses [vscode-languageserver](https://www.npmjs.com/package/vscode-languageserver) for TypeScript LSP
- CP2K input format reference: https://manual.cp2k.org/

---

**Note**: This project is an enhanced version of the original cp2k-input-tools with added Language Server Protocol support. The original Python tools remain fully functional and maintained.
