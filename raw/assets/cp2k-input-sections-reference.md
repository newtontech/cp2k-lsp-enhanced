> Source: https://manual.cp2k.org/trunk/CP2K_INPUT.html
> Additional: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html, https://www.cp2k.org/input_file

# CP2K Input Sections Reference

## Overview

CP2K input files use a hierarchical section-keyword structure. The top-level input reference
organizes all configurable sections in a tree. This document catalogs the complete section
hierarchy and key parameters as of CP2K version 2026.1.

## Top-Level Sections

The CP2K input file is organized into the following top-level sections:

### ATOM
Atomic calculations for generating pseudopotentials and basis sets.
- Subsections: AE_BASIS, METHOD, OPTIMIZATION, POTENTIAL, POWELL, PP_BASIS, PRINT, REFERENCE

### DEBUG
Debugging and diagnostic output.
- Subsections: PROGRAM_RUN_INFO

### EXT_RESTART
External restart configuration for continuing calculations.

### FARMING
Farming/embarrassingly parallel job management.
- Subsections: JOB, PROGRAM_RUN_INFO, RESTART

### FORCE_EVAL
**Core section** for energy and force calculations. This is the heart of any CP2K input file.
Can be repeated. Contains all parameters needed to calculate energy and forces and describe the system.

### GLOBAL
Global simulation parameters.
- Subsections: DBCSR, FM, FM_DIAG_SETTINGS, GRID, PRINT, PROGRAM_RUN_INFO, REFERENCES, TIMINGS

### MOTION
Molecular dynamics, geometry optimization, and other nuclear motion methods.
- Subsections: BAND, CELL_OPT, CONSTRAINT, DRIVER, FLEXIBLE_PARTITIONING, FREE_ENERGY, GEO_OPT, MC, MD, PINT, PRINT, SHELL_OPT, TMC

### MULTIPLE_FORCE_EVALS
Combining multiple FORCE_EVAL sections with specified ordering.

### NEGF
Non-equilibrium Green's function transport calculations.
- Subsections: CONTACT, MIXING, PRINT, SCATTERING_REGION, SCF

### OPTIMIZE_BASIS
Basis set optimization.
- Subsections: FIT_KIND, OPTIMIZATION, TRAINING_FILES

### OPTIMIZE_INPUT
Input parameter optimization via force matching.
- Subsections: FORCE_MATCHING, HISTORY, RESTART, VARIABLE

### SWARM
Global optimization via swarm methods.
- Subsections: GLOBAL_OPT, PRINT

### TEST
Internal testing and benchmarking sections.

### VIBRATIONAL_ANALYSIS
Frequency and vibrational mode calculations.
- Subsections: MODE_SELECTIVE, PRINT

## FORCE_EVAL Section Hierarchy

The FORCE_EVAL section is the most important and complex section. Full hierarchy:

```
FORCE_EVAL
├── BSSE                    # Basis set superposition error
│   ├── CONFIGURATION
│   ├── FRAGMENT
│   ├── FRAGMENT_ENERGIES
│   └── PRINT
├── DFT                     # Density Functional Theory settings
│   ├── ACTIVE_SPACE
│   ├── ALMO_SCF
│   ├── AUXILIARY_DENSITY_MATRIX_METHOD
│   ├── DENSITY_FITTING
│   ├── EFIELD
│   ├── ENERGY_CORRECTION
│   ├── EXCITED_STATES
│   ├── EXTERNAL_DENSITY
│   ├── EXTERNAL_POTENTIAL
│   ├── EXTERNAL_VXC
│   ├── HAIRY_PROBES
│   ├── HARRIS_METHOD
│   ├── KG_METHOD
│   ├── KPOINTS
│   ├── KPOINT_SET
│   ├── LOCALIZE
│   ├── LOW_SPIN_ROKS
│   ├── LS_SCF
│   ├── MGRID               # Multigrid plane wave settings
│   ├── PERIODIC_EFIELD
│   ├── PLANAR_AVERAGED_V_HARTREE
│   ├── PLANAR_COUNTER_CHARGE
│   ├── POISSON
│   ├── PRINT
│   ├── QS                   # Quickstep module parameters
│   ├── REAL_TIME_PROPAGATION
│   ├── RELATIVISTIC
│   ├── SCCS
│   ├── SCF                  # Self-consistent field settings
│   ├── SCRF
│   ├── SIC
│   ├── SMEAGOL
│   ├── TRANSPORT
│   ├── XAS
│   ├── XAS_TDP
│   └── XC                   # Exchange-correlation functional
├── EIP                      # Embedded ion method
├── EMBED                    # Embedding methods
├── EXTERNAL_POTENTIAL
├── MIXED                    # Mixed force evaluations
├── MM                       # Molecular mechanics
│   ├── FORCEFIELD
│   ├── NEIGHBOR_LISTS
│   ├── PERIODIC_EFIELD
│   ├── POISSON
│   └── PRINT
├── NNP                      # Neural Network Potentials
│   ├── BIAS
│   ├── MODEL
│   └── PRINT
├── PRINT
├── PROPERTIES
├── PW_DFT                   # Plane-wave DFT
├── QMMM                     # QM/MM coupling
├── RESCALE_FORCES
└── SUBSYS                   # System definition (atoms, cell, topology)
    ├── CELL
    ├── COLVAR
    ├── COORD
    ├── CORE_COORD
    ├── CORE_VELOCITY
    ├── KIND
    ├── MULTIPOLES
    ├── PRINT
    ├── RNG_INIT
    ├── SHELL_COORD
    ├── SHELL_VELOCITY
    ├── TOPOLOGY
    └── VELOCITY
```

## FORCE_EVAL Keywords

Key keywords at the FORCE_EVAL level:

- **METHOD**: Selects the calculation method.
  - `Quickstep` - DFT/GPW/GAPW electronic structure
  - `Fist` - Classical molecular mechanics
  - `EIP` - Embedded ion method
  - `Mixed` - Mixed force evaluation
  - `QMMM` - QM/MM hybrid
  - `NNP` - Neural network potentials

## MOTION Section Hierarchy

```
MOTION
├── BAND                     # Nudged elastic band / string method
├── CELL_OPT                 # Cell optimization
│   ├── BFGS, CG, LBFGS, PRINT
├── CONSTRAINT               # Atomic constraints
│   ├── COLLECTIVE, FIXED_ATOMS, G3X3, G4X6, HBONDS, VIRTUAL_SITE
├── DRIVER
├── FLEXIBLE_PARTITIONING
├── FREE_ENERGY              # Free energy methods
│   ├── ALCHEMICAL_CHANGE, METADYN, UMBRELLA_INTEGRATION
├── GEO_OPT                  # Geometry optimization
│   ├── BFGS, CG, LBFGS, PRINT, TRANSITION_STATE
├── MC                       # Monte Carlo
├── MD                       # Molecular dynamics
│   ├── ADIABATIC_DYNAMICS, AVERAGES, BAROSTAT, CASCADE
│   ├── INITIAL_VIBRATION, LANGEVIN, MSST, PRINT
│   ├── REFTRAJ, RESPA, SHELL, THERMAL_REGION
│   ├── THERMOSTAT, VELOCITY_SOFTENING
├── PINT                     # Path integral MD
├── PRINT
├── SHELL_OPT
└── TMC                      # Temperature Monte Carlo
```

## Input File Syntax Rules

1. Sections begin with `&SECTION_NAME` and end with `&END SECTION_NAME`
2. Sections can accept parameters: `&KIND H`
3. Sections can be repeated
4. Keywords: `KEYWORD value1 value2 ...`
5. Units supported: `COORD [angstrom] 1.0 2.0 3.0`
6. Comments: lines starting with `!` or `#`

### Preprocessor Directives

- `@SET var value` - Define variable
- `${var}` - Variable substitution
- `@INCLUDE file` - Include file
- `@IF/@ELSE/@ENDIF` - Conditional compilation
- `@XCTYPE` - Include XC functional definition

## References

1. CP2K Input Reference: https://manual.cp2k.org/trunk/CP2K_INPUT.html
2. FORCE_EVAL Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL.html
3. Input File Overview: https://www.cp2k.org/input_file
4. IPCMS CP2K Tutorial: https://www.ipcms.fr/uploads/2023/09/cp2k.pdf
