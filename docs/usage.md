# CP2K-LSP Usage Guide

Comprehensive guide for using the CP2K Language Server Protocol implementation.

## Table of Contents

1. [Installation](#installation)
2. [Getting Started](#getting-started)
3. [Command Line Tools](#command-line-tools)
4. [VS Code Integration](#vs-code-integration)
5. [Python API](#python-api)
6. [LSP Configuration](#lsp-configuration)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

## Installation

### Python Package

```bash
# Basic installation
pip install cp2k-input-tools

# With YAML support
pip install cp2k-input-tools[yaml]

# With LSP support
pip install cp2k-input-tools[lsp]

# Full installation
pip install cp2k-input-tools[yaml,lsp]
```

### TypeScript LSP (Enhanced)

```bash
git clone https://github.com/newtontech/cp2k-lsp-enhanced.git
cd cp2k-lsp-enhanced
npm install
npm run build
npm link
```

## Getting Started

### Verify Installation

```bash
# Check Python tools
cp2klint --help
fromcp2k --help

# Check LSP server
cp2k-language-server --help

# Check TypeScript LSP (if installed)
cp2k-lsp-enhanced --help
```

### Quick Test

Create a test file `test.inp`:

```cp2k
&GLOBAL
  PROJECT_NAME test
  RUN_TYPE ENERGY
&END GLOBAL

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_SET
    POTENTIAL_FILE_NAME POTENTIAL
  &END DFT
&END FORCE_EVAL
```

Run the linter:

```bash
cp2klint test.inp
```

## Command Line Tools

### cp2klint - Input File Linter

Validate CP2K input files:

```bash
# Basic usage
cp2klint input.inp

# Check multiple files
cp2klint *.inp

# With verbose output
cp2klint -v input.inp
```

### fromcp2k - Convert to JSON/YAML

Convert CP2K input to structured formats:

```bash
# Convert to JSON
fromcp2k input.inp -o output.json

# Convert to YAML
fromcp2k input.inp -y -o output.yaml

# Canonical format
fromcp2k input.inp -c -o output.json

# Generate AiiDA script
fromcp2k --format aiida-cp2k-calc input.inp > run_calc.py
```

### tocp2k - Convert from JSON/YAML

Convert structured formats back to CP2K input:

```bash
# From JSON
tocp2k config.json -o input.inp

# From YAML
tocp2k config.yaml -y -o input.inp
```

### cp2kgen - Parameter Sweep Generator

Generate input files for parameter studies:

```bash
# Single parameter sweep
cp2kgen input.inp "force_eval/dft/mgrid/cutoff=[400,600,800,1000]"

# Multiple parameters (Cartesian product)
cp2kgen input.inp \
  "force_eval/dft/mgrid/cutoff=[400,600]" \
  "force_eval/dft/scf/eps_scf=[1e-6,1e-7]"

# With output prefix
cp2kgen input.inp "global/print_level=[LOW,MEDIUM,HIGH]" --prefix study
```

### cp2kget - Extract Values

Get values from CP2K restart files:

```bash
# Get cell parameter
cp2kget restart.inp "force_eval/subsys/cell/a/0"

# Get multiple values
cp2kget restart.inp "force_eval/subsys/cell/a/0"
cp2kget restart.inp "force_eval/subsys/cell/b/0"

# Get from JSON output
fromcp2k restart.inp | jq '.force_eval[0].subsys.cell.A'
```

### cp2k-language-server - LSP Server

Start the language server:

```bash
# Default (stdio mode)
cp2k-language-server

# TCP mode
cp2k-language-server --tcp --port 12345

# With verbose logging
cp2k-language-server -v
```

## VS Code Integration

### Installing the Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "OpenQC-VSCode"
4. Click Install

### Basic Configuration

Open VS Code settings (Ctrl+,) and add:

```json
{
  "cp2k.languageServer.path": "cp2k-language-server",
  "cp2k.enableSchemaValidation": true
}
```

### Advanced Configuration

```json
{
  "cp2k": {
    "languageServer": {
      "path": "cp2k-lsp-enhanced",
      "args": ["--stdio"]
    },
    "enableSchemaValidation": true,
    "enableDeepValidation": true,
    "cp2kPath": "/usr/local/bin/cp2k.psmp",
    "validationDelay": 1000,
    "maxNumberOfProblems": 100,
    "formatting": {
      "indentSize": 2,
      "useTabs": false,
      "normalizeKeywords": true
    }
  }
}
```

### Using LSP Features

#### Auto-completion

1. Type `&` to see section completions
2. Type inside a section to see keyword completions
3. Press Ctrl+Space to trigger completions manually

#### Diagnostics

Errors and warnings appear automatically as you type:

- Red squiggles: Syntax errors
- Yellow squiggles: Warnings
- Blue squiggles: Information

Hover over diagnostics to see details.

#### Hover Documentation

Hover over any keyword to see:

- Description
- Data type
- Default value
- Allowed values

#### Go to Definition

- Ctrl+Click on a section to navigate to its definition
- Ctrl+Click on `${VAR}` to go to `@SET VAR`

#### Formatting

- Format document: Shift+Alt+F
- Format selection: Ctrl+K Ctrl+F

## Python API

### Parsing Input Files

```python
from cp2k_input_tools.parser import CP2KInputParserSimplified

parser = CP2KInputParserSimplified()

with open("input.inp") as f:
    tree = parser.parse(f)

# Access data
print(tree['global']['project_name'])
print(tree['force_eval']['method'])
```

### Generating Input Files

```python
from cp2k_input_tools.generator import CP2KInputGenerator

generator = CP2KInputGenerator()

tree = {
    "global": {
        "project_name": "my_calculation",
        "run_type": "GEO_OPT"
    },
    "force_eval": {
        "method": "Quickstep",
        "dft": {
            "basis_set_file_name": "BASIS_SET",
            "potential_file_name": "POTENTIAL"
        }
    }
}

with open("output.inp", "w") as f:
    for line in generator.line_iter(tree):
        f.write(f"{line}\n")
```

### Working with Units

```python
from cp2k_input_tools.parser import CP2KInputParserSimplified

parser = CP2KInputParserSimplified()

with open("input.inp") as f:
    tree = parser.parse(f)

# Access cell with unit conversion
cell_a = tree['force_eval']['subsys']['cell']['A']
print(f"Cell A: {cell_a} angstrom")
```

## LSP Configuration

### Python LSP Configuration

Configure via initialization options:

```json
{
  "initializationOptions": {
    "parser": {
      "canonical": false,
      "simplified": true
    },
    "completion": {
      "snippetSupport": true,
      "triggerCharacters": ["&", " ", "\n", "_", "/"]
    },
    "diagnostics": {
      "enable": true,
      "maxProblems": 100
    },
    "formatting": {
      "indentSize": 2,
      "useTabs": false,
      "normalizeKeywords": true,
      "normalizeSections": true
    }
  }
}
```

### TypeScript LSP Configuration

Configure via settings:

```json
{
  "cp2k": {
    "languageServer": {
      "path": "cp2k-lsp-enhanced"
    },
    "enableSchemaValidation": true,
    "enableDeepValidation": false,
    "cp2kPath": "",
    "validationDelay": 1000,
    "maxNumberOfProblems": 100,
    "schemaCachePath": "data/cp2k-schema-cache.json",
    "formatting": {
      "indentSize": 2,
      "useTabs": false,
      "normalizeKeywords": true,
      "normalizeSections": true,
      "preserveComments": true
    }
  }
}
```

## Examples

### Example 1: Complete DFT Calculation

```cp2k
&GLOBAL
  PROJECT_NAME Si_bulk
  RUN_TYPE ENERGY
  PRINT_LEVEL MEDIUM
&END GLOBAL

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    BASIS_SET_FILE_NAME BASIS_MOLOPT
    POTENTIAL_FILE_NAME GTH_POTENTIALS
    
    &MGRID
      CUTOFF 400
      REL_CUTOFF 50
      NGRIDS 4
    &END MGRID
    
    &QS
      EPS_DEFAULT 1.0E-12
      WF_INTERPOLATION PS
      EXTRAPOLATION ASPC
    &END QS
    
    &SCF
      SCF_GUESS ATOMIC
      EPS_SCF 1.0E-6
      MAX_SCF 50
      &DIAGONALIZATION
        ALGORITHM STANDARD
      &END DIAGONALIZATION
    &END SCF
    
    &XC
      &XC_FUNCTIONAL PBE
      &END XC_FUNCTIONAL
    &END XC
  &END DFT
  
  &SUBSYS
    &CELL
      A 5.43 0.00 0.00
      B 0.00 5.43 0.00
      C 0.00 0.00 5.43
      PERIODIC XYZ
    &END CELL
    
    &TOPOLOGY
      COORD_FILE_NAME Si.xyz
      COORD_FILE_FORMAT XYZ
    &END TOPOLOGY
    
    &KIND Si
      ELEMENT Si
      BASIS_SET DZVP-MOLOPT-GTH
      POTENTIAL GTH-PBE-q4
    &END KIND
  &END SUBSYS
&END FORCE_EVAL
```

### Example 2: Geometry Optimization

```cp2k
&GLOBAL
  PROJECT_NAME geo_opt
  RUN_TYPE GEO_OPT
&END GLOBAL

&MOTION
  &GEO_OPT
    OPTIMIZER BFGS
    MAX_ITER 200
    MAX_DR 1.0E-3
    RMS_DR 5.0E-4
    MAX_FORCE 1.0E-4
    RMS_FORCE 5.0E-5
  &END GEO_OPT
&END MOTION

&FORCE_EVAL
  METHOD Quickstep
  &DFT
    # ... DFT settings ...
  &END DFT
  &SUBSYS
    # ... structure ...
  &END SUBSYS
&END FORCE_EVAL
```

### Example 3: Molecular Dynamics

```cp2k
&GLOBAL
  PROJECT_NAME md_run
  RUN_TYPE MD
&END GLOBAL

&MOTION
  &MD
    ENSEMBLE NVT
    STEPS 10000
    TIMESTEP 0.5
    TEMPERATURE 300.0
    &THERMOSTAT
      &NOSE
        LENGTH 3
        YOSHIDA 3
        TIMECON 100.0
        MTS 2
      &END NOSE
    &END THERMOSTAT
  &END MD
&END MOTION
```

## Troubleshooting

### LSP Server Not Starting

**Problem:** VS Code shows "LSP server failed to start"

**Solutions:**
1. Verify LSP is installed: `which cp2k-language-server`
2. Check the path in VS Code settings
3. Try running manually: `cp2k-language-server --stdio`
4. Check the VS Code Output panel for error messages

### No Completions Appearing

**Problem:** Auto-completion doesn't work

**Solutions:**
1. Ensure file is recognized as CP2K: Check status bar shows "CP2K"
2. Manually trigger with Ctrl+Space
3. Check LSP server is running in Output panel
4. Verify schema validation is enabled

### Deep Validation Not Working

**Problem:** No errors from CP2K validation

**Solutions:**
1. Verify CP2K is installed: `which cp2k.psmp`
2. Check cp2kPath setting is correct
3. Enable enableDeepValidation: true
4. Check CP2K supports `-c` flag: `cp2k.psmp -c test.inp`

### Schema Cache Issues

**Problem:** Schema validation shows incorrect errors

**Solutions:**
1. Delete cache: `rm data/cp2k-schema-cache.json`
2. Restart LSP server
3. Verify CP2K path for schema generation
4. Check CP2K supports `--xml` flag

### Performance Issues

**Problem:** LSP is slow

**Solutions:**
1. Disable deep validation if not needed
2. Increase validationDelay
3. Reduce maxNumberOfProblems
4. Check CPU usage of CP2K processes

### Getting Help

1. Check [GitHub Issues](https://github.com/cp2k/cp2k-input-tools/issues)
2. Review [LSP Documentation](../README-LSP.md)
3. Enable verbose logging: `cp2k-language-server -v`
4. Check VS Code Output panel for errors

---

For more information, see:
- [Main README](../README.md)
- [LSP README](../README-LSP.md)
- [Changelog](../CHANGELOG.md)
