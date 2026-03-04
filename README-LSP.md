# CP2K Language Server Protocol (LSP) Enhanced

An enhanced Language Server Protocol implementation for CP2K input files, providing IDE-like features for editing CP2K input files.

## 🌟 Overview

This project provides two Language Server Protocol implementations for CP2K input files:

1. **Python LSP** (`cp2k-language-server`) - Built on pygls, integrated with the existing Python parser
2. **TypeScript/Node.js LSP** (`cp2k-lsp-enhanced`) - Built on vscode-languageserver, with enhanced schema validation

## ✨ LSP Features

### Core LSP Capabilities

| Feature | Python LSP | TypeScript LSP | Description |
|---------|------------|----------------|-------------|
| Text Document Sync | ✅ | ✅ | Full document synchronization |
| Diagnostics | ✅ | ✅ | Real-time error/warning detection |
| Completion | ✅ | ✅ | Auto-completion for sections, keywords, values |
| Hover | ✅ | ✅ | Documentation on hover |
| Definition | ✅ | ✅ | Go to definition for sections and variables |
| Formatting | ✅ | ✅ | Code formatting with options |
| Code Actions | ✅ | ✅ | Quick fixes for common issues |

### Enhanced Features (TypeScript LSP)

| Feature | Description |
|---------|-------------|
| **XML Schema Validation** | Parse CP2K's official XML schema for accurate validation |
| **Deep Validation** | Integration with CP2K CLI for native syntax checking |
| **Unit Completion** | Smart completion for physical units (angstrom, eV, etc.) |
| **Schema Caching** | Cached schema for fast startup |
| **Debounced Validation** | Optimized validation to avoid excessive CP2K calls |

## 🐍 Python LSP Implementation

### Installation

```bash
# Install from PyPI
pip install cp2k-input-tools[lsp]

# Or install from source
pip install -e ".[lsp]"
```

### Running the Server

```bash
# Start the LSP server
cp2k-language-server

# Or run as a module
python -m cp2k_input_tools.lsp
```

### Architecture

```
cp2k_input_tools/
└── lsp/
    ├── __init__.py
    ├── server.py              # Main LSP server entry point
    ├── parser/
    │   ├── __init__.py
    │   ├── lexer.py           # Tokenizer/lexer for CP2K input
    │   ├── parser.py          # CP2K input parser
    │   ├── ast.py             # AST node definitions
    │   └── errors.py          # Error types and handling
    ├── features/
    │   ├── __init__.py
    │   ├── completion.py      # Auto-completion provider
    │   ├── diagnostics.py     # Error diagnostics
    │   ├── hover.py           # Hover documentation
    │   ├── formatting.py      # Code formatting
    │   └── code_action.py     # Quick fixes
    └── data/
        ├── keywords.py        # Keyword definitions
        └── sections.py        # Section definitions
```

### Features

#### 1. Parser

Custom lexer and parser for CP2K input files:

```python
from cp2k_input_tools.lsp.parser import CP2KLexer, CP2KParser

# Lexing
lexer = CP2KLexer()
tokens = lexer.tokenize("&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL")

# Parsing
parser = CP2KParser()
ast = parser.parse("&GLOBAL\n  PROJECT_NAME test\n&END GLOBAL")
```

**Components:**
- `lexer.py`: Tokenizes CP2K input into tokens (SECTION, KEYWORD, VALUE, etc.)
- `parser.py`: Builds AST from tokens
- `ast.py`: AST node definitions (Section, Keyword, Value, etc.)
- `errors.py`: Custom error types for parsing

#### 2. Completion Provider

Context-aware auto-completion:

```python
from cp2k_input_tools.lsp.features.completion import CompletionProvider

provider = CompletionProvider()
completions = provider.get_completions(document, position)
```

**Completion Types:**
- Section completions: `&GLO` → `&GLOBAL`
- Keyword completions: Section-specific keywords
- Value completions: Enum values, booleans, units
- Snippet completions: Section templates

#### 3. Diagnostics Provider

Real-time error detection:

```python
from cp2k_input_tools.lsp.features.diagnostics import DiagnosticsProvider

provider = DiagnosticsProvider()
diagnostics = provider.get_diagnostics(document)
```

**Diagnostic Types:**
- Syntax errors (unclosed sections, mismatched names)
- Missing required sections (GLOBAL, FORCE_EVAL)
- Type mismatches
- Unknown keywords
- Variable reference errors

#### 4. Hover Provider

Documentation on hover:

```python
from cp2k_input_tools.lsp.features.hover import HoverProvider

provider = HoverProvider()
hover_info = provider.get_hover(document, position)
```

**Hover Information:**
- Section descriptions
- Keyword types and defaults
- Allowed values for enums
- Data type information

#### 5. Formatting Provider

Code formatting:

```python
from cp2k_input_tools.lsp.features.formatting import FormattingProvider

provider = FormattingProvider()
edits = provider.format_document(document, options)
```

**Formatting Options:**
- Indent size (default: 2 spaces)
- Use tabs vs spaces
- Keyword uppercase normalization
- Section name uppercase normalization
- Value alignment

#### 6. Code Actions

Quick fixes for common issues:

```python
from cp2k_input_tools.lsp.features.code_action import CodeActionProvider

provider = CodeActionProvider()
actions = provider.get_code_actions(document, range, context)
```

**Code Actions:**
- Fix unclosed sections
- Add missing required sections
- Normalize keyword case
- Remove unused variables

### Testing

```bash
# Run all Python LSP tests
pytest tests/test_lsp_server_full_coverage.py -v

# Run with coverage
pytest tests/ --cov=cp2k_input_tools.lsp --cov-report=html

# Run specific test categories
pytest tests/test_lsp_server_full_coverage.py::test_server_initialization -v
pytest tests/test_lsp_server_full_coverage.py::test_parser -v
pytest tests/test_lsp_server_full_coverage.py::test_lexer -v
```

### Configuration

Python LSP can be configured via initialization options:

```json
{
  "initializationOptions": {
    "parser": {
      "canonical": false,
      "simplified": true
    },
    "completion": {
      "snippetSupport": true
    },
    "formatting": {
      "indentSize": 2,
      "useTabs": false,
      "normalizeKeywords": true
    }
  }
}
```

## 📘 TypeScript LSP Implementation

### Installation

```bash
git clone https://github.com/newtontech/cp2k-lsp-enhanced.git
cd cp2k-lsp-enhanced
npm install
npm run build
npm link
```

### Running the Server

```bash
# Start the LSP server
cp2k-lsp-enhanced --stdio

# Or via npm
npm start
```

### Architecture

```
src/
├── server.ts                    # Main LSP server
├── parser/
│   ├── cp2k-parser.ts          # CP2K input parser
│   └── index.ts
├── features/
│   ├── completion.ts           # Enhanced completion provider
│   ├── diagnostics.ts          # Enhanced diagnostics
│   ├── deep-validation.ts      # CP2K CLI integration
│   ├── hover.ts                # Hover provider
│   ├── definition.ts           # Definition provider
│   └── formatting.ts           # Formatting provider
└── data/
    ├── keyword-database.ts     # Keyword definitions
    └── schema-parser.ts        # XML schema parser
```

### Features

#### 1. XML Schema Parser

Parses CP2K's official XML schema for accurate validation:

```typescript
import { SchemaParser } from './data/schema-parser';

const parser = new SchemaParser();
const schema = parser.parse(cp2kXmlOutput);
```

**Features:**
- Automatic schema generation from CP2K (`cp2k --xml`)
- Schema caching for fast startup
- Comprehensive metadata extraction:
  - Sections and subsections
  - Keywords with types and defaults
  - Allowed enum values
  - Units
  - Repetition flags
  - Deprecated status
  - Required flags
  - Mutually exclusive constraints

**Schema Cache:**
- Location: `data/cp2k-schema-cache.json`
- Automatically regenerated when outdated
- Can be manually regenerated by deleting the cache

#### 2. Enhanced Diagnostics

Comprehensive validation beyond basic syntax:

**Validation Types:**

| Diagnostic Code | Description |
|-----------------|-------------|
| `missing-section` | Required section missing (GLOBAL, FORCE_EVAL) |
| `missing-keyword` | Required keyword missing |
| `missing-subsection` | Required subsection missing |
| `unknown-keyword` | Keyword not found in schema |
| `invalid-value` | Value doesn't match allowed values |
| `type-mismatch` | Value doesn't match expected type |
| `mutual-exclusion` | Mutually exclusive keywords present |
| `deprecated-section` | Section is deprecated |
| `deprecated-keyword` | Keyword is deprecated |

#### 3. Enhanced Completion

Intelligent code completion:

**Completion Types:**

| Trigger | Completion |
|---------|------------|
| `&` or section prefix | Section completions with snippets |
| Line start in section | Context-aware keyword completions |
| After keywords | Enum values, booleans |
| After numbers | Physical units |

**Unit Completions:**

| Category | Units |
|----------|-------|
| Length | `angstrom`, `bohr`, `nm`, `pm`, `m` |
| Energy | `hartree`, `eV`, `kcalmol`, `kJmol`, `Ry`, `J` |
| Time | `fs`, `ps`, `s` |
| Temperature | `K` |
| Pressure | `bar`, `atm`, `Pa`, `GPa` |
| Mass | `amu` |
| Angle | `deg`, `rad` |
| Force | `hartree/bohr` |

#### 4. Deep Validation

Integration with CP2K CLI for native syntax checking:

```typescript
import { DeepValidationProvider } from './features/deep-validation';

const validator = new DeepValidationProvider(cp2kPath);
const diagnostics = await validator.validate(document);
```

**Features:**
- Real-time syntax validation using CP2K's parser
- Captures errors, warnings, and information
- Parses CP2K error messages into LSP diagnostics
- Debounced to avoid excessive CP2K invocations
- Configurable timeout and executable path

#### 5. Go to Definition

Navigate to definitions:

- Section definitions: Click on `&END GLOBAL` → Go to `&GLOBAL`
- Variable definitions: Click on `${VAR}` → Go to `@SET VAR`
- Include file navigation

#### 6. Code Formatting

Automatic code formatting:

```typescript
import { FormattingProvider } from './features/formatting';

const formatter = new FormattingProvider(options);
const edits = formatter.formatDocument(document);
```

**Options:**
- `indentSize`: Number of spaces for indentation (default: 2)
- `useTabs`: Use tabs instead of spaces (default: false)
- `normalizeKeywords`: Convert keywords to uppercase (default: true)
- `normalizeSections`: Convert section names to uppercase (default: true)

### Testing

```bash
# Run all tests
npm test

# Run with coverage
npm run test -- --coverage

# Run in watch mode
npm run test:watch

# Run specific tests
npm test -- --testNamePattern="completion"
```

Current test coverage (as of 2026-03-04):

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

### Configuration

TypeScript LSP configuration options:

```json
{
  "cp2k": {
    "languageServer.path": "cp2k-lsp-enhanced",
    "enableSchemaValidation": true,
    "enableDeepValidation": false,
    "cp2kPath": "/usr/local/bin/cp2k.psmp",
    "validationDelay": 1000,
    "maxNumberOfProblems": 100,
    "formatting": {
      "indentSize": 2,
      "useTabs": false,
      "normalizeKeywords": true,
      "normalizeSections": true
    }
  }
}
```

## 🆚 Comparison: Python vs TypeScript LSP

| Aspect | Python LSP | TypeScript LSP |
|--------|------------|----------------|
| **Best For** | Python ecosystem integration | VS Code, enhanced features |
| **Performance** | Fast (pure Python) | Fast with caching |
| **Schema Validation** | Based on keyword database | Based on CP2K XML schema |
| **Deep Validation** | Not available | CP2K CLI integration |
| **Unit Completions** | Basic | Comprehensive |
| **Startup Time** | Fast | Fast (with cache) |
| **Memory Usage** | Lower | Slightly higher |
| **Test Coverage** | 100% target | 78%+ |

## 🔧 Editor Integration

### VS Code

1. Install [OpenQC-VSCode](https://marketplace.visualstudio.com/items?itemName=openqc.openqc-vscode) extension
2. Configure the language server in settings

### Vim/Neovim

Using [ALE](https://github.com/dense-analysis/ale):

```vim
" Create ale_linters/cp2k/language_server.vim
call ale#Set('cp2k_lsp_executable', 'cp2k-language-server')

function! ale_linters#cp2k#language_server#GetProjectRoot(buffer) abort
  let l:git_path = ale#path#FindNearestDirectory(a:buffer, '.git')
  return !empty(l:git_path) ? fnamemodify(l:git_path, ':h:h') : ''
endfunction

call ale#linter#Define('cp2k', {
\   'name': 'language_server',
\   'lsp': 'stdio',
\   'executable': {b -> ale#Var(b, 'cp2k_lsp_executable')},
\   'project_root': function('ale_linters#cp2k#language_server#GetProjectRoot'),
\   'command': '%e',
\})
```

Then set filetype: `:set filetype=cp2k`

### Emacs

Using [lsp-mode](https://github.com/emacs-lsp/lsp-mode):

```elisp
(require 'lsp-mode)

(add-to-list 'lsp-language-id-configuration '(cp2k-mode . "cp2k"))

(lsp-register-client
 (make-lsp-client :new-connection (lsp-stdio-connection "cp2k-language-server")
                  :major-modes '(cp2k-mode)
                  :server-id 'cp2k-lsp))
```

## 📊 Performance

| Operation | Python LSP | TypeScript LSP |
|-----------|------------|----------------|
| Schema validation | < 10ms | < 10ms (cached) |
| Deep validation | N/A | 100-500ms (debounced) |
| Completion | < 5ms | < 5ms |
| Hover | < 5ms | < 5ms |
| Formatting | < 50ms | < 50ms |

## 📝 LSP Protocol Version

Both implementations support **LSP Protocol 3.17**:
- `textDocument/didOpen`
- `textDocument/didChange`
- `textDocument/didClose`
- `textDocument/didSave`
- `textDocument/completion`
- `textDocument/hover`
- `textDocument/definition`
- `textDocument/formatting`
- `textDocument/codeAction`
- `textDocument/publishDiagnostics`

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Make changes with tests
4. Ensure tests pass
5. Submit a Pull Request

### Development Setup

**Python LSP:**
```bash
cd cp2k_input_tools
pip install -e ".[lsp,dev]"
pytest tests/test_lsp_server_full_coverage.py
```

**TypeScript LSP:**
```bash
cd cp2k-lsp-enhanced
npm install
npm run build
npm test
```

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Original [cp2k-input-tools](https://github.com/cp2k/cp2k-input-tools)
- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [pygls](https://github.com/openlawlibrary/pygls) for Python LSP
- [vscode-languageserver](https://www.npmjs.com/package/vscode-languageserver) for TypeScript LSP
