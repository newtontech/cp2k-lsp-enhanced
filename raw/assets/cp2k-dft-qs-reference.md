> Source: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html
> Additional: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT.html, https://manual.cp2k.org/trunk/methods/dft/index.html

# CP2K DFT QS (Quickstep) Module Reference

## Overview

The QS (Quickstep) section under `&FORCE_EVAL / &DFT / &QS` contains parameters needed to set up
the Quickstep framework -- CP2K's primary DFT engine. It controls the electronic structure method,
precision settings, extrapolation strategies, and various advanced options.

## QS Section Path

```
CP2K_INPUT / FORCE_EVAL / DFT / QS
```

## QS Subsections

| Subsection | Purpose |
|------------|---------|
| CDFT | Constrained DFT |
| DDAPC_RESTRAINT | Density-derived atomic point charge restraint |
| DFTB | Density Functional Tight Binding |
| DISTRIBUTION | Distribution settings for parallel calculations |
| LRIGPW | Local Resolution of Identity GPW |
| MULLIKEN_RESTRAINT | Mulliken population restraint |
| OPTIMIZE_LRI_BASIS | Optimize LRI basis sets |
| OPT_DMFET | Density matrix embedding optimization |
| OPT_EMBED | Embedding optimization |
| S2_RESTRAINT | Spin-squared restraint |
| SE | Semi-empirical methods |
| XTB | Extended Tight Binding (GFN-xTB) |

## QS Keywords -- Complete Reference

### METHOD (enum, default: GPW)

Specifies the electronic structure method:

| Value | Description |
|-------|-------------|
| `GPW` | Gaussian and Plane Waves method (most common) |
| `GAPW` | Gaussian Augmented Plane Waves method |
| `GAPW_XC` | GAPW only for exchange-correlation |
| `LRIGPW` | Local Resolution of Identity GPW |
| `RIGPW` | Resolution of Identity for HXC terms |
| `OFGPW` | Orbital-free GPW method |
| `DFTB` | Density Functional based Tight Binding |
| `XTB` | GFN-xTB Extended Tight Binding |
| `MNDO` | MNDO semiempirical |
| `MNDOD` | MNDO-d semiempirical |
| `AM1` | AM1 semiempirical |
| `PM3` | PM3 semiempirical |
| `PM6` | PM6 semiempirical |
| `PM6-FM` | PM6-FM semiempirical |
| `PDG` | PDG semiempirical |
| `RM1` | RM1 semiempirical |
| `PNNL` | PNNL semiempirical |

References: Lippert1997, Lippert1999, Krack2000, VandeVondele2005, VandeVondele2006

### Precision Control Keywords

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `EPS_DEFAULT` | real | 1.0E-10 | Master precision; sets all EPS_xxx to achieve energy correct up to this value |
| `EPS_PGF_ORB` | real | sqrt(EPS_DEFAULT) | Precision of overlap matrix elements |
| `EPS_FILTER_MATRIX` | real | 0.0 | Threshold for filtering matrix elements |
| `EPS_GVG_RSPACE` | real | sqrt(EPS_DEFAULT) | Precision of realspace KS matrix element integration |
| `EPS_RHO` | real | EPS_DEFAULT | Precision of density mapping on grids |
| `EPS_RHO_GSPACE` | real | EPS_DEFAULT | Precision of density mapping in g-space (overrides EPS_RHO) |
| `EPS_RHO_RSPACE` | real | EPS_DEFAULT | Precision of density mapping in r-space (overrides EPS_RHO) |
| `EPS_CORE_CHARGE` | real | EPS_DEFAULT/100 | Precision for mapping core charges |
| `EPS_PPL` | real | 1.0E-2 | Precision for local part of pseudopotential |
| `EPS_PPNL` | real | sqrt(EPS_DEFAULT) | Precision of non-local pseudopotential |
| `EPS_KG_ORB` | real | sqrt(EPS_DEFAULT) | Precision for Kim-Gordon subset coloring |
| `EPS_CPC` | real | EPS_DEFAULT | Precision of GAPW projection |

### GAPW-Specific Keywords

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `ALPHA0_HARD` | real | 0.0 | Exponent for hard compensation charge |
| `ALPHA_WEIGHTS` | real | 6.0 | Gaussian exponent reference for accurate integration (rc=1.2 Bohr) |
| `EPSFIT` | real | 1.0E-4 | Tolerance controlling split of Gaussian basis into hard/soft parts |
| `EPSISO` | real | 1.0E-12 | Precision for isolated projector determination |
| `EPSRHO0` | real | 1.0E-6 | Tolerance for V(rho0-rho0_soft) compensation range |
| `EPSSVD` | real | 1.0E-8 | Tolerance for SVD of projector matrix |
| `GAPW_1C_BASIS` | enum | ORB | How to construct GAPW one-center basis (ORB, EXT_SMALL, EXT_MEDIUM, EXT_LARGE, EXT_VERY_LARGE) |
| `GAPW_ACCURATE_XCINT` | logical | F | Use accurate GAPW/GAPW_XC XC integration scheme |
| `FORCE_PAW` | logical | F | Use GAPW for all atoms including soft basis sets |
| `LADDN0` | integer | 99 | Integer added to max L for compensation charge density |
| `LMAXN0` | integer | 2 | Max L for compensation density expansion |
| `LMAXN1` | integer | -1 | Max L for atomic density expansion |
| `MAX_RAD_LOCAL` | real | 25.0 | Maximum radius for projector generation |
| `QUADRATURE` | enum | GC_LOG | Algorithm for atomic radial grids (GC_SIMPLE, GC_TRANSFORMED, GC_LOG) |

### EXTRAPOLATION (enum)

Extrapolation strategy for the wavefunction during MD. Not all options available for all methods.

| Value | Description |
|-------|-------------|
| `USE_GUESS` | Use SCF_GUESS method (no extrapolation) |
| `USE_PREV_P` | Use previous density matrix |
| `USE_PREV_RHO_R` | Use previous density in real space |
| `LINEAR_WF` | Linear extrapolation of wavefunction (not for k-points) |
| `LINEAR_P` | Linear extrapolation of density matrix |
| `LINEAR_PS` | Linear extrapolation of P*S matrix (not for k-points) |
| `USE_PREV_WF` | Use previous wavefunction |
| `PS` | Higher order extrapolation of P*S (recommended) |
| `FROZEN` | Frozen (not for k-points) |
| `ASPC` | Always stable predictor corrector (recommended for MD) |
| `GEXT_PROJ` | GExt extrapolation for P*S matrix |
| `GEXT_PROJ_QTR` | Quasi time-reversible GExt extrapolation |

- `EXTRAPOLATION_ORDER` (integer): Order for PS/ASPC (typically 2-4) or GEXT (typically 4-10)

### Plane Wave Grid Keywords

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `PW_GRID` | enum | NS-FULLSPACE | PW grid type (SPHERICAL, NS-FULLSPACE, NS-HALFSPACE) |
| `PW_GRID_BLOCKED` | enum | FREE | Distribution in g-space (FREE, TRUE, FALSE) |
| `PW_GRID_LAYOUT` | integer[2] | -1 -1 | Force particular real-space layout for PW grids |

### Other Keywords

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `STO_NG` | integer | 6 | Order of Gaussian expansion of Slater orbital basis sets |
| `CORE_PPL` | enum | ANALYTIC | Method for local pseudopotential (ANALYTIC, GRID) |
| `MIN_PAIR_LIST_RADIUS` | real | 0.0 | Minimum overlap pair list radius [Bohr] |
| `TRANSPORT` | logical | F | Perform transport calculations (coupling with OMEN) |
| `LS_SCF` | logical | F | Perform linear scaling SCF |
| `KG_METHOD` | logical | F | Use Kim-Gordon-like scheme |

## DFT Section Key Keywords (Parent of QS)

The parent `&DFT` section contains these important keywords:

- `BASIS_SET_FILE_NAME` - Path to basis set file
- `POTENTIAL_FILE_NAME` - Path to pseudopotential file
- `CHARGE` - Total system charge (default 0)
- `MULTIPLICITY` - Spin multiplicity
- `LSD` - Enable spin-polarized calculation
- `UKS` - Unrestricted Kohn-Sham

### Key DFT Subsections

- **MGRID**: Multigrid plane wave cutoff settings (CUTOFF, REL_CUTOFF, NGRIDS)
- **SCF**: SCF convergence parameters (EPS_SCF, MAX_SCF, SCF_GUESS, OT, SMEAR)
- **XC**: Exchange-correlation functional and van der Waals corrections
- **KPOINTS**: k-point sampling for periodic systems
- **POISSON**: Poisson solver settings
- **LOCALIZE**: Orbital localization
- **PRINT**: Output control

## Recommended Settings by Calculation Type

### Standard GPW Production Calculation

```cp2k
&DFT
  BASIS_SET_FILE_NAME BASIS_SET
  POTENTIAL_FILE_NAME POTENTIAL
  &MGRID
    CUTOFF 400
    REL_CUTOFF 60
  &END MGRID
  &QS
    METHOD GPW
    EPS_DEFAULT 1.0E-10
    EXTRAPOLATION PS
    EXTRAPOLATION_ORDER 3
  &END QS
  &SCF
    EPS_SCF 1.0E-6
    MAX_SCF 50
    SCF_GUESS atomic
    &OT
      PRECONDITIONER FULL_ALL
    &END OT
  &END SCF
  &XC
    &XC_FUNCTIONAL PBE
    &END XC_FUNCTIONAL
  &END XC
&END DFT
```

### GAPW All-Electron Calculation

```cp2k
&QS
  METHOD GAPW
  EPS_DEFAULT 1.0E-12
  GAPW_ACCURATE_XCINT T
  QUADRATURE GC_LOG
&END QS
```

### AIMD with Efficient Extrapolation

```cp2k
&QS
  METHOD GPW
  EPS_DEFAULT 1.0E-8
  EXTRAPOLATION ASPC
  EXTRAPOLATION_ORDER 3
&END QS
```

## References

1. QS Module Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/QS.html
2. DFT Section Reference: https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT.html
3. DFT Methods Overview: https://manual.cp2k.org/trunk/methods/dft/index.html
4. Lippert et al., J. Comput. Phys. 100, 623 (1997)
5. VandeVondele et al., Comput. Phys. Commun. 167, 103 (2005)
